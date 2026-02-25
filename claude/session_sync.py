#!/usr/bin/env python3
"""claude-session-sync — Export Claude Code session transcripts to markdown or raw copies.

Usage:
    claude-session-sync export <session.jsonl> <dest> [--format markdown|raw] [--force]
    claude-session-sync sync-all <dest> [--project-filter PATH] [--format ...] [--force]
    claude-session-sync status [dest] [--project-filter PATH]
    claude-session-sync export-current <dest> [--project-dir CWD] [--format ...]
"""

import argparse
import json
import os
import sys
import datetime
import shutil

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MANIFEST_FILENAME = ".claude-sync-manifest.json"
CLAUDE_PROJECTS_DIR = os.path.join(os.path.expanduser("~"), ".claude", "projects")

# ---------------------------------------------------------------------------
# Parsing layer
# ---------------------------------------------------------------------------


def parse_line(line):
    """Parse a single JSONL line. Returns dict or None on error."""
    try:
        return json.loads(line)
    except (json.JSONDecodeError, ValueError):
        return None


def extract_user_text(content):
    """Extract user text from message content.

    Handles:
    - Plain string
    - List of single-character strings (char list)
    - Mixed list with tool_result dicts and chars
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chars = [c for c in content if isinstance(c, str)]
        return "".join(chars)
    return ""


def is_tool_result_only(content):
    """True if content is exclusively tool_result blocks (no user text)."""
    if isinstance(content, str):
        return False
    if isinstance(content, list):
        if not content:
            return True
        has_tool_result = False
        for item in content:
            if isinstance(item, dict) and item.get("type") == "tool_result":
                has_tool_result = True
            elif isinstance(item, str):
                return False
        return has_tool_result
    return False


def extract_tool_results(content):
    """Extract tool_result dicts from content list."""
    if not isinstance(content, list):
        return []
    return [
        item
        for item in content
        if isinstance(item, dict) and item.get("type") == "tool_result"
    ]


def scan_metadata(jsonl_path):
    """Pass 1: Read first user message, extract session metadata.

    Returns dict with sessionId, cwd, version, gitBranch, timestamp or None.
    """
    try:
        with open(jsonl_path) as f:
            for line in f:
                record = parse_line(line)
                if record is None:
                    continue
                if (
                    record.get("type") == "user"
                    and record.get("message", {}).get("role") == "user"
                ):
                    return {
                        "sessionId": record.get("sessionId"),
                        "cwd": record.get("cwd"),
                        "version": record.get("version"),
                        "gitBranch": record.get("gitBranch"),
                        "timestamp": record.get("timestamp"),
                    }
    except (OSError, IOError):
        return None
    return None


# ---------------------------------------------------------------------------
# Discovery & disambiguation
# ---------------------------------------------------------------------------


def discover_sessions(project_filter=None):
    """Scan ~/.claude/projects/*/ for *.jsonl files.

    If project_filter is set, only include sessions whose cwd starts with that path.
    Returns list of absolute paths to JSONL files.
    """
    sessions = []
    if not os.path.isdir(CLAUDE_PROJECTS_DIR):
        return sessions

    for project_dir in os.listdir(CLAUDE_PROJECTS_DIR):
        full_dir = os.path.join(CLAUDE_PROJECTS_DIR, project_dir)
        if not os.path.isdir(full_dir):
            continue
        for fname in os.listdir(full_dir):
            if fname.endswith(".jsonl"):
                jsonl_path = os.path.join(full_dir, fname)
                if project_filter:
                    meta = scan_metadata(jsonl_path)
                    if (
                        meta
                        and meta.get("cwd")
                        and meta["cwd"].startswith(project_filter)
                    ):
                        sessions.append(jsonl_path)
                else:
                    sessions.append(jsonl_path)

    return sorted(sessions)


def compute_project_paths(cwd_list):
    """Compute minimum trailing path components for uniqueness.

    Given a list of cwd strings, returns a dict mapping each cwd to its
    disambiguated project path (using minimum trailing components).
    """
    if not cwd_list:
        return {}

    unique_cwds = list(set(cwd_list))
    if len(unique_cwds) == 1:
        return {unique_cwds[0]: os.path.basename(unique_cwds[0])}

    # Split each cwd into components
    def split_path(p):
        parts = []
        while True:
            head, tail = os.path.split(p)
            if tail:
                parts.insert(0, tail)
                p = head
            elif head and head != p:
                p = head
            else:
                break
        return parts

    cwd_parts = {cwd: split_path(cwd) for cwd in unique_cwds}

    # Start with 1 trailing component, increase until all unique
    result = {}
    remaining = set(unique_cwds)
    max_depth = max(len(parts) for parts in cwd_parts.values())

    for depth in range(1, max_depth + 1):
        if not remaining:
            break

        # Build trailing-component keys at this depth for remaining cwds only
        keys = {}
        for cwd in remaining:
            parts = cwd_parts[cwd]
            key = (
                os.path.join(*parts[-depth:])
                if depth <= len(parts)
                else os.path.join(*parts)
            )
            keys[cwd] = key

        # Find collisions among remaining cwds
        key_counts = {}
        for cwd, key in keys.items():
            key_counts[key] = key_counts.get(key, 0) + 1

        # Assign non-colliding cwds
        for cwd, key in keys.items():
            if key_counts[key] == 1:
                result[cwd] = key
                remaining.discard(cwd)

    # Handle any remaining (identical paths get same key)
    for cwd in remaining:
        parts = cwd_parts[cwd]
        result[cwd] = os.path.join(*parts) if parts else cwd

    return result


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------


def load_manifest(dest_dir):
    """Load manifest from dest_dir or return fresh one."""
    manifest_path = os.path.join(dest_dir, MANIFEST_FILENAME)
    try:
        with open(manifest_path) as f:
            data = json.load(f)
            if isinstance(data, dict) and "version" in data:
                return data
    except (OSError, IOError, json.JSONDecodeError, ValueError):
        pass
    return {"version": 1, "sessions": {}}


def save_manifest(dest_dir, manifest):
    """Atomic write manifest via .tmp + os.rename()."""
    manifest_path = os.path.join(dest_dir, MANIFEST_FILENAME)
    tmp_path = manifest_path + ".tmp"
    manifest["last_sync"] = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    with open(tmp_path, "w") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")
    os.rename(tmp_path, manifest_path)


def needs_sync(manifest, jsonl_path, force=False):
    """Check if session needs syncing based on mtime."""
    if force:
        return True
    entry = manifest.get("sessions", {}).get(jsonl_path)
    if entry is None:
        return True
    try:
        current_mtime = os.path.getmtime(jsonl_path)
    except OSError:
        return True
    return current_mtime != entry.get("source_mtime")


# ---------------------------------------------------------------------------
# Markdown rendering (Pass 2 — streaming)
# ---------------------------------------------------------------------------


def render_tool_input(tool_name, tool_input):
    """Render tool input for markdown."""
    if not isinstance(tool_input, dict):
        return ""

    if tool_name == "Bash":
        cmd = tool_input.get("command", "")
        desc = tool_input.get("description", "")
        lines = []
        if desc:
            lines.append(f"> {desc}")
            lines.append("")
        lines.append("```bash")
        lines.append(cmd)
        lines.append("```")
        return "\n".join(lines)

    if tool_name in ("Write", "Edit"):
        path = tool_input.get("file_path", "")
        lines = [f"> `{path}`"]
        if tool_name == "Write":
            content = tool_input.get("content", "")
            preview = content[:200]
            if len(content) > 200:
                preview += f"\n... ({len(content)} chars total)"
            lines.append("")
            lines.append("```")
            lines.append(preview)
            lines.append("```")
        elif tool_name == "Edit":
            old = tool_input.get("old_string", "")
            new = tool_input.get("new_string", "")
            old_preview = old[:100] + ("..." if len(old) > 100 else "")
            new_preview = new[:100] + ("..." if len(new) > 100 else "")
            lines.append("")
            lines.append(f"Old: `{old_preview}`")
            lines.append(f"New: `{new_preview}`")
        return "\n".join(lines)

    if tool_name == "Read":
        path = tool_input.get("file_path", "")
        return f"> `{path}`"

    if tool_name in ("Glob", "Grep"):
        pattern = tool_input.get("pattern", "")
        path = tool_input.get("path", "")
        if path:
            return f"> Pattern: `{pattern}` in `{path}`"
        return f"> Pattern: `{pattern}`"

    if tool_name == "Task":
        desc = tool_input.get("description", "")
        agent_type = tool_input.get("subagent_type", "")
        return f"> {agent_type}: {desc}"

    # Generic: JSON dump
    try:
        formatted = json.dumps(tool_input, indent=2)
        if len(formatted) > 500:
            formatted = formatted[:500] + "\n..."
        return f"```json\n{formatted}\n```"
    except (TypeError, ValueError):
        return str(tool_input)


def render_tool_result(result_content, is_error=False):
    """Render tool result in <details> block."""
    summary = "**Error**" if is_error else "Result"

    # Extract text from result content
    if isinstance(result_content, str):
        text = result_content
    elif isinstance(result_content, list):
        parts = []
        for block in result_content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        text = "\n".join(parts)
    else:
        text = str(result_content) if result_content else ""

    lines = [
        f"<details><summary>{summary}</summary>",
        "",
        "```",
        text,
        "```",
        "",
        "</details>",
    ]
    return "\n".join(lines)


def render_thinking_block(thinking_text):
    """Render thinking in <details> block."""
    return f"<details><summary>Thinking</summary>\n\n{thinking_text}\n\n</details>"


def render_markdown(jsonl_path, out_file, include_subagents=False):
    """Pass 2: Stream JSONL and write markdown to out_file.

    State machine that pairs tool_use with tool_result by id.
    """
    meta = scan_metadata(jsonl_path)
    if not meta:
        out_file.write("# Session (no metadata)\n\n---\n\n")
    else:
        session_id = meta.get("sessionId", "unknown")
        short_id = session_id[:8] if session_id else "unknown"
        ts = meta.get("timestamp", "")
        date = ts[:10] if ts else "unknown"
        cwd = meta.get("cwd", "unknown")
        project = os.path.basename(cwd) if cwd else "unknown"

        out_file.write(f"# Session: {short_id}\n\n")
        out_file.write(f"- **Date:** {date}\n")
        out_file.write(f"- **Project:** {project}\n")
        out_file.write(f"- **Working Directory:** {cwd}\n")
        if meta.get("gitBranch"):
            out_file.write(f"- **Git Branch:** {meta['gitBranch']}\n")
        if meta.get("version"):
            out_file.write(f"- **Claude Version:** {meta['version']}\n")
        out_file.write(f"- **Session ID:** {session_id}\n")
        out_file.write("\n---\n\n")

    # State for tool pairing
    pending_tool_uses = {}  # tool_use_id -> {name, input}
    subagent_messages = []  # collected progress messages

    with open(jsonl_path) as f:
        for line in f:
            record = parse_line(line)
            if record is None:
                continue

            msg_type = record.get("type")
            is_sidechain = record.get("isSidechain", False)

            # Skip file-history-snapshot
            if msg_type == "file-history-snapshot":
                continue

            # Skip hook_progress
            if msg_type == "hook_progress":
                continue

            # Collect progress/subagent messages
            if msg_type == "progress":
                if include_subagents:
                    subagent_messages.append(record)
                continue

            message = record.get("message", {})
            role = message.get("role", "")
            content = message.get("content", "")

            # System messages
            if msg_type == "system":
                subtype = record.get("subtype") or message.get("subtype")
                if subtype == "local_command":
                    continue
                # Render system message as blockquote
                sys_content = message.get("content", "")
                if isinstance(sys_content, str) and sys_content.strip():
                    text = sys_content.strip()
                    if len(text) > 500:
                        text = text[:500] + "..."
                    out_file.write("## System\n\n")
                    for sys_line in text.split("\n"):
                        out_file.write(f"> {sys_line}\n")
                    out_file.write("\n---\n\n")
                elif isinstance(sys_content, list):
                    parts = []
                    for block in sys_content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            parts.append(block.get("text", ""))
                    text = "\n".join(parts).strip()
                    if text:
                        if len(text) > 500:
                            text = text[:500] + "..."
                        out_file.write("## System\n\n")
                        for sys_line in text.split("\n"):
                            out_file.write(f"> {sys_line}\n")
                        out_file.write("\n---\n\n")
                continue

            # User messages
            if msg_type == "user" and role == "user":
                # Check if tool_result only — pair with pending tool_uses
                if is_tool_result_only(content):
                    tool_results = extract_tool_results(content)
                    for tr in tool_results:
                        tool_use_id = tr.get("tool_use_id", "")
                        tr_content = tr.get("content", "")
                        tr_is_error = tr.get("is_error", False)
                        if tool_use_id in pending_tool_uses:
                            rendered = render_tool_result(tr_content, tr_is_error)
                            out_file.write(rendered + "\n\n")
                            del pending_tool_uses[tool_use_id]
                        else:
                            # Orphan tool result — still render it
                            rendered = render_tool_result(tr_content, tr_is_error)
                            out_file.write(rendered + "\n\n")
                    continue

                # User typed text
                text = extract_user_text(content)
                if text.strip():
                    sidechain_marker = " *(sidechain)*" if is_sidechain else ""
                    out_file.write(f"## User{sidechain_marker}\n\n")
                    out_file.write(text.strip() + "\n\n")
                    out_file.write("---\n\n")
                continue

            # Assistant messages
            if msg_type == "assistant" or (not msg_type and role == "assistant"):
                if not isinstance(content, list):
                    continue

                sidechain_marker = " *(sidechain)*" if is_sidechain else ""
                wrote_header = False

                for block in content:
                    if not isinstance(block, dict):
                        continue

                    block_type = block.get("type", "")

                    if block_type == "thinking":
                        if not wrote_header:
                            out_file.write(f"## Assistant{sidechain_marker}\n\n")
                            wrote_header = True
                        rendered = render_thinking_block(block.get("thinking", ""))
                        out_file.write(rendered + "\n\n")

                    elif block_type == "text":
                        text = block.get("text", "")
                        # Strip model signature lines
                        lines = text.split("\n")
                        filtered = [
                            ln
                            for ln in lines
                            if not ln.strip().startswith("Co-Authored-By:")
                        ]
                        text = "\n".join(filtered).strip()
                        if text:
                            if not wrote_header:
                                out_file.write(f"## Assistant{sidechain_marker}\n\n")
                                wrote_header = True
                            out_file.write(text + "\n\n")

                    elif block_type == "tool_use":
                        if not wrote_header:
                            out_file.write(f"## Assistant{sidechain_marker}\n\n")
                            wrote_header = True
                        tool_name = block.get("name", "Unknown")
                        tool_id = block.get("id", "")
                        tool_input = block.get("input", {})
                        pending_tool_uses[tool_id] = {
                            "name": tool_name,
                            "input": tool_input,
                        }

                        out_file.write(f"### Tool: {tool_name}\n\n")
                        rendered_input = render_tool_input(tool_name, tool_input)
                        if rendered_input:
                            out_file.write(rendered_input + "\n\n")

                if wrote_header:
                    out_file.write("---\n\n")

    # Append subagent sections if included
    if subagent_messages:
        _render_subagent_section(out_file, subagent_messages)


def _render_subagent_section(out_file, subagent_messages):
    """Group subagent messages by agentId and render each in <details>."""
    # Group by agentId
    agents = {}
    for msg in subagent_messages:
        data = msg.get("data", {})
        agent_id = data.get("agentId", "unknown")
        if agent_id not in agents:
            agents[agent_id] = {
                "prompt": data.get("prompt", ""),
                "messages": [],
            }
        agents[agent_id]["messages"].append(data.get("message", {}))

    for agent_id, info in agents.items():
        prompt = info["prompt"]
        desc = prompt[:80] if prompt else agent_id
        out_file.write(f"## Subagent: {desc}\n\n")
        out_file.write(f"<details><summary>Agent {agent_id[:12]}</summary>\n\n")

        for nested_msg in info["messages"]:
            nested_message = nested_msg.get("message", {})
            role = nested_message.get("role", "")
            content = nested_message.get("content", "")

            if role == "user":
                text = extract_user_text(content)
                if text.strip():
                    out_file.write(f"**User:** {text.strip()}\n\n")
            elif role == "assistant":
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict):
                            if block.get("type") == "text":
                                out_file.write(
                                    f"**Assistant:** {block.get('text', '')}\n\n"
                                )
                            elif block.get("type") == "tool_use":
                                out_file.write(f"**Tool:** {block.get('name', '')}\n\n")

        out_file.write("</details>\n\n---\n\n")


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


def make_output_filename(meta, fmt):
    """Generate output filename: YYYY-MM-DD_<8-char-id>.{md|jsonl}"""
    session_id = meta.get("sessionId", "unknown")
    short_id = session_id[:8] if session_id else "unknown"
    ts = meta.get("timestamp", "")
    date = ts[:10] if ts else "unknown"
    ext = "md" if fmt == "markdown" else "jsonl"
    return f"{date}_{short_id}.{ext}"


def export_session(
    jsonl_path,
    dest_dir,
    project_name,
    fmt,
    manifest,
    force=False,
    include_subagents=False,
):
    """Export a single session. Returns True on success."""
    meta = scan_metadata(jsonl_path)
    if not meta:
        print(f"Warning: Could not read metadata from {jsonl_path}", file=sys.stderr)
        return False

    if not needs_sync(manifest, jsonl_path, force):
        return False

    output_name = make_output_filename(meta, fmt)
    project_dir = os.path.join(dest_dir, project_name)
    os.makedirs(project_dir, exist_ok=True)
    output_path = os.path.join(project_dir, output_name)

    if fmt == "raw":
        shutil.copy2(jsonl_path, output_path)
    else:
        with open(output_path, "w") as out:
            render_markdown(jsonl_path, out, include_subagents=include_subagents)

    # Update manifest
    try:
        source_mtime = os.path.getmtime(jsonl_path)
    except OSError:
        source_mtime = 0

    manifest.setdefault("sessions", {})[jsonl_path] = {
        "session_id": meta.get("sessionId", ""),
        "project_name": project_name,
        "source_mtime": source_mtime,
        "exported_path": os.path.join(project_name, output_name),
        "format": fmt,
    }

    return True


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------


def cmd_export(args):
    """Single session export."""
    jsonl_path = os.path.abspath(args.session)
    dest_dir = os.path.abspath(args.dest)
    fmt = args.format

    if not os.path.isfile(jsonl_path):
        print(f"Error: File not found: {jsonl_path}", file=sys.stderr)
        return 1

    os.makedirs(dest_dir, exist_ok=True)
    manifest = load_manifest(dest_dir)

    meta = scan_metadata(jsonl_path)
    if not meta:
        print(f"Error: Could not read metadata from {jsonl_path}", file=sys.stderr)
        return 1

    cwd = meta.get("cwd", "")
    project_name = os.path.basename(cwd) if cwd else "unknown"

    exported = export_session(
        jsonl_path,
        dest_dir,
        project_name,
        fmt,
        manifest,
        force=args.force,
        include_subagents=getattr(args, "include_subagents", False),
    )

    if exported:
        save_manifest(dest_dir, manifest)
        entry = manifest["sessions"][jsonl_path]
        print(f"Exported: {entry['exported_path']}")
    else:
        print("Session already up to date (use --force to re-export)")

    return 0


def cmd_sync_all(args):
    """Batch sync all discovered sessions."""
    dest_dir = os.path.abspath(args.dest)
    fmt = args.format
    project_filter = args.project_filter
    force = args.force
    include_subagents = args.include_subagents

    os.makedirs(dest_dir, exist_ok=True)
    manifest = load_manifest(dest_dir)

    sessions = discover_sessions(project_filter)
    if not sessions:
        print("No sessions found.")
        return 0

    # Collect metadata for all sessions to compute project paths
    session_meta = {}
    cwds = []
    for jsonl_path in sessions:
        meta = scan_metadata(jsonl_path)
        if meta and meta.get("cwd"):
            session_meta[jsonl_path] = meta
            cwds.append(meta["cwd"])

    # Compute disambiguated project paths
    path_map = compute_project_paths(cwds)

    exported_count = 0
    skipped_count = 0
    error_count = 0

    for jsonl_path, meta in session_meta.items():
        cwd = meta["cwd"]
        project_name = path_map.get(cwd, os.path.basename(cwd))

        try:
            exported = export_session(
                jsonl_path,
                dest_dir,
                project_name,
                fmt,
                manifest,
                force=force,
                include_subagents=include_subagents,
            )
            if exported:
                exported_count += 1
            else:
                skipped_count += 1
        except Exception as e:
            print(f"Error exporting {jsonl_path}: {e}", file=sys.stderr)
            error_count += 1

    save_manifest(dest_dir, manifest)
    print(
        f"Sync complete: {exported_count} exported, {skipped_count} up-to-date, {error_count} errors"
    )
    return 0


def cmd_status(args):
    """Print synced/unsynced/modified counts."""
    dest_dir = os.path.abspath(args.dest) if args.dest else None
    project_filter = args.project_filter

    sessions = discover_sessions(project_filter)
    if not sessions:
        print("No sessions found.")
        return 0

    if dest_dir:
        manifest = load_manifest(dest_dir)
    else:
        manifest = {"version": 1, "sessions": {}}

    synced = 0
    unsynced = 0
    modified = 0

    for jsonl_path in sessions:
        entry = manifest.get("sessions", {}).get(jsonl_path)
        if entry is None:
            unsynced += 1
        else:
            try:
                current_mtime = os.path.getmtime(jsonl_path)
            except OSError:
                unsynced += 1
                continue
            if current_mtime != entry.get("source_mtime"):
                modified += 1
            else:
                synced += 1

    total = synced + unsynced + modified
    print(
        f"Sessions: {total} total, {synced} synced, {unsynced} unsynced, {modified} modified"
    )
    return 0


def cmd_export_current(args):
    """Auto-detect most recent JSONL matching --project-dir."""
    dest_dir = os.path.abspath(args.dest)
    project_dir = os.path.abspath(args.project_dir)
    fmt = args.format

    # Find all JSONL files, filter by cwd matching project_dir
    candidates = []
    if os.path.isdir(CLAUDE_PROJECTS_DIR):
        for pdir in os.listdir(CLAUDE_PROJECTS_DIR):
            full_dir = os.path.join(CLAUDE_PROJECTS_DIR, pdir)
            if not os.path.isdir(full_dir):
                continue
            for fname in os.listdir(full_dir):
                if fname.endswith(".jsonl"):
                    jsonl_path = os.path.join(full_dir, fname)
                    meta = scan_metadata(jsonl_path)
                    if meta and meta.get("cwd") == project_dir:
                        try:
                            mtime = os.path.getmtime(jsonl_path)
                        except OSError:
                            continue
                        candidates.append((mtime, jsonl_path, meta))

    if not candidates:
        print(
            f"No sessions found for project directory: {project_dir}", file=sys.stderr
        )
        return 1

    # Pick the most recently modified
    candidates.sort(key=lambda x: x[0], reverse=True)
    _, jsonl_path, meta = candidates[0]

    os.makedirs(dest_dir, exist_ok=True)
    manifest = load_manifest(dest_dir)

    cwd = meta.get("cwd", "")
    project_name = os.path.basename(cwd) if cwd else "unknown"

    exported = export_session(
        jsonl_path,
        dest_dir,
        project_name,
        fmt,
        manifest,
        force=True,
        include_subagents=getattr(args, "include_subagents", False),
    )

    if exported:
        save_manifest(dest_dir, manifest)
        entry = manifest["sessions"][jsonl_path]
        print(f"Exported: {entry['exported_path']}")
    else:
        print("Export failed.", file=sys.stderr)
        return 1

    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv=None):
    if argv is None:
        argv = sys.argv

    parser = argparse.ArgumentParser(
        prog="claude-session-sync",
        description="Export Claude Code session transcripts to markdown or raw copies",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # export
    p_export = subparsers.add_parser("export", help="Export a single session")
    p_export.add_argument("session", help="Path to session JSONL file")
    p_export.add_argument("dest", help="Destination directory")
    p_export.add_argument(
        "--format",
        choices=["markdown", "raw"],
        default="markdown",
        help="Output format (default: markdown)",
    )
    p_export.add_argument(
        "--force", action="store_true", help="Re-export even if up to date"
    )
    p_export.add_argument(
        "--include-subagents",
        action="store_true",
        help="Include subagent messages in output",
    )

    # sync-all
    p_sync = subparsers.add_parser("sync-all", help="Batch sync all sessions")
    p_sync.add_argument("dest", help="Destination directory")
    p_sync.add_argument(
        "--project-filter", help="Only sync sessions whose cwd starts with PATH"
    )
    p_sync.add_argument(
        "--format",
        choices=["markdown", "raw"],
        default="markdown",
        help="Output format (default: markdown)",
    )
    p_sync.add_argument("--force", action="store_true", help="Re-export all sessions")
    p_sync.add_argument(
        "--include-subagents",
        action="store_true",
        help="Include subagent messages in output",
    )

    # status
    p_status = subparsers.add_parser("status", help="Show sync status")
    p_status.add_argument("dest", nargs="?", default=None, help="Destination directory")
    p_status.add_argument(
        "--project-filter", help="Only check sessions whose cwd starts with PATH"
    )

    # export-current
    p_current = subparsers.add_parser(
        "export-current", help="Export most recent session for a project"
    )
    p_current.add_argument("dest", help="Destination directory")
    p_current.add_argument(
        "--project-dir",
        default=os.getcwd(),
        help="Project directory to match (default: $PWD)",
    )
    p_current.add_argument(
        "--format",
        choices=["markdown", "raw"],
        default="markdown",
        help="Output format (default: markdown)",
    )
    p_current.add_argument(
        "--include-subagents",
        action="store_true",
        help="Include subagent messages in output",
    )

    args = parser.parse_args(argv[1:])

    if not args.command:
        parser.print_help()
        return 1

    dispatch = {
        "export": cmd_export,
        "sync-all": cmd_sync_all,
        "status": cmd_status,
        "export-current": cmd_export_current,
    }

    return dispatch[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
