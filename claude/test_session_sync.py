#!/usr/bin/env python3
"""Tests for claude-session-sync (session_sync.py)."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

# Import the module under test
sys.path.insert(0, os.path.dirname(__file__))
import session_sync


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_synthetic_jsonl(messages, path=None):
    """Create a temp JSONL file from a list of dicts. Returns the file path."""
    if path is None:
        fd, path = tempfile.mkstemp(suffix=".jsonl")
        os.close(fd)
    with open(path, "w") as f:
        for msg in messages:
            f.write(json.dumps(msg) + "\n")
    return path


def make_user_message(text, session_id="abcd1234-5678-9abc-def0-123456789abc",
                      cwd="/home/user/project", version="2.1.55",
                      git_branch="main", timestamp="2026-02-24T10:00:00Z",
                      sidechain=False):
    """Create a synthetic user message."""
    return {
        "type": "user",
        "sessionId": session_id,
        "cwd": cwd,
        "version": version,
        "gitBranch": git_branch,
        "timestamp": timestamp,
        "isSidechain": sidechain,
        "message": {
            "role": "user",
            "content": text,
        },
    }


def make_assistant_message(content_blocks, sidechain=False):
    """Create a synthetic assistant message."""
    return {
        "type": "assistant",
        "isSidechain": sidechain,
        "message": {
            "role": "assistant",
            "content": content_blocks,
        },
    }


def make_tool_result_message(tool_use_id, content, is_error=False):
    """Create a user message containing only a tool_result."""
    return {
        "type": "user",
        "isSidechain": False,
        "message": {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "is_error": is_error,
                    "content": content,
                }
            ],
        },
    }


def make_system_message(content, subtype=None):
    """Create a synthetic system message."""
    msg = {
        "type": "system",
        "isSidechain": False,
        "message": {
            "role": "system",
            "content": content,
        },
    }
    if subtype:
        msg["subtype"] = subtype
    return msg


def make_file_history_snapshot():
    """Create a file-history-snapshot message."""
    return {
        "type": "file-history-snapshot",
        "snapshot": {"trackedFileBackups": {}},
        "isSnapshotUpdate": False,
    }


def make_progress_message(agent_id="agent123", prompt="Search codebase",
                          nested_text="Found 5 results"):
    """Create a progress (subagent) message."""
    return {
        "type": "progress",
        "toolUseID": "agent_msg_001",
        "parentToolUseID": "toolu_001",
        "data": {
            "type": "agent_progress",
            "agentId": agent_id,
            "prompt": prompt,
            "message": {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": nested_text}],
                },
            },
        },
    }


# ---------------------------------------------------------------------------
# Test: extract_user_text
# ---------------------------------------------------------------------------

class TestExtractUserText(unittest.TestCase):
    def test_plain_string(self):
        self.assertEqual(session_sync.extract_user_text("hello world"), "hello world")

    def test_char_list(self):
        chars = list("hello")
        self.assertEqual(session_sync.extract_user_text(chars), "hello")

    def test_mixed_list_with_tool_results(self):
        content = [{"type": "tool_result", "tool_use_id": "t1", "content": "ok"}]
        self.assertEqual(session_sync.extract_user_text(content), "")

    def test_empty_string(self):
        self.assertEqual(session_sync.extract_user_text(""), "")

    def test_empty_list(self):
        self.assertEqual(session_sync.extract_user_text([]), "")

    def test_none(self):
        self.assertEqual(session_sync.extract_user_text(None), "")


# ---------------------------------------------------------------------------
# Test: is_tool_result_only
# ---------------------------------------------------------------------------

class TestIsToolResultOnly(unittest.TestCase):
    def test_tool_result_only(self):
        content = [{"type": "tool_result", "tool_use_id": "t1", "content": "ok"}]
        self.assertTrue(session_sync.is_tool_result_only(content))

    def test_with_text_chars(self):
        content = ["h", "i", {"type": "tool_result", "tool_use_id": "t1", "content": "ok"}]
        self.assertFalse(session_sync.is_tool_result_only(content))

    def test_plain_string(self):
        self.assertFalse(session_sync.is_tool_result_only("hello"))

    def test_empty_list(self):
        self.assertTrue(session_sync.is_tool_result_only([]))


# ---------------------------------------------------------------------------
# Test: scan_metadata
# ---------------------------------------------------------------------------

class TestScanMetadata(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_extracts_fields(self):
        path = make_synthetic_jsonl([
            make_file_history_snapshot(),
            make_user_message("hello", session_id="sess-1234", cwd="/home/user/proj"),
        ], os.path.join(self.tmpdir, "test.jsonl"))
        meta = session_sync.scan_metadata(path)
        self.assertIsNotNone(meta)
        self.assertEqual(meta["sessionId"], "sess-1234")
        self.assertEqual(meta["cwd"], "/home/user/proj")
        self.assertEqual(meta["version"], "2.1.55")
        self.assertEqual(meta["gitBranch"], "main")

    def test_skips_snapshot(self):
        path = make_synthetic_jsonl([
            make_file_history_snapshot(),
            make_user_message("hello"),
        ], os.path.join(self.tmpdir, "test.jsonl"))
        meta = session_sync.scan_metadata(path)
        self.assertIsNotNone(meta)

    def test_empty_file(self):
        path = os.path.join(self.tmpdir, "empty.jsonl")
        with open(path, "w") as f:
            pass
        meta = session_sync.scan_metadata(path)
        self.assertIsNone(meta)

    def test_corrupt_file(self):
        path = os.path.join(self.tmpdir, "corrupt.jsonl")
        with open(path, "w") as f:
            f.write("not json\n")
            f.write("also not json\n")
        meta = session_sync.scan_metadata(path)
        self.assertIsNone(meta)

    def test_no_user_message(self):
        path = make_synthetic_jsonl([
            make_file_history_snapshot(),
            make_assistant_message([{"type": "text", "text": "hi"}]),
        ], os.path.join(self.tmpdir, "test.jsonl"))
        meta = session_sync.scan_metadata(path)
        self.assertIsNone(meta)


# ---------------------------------------------------------------------------
# Test: compute_project_paths
# ---------------------------------------------------------------------------

class TestComputeProjectPaths(unittest.TestCase):
    def test_no_collision(self):
        result = session_sync.compute_project_paths([
            "/home/user/Work/firefox",
            "/home/user/Work/worklog",
        ])
        self.assertEqual(result["/home/user/Work/firefox"], "firefox")
        self.assertEqual(result["/home/user/Work/worklog"], "worklog")

    def test_two_way_collision(self):
        result = session_sync.compute_project_paths([
            "/home/user/Work/X/Z",
            "/home/user/Work/Y/Z",
        ])
        self.assertEqual(result["/home/user/Work/X/Z"], os.path.join("X", "Z"))
        self.assertEqual(result["/home/user/Work/Y/Z"], os.path.join("Y", "Z"))

    def test_mixed_collision(self):
        result = session_sync.compute_project_paths([
            "/home/user/Work/X/Z",
            "/home/user/Work/Y/Z",
            "/home/user/Work/firefox",
        ])
        self.assertEqual(result["/home/user/Work/X/Z"], os.path.join("X", "Z"))
        self.assertEqual(result["/home/user/Work/Y/Z"], os.path.join("Y", "Z"))
        self.assertEqual(result["/home/user/Work/firefox"], "firefox")

    def test_single_path(self):
        result = session_sync.compute_project_paths(["/home/user/project"])
        self.assertEqual(result["/home/user/project"], "project")

    def test_empty(self):
        result = session_sync.compute_project_paths([])
        self.assertEqual(result, {})

    def test_identical_paths(self):
        result = session_sync.compute_project_paths([
            "/home/user/project",
            "/home/user/project",
        ])
        # Deduplicated to single entry
        self.assertIn("/home/user/project", result)


# ---------------------------------------------------------------------------
# Test: Manifest
# ---------------------------------------------------------------------------

class TestManifest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_load_missing(self):
        m = session_sync.load_manifest(self.tmpdir)
        self.assertEqual(m["version"], 1)
        self.assertEqual(m["sessions"], {})

    def test_load_corrupt(self):
        manifest_path = os.path.join(self.tmpdir, session_sync.MANIFEST_FILENAME)
        with open(manifest_path, "w") as f:
            f.write("not json")
        m = session_sync.load_manifest(self.tmpdir)
        self.assertEqual(m["version"], 1)

    def test_save_load_roundtrip(self):
        m = {"version": 1, "sessions": {"/tmp/test.jsonl": {"session_id": "abc"}}}
        session_sync.save_manifest(self.tmpdir, m)
        loaded = session_sync.load_manifest(self.tmpdir)
        self.assertEqual(loaded["sessions"]["/tmp/test.jsonl"]["session_id"], "abc")
        self.assertIn("last_sync", loaded)

    def test_needs_sync_new_session(self):
        m = {"version": 1, "sessions": {}}
        self.assertTrue(session_sync.needs_sync(m, "/tmp/new.jsonl"))

    def test_needs_sync_mtime_match(self):
        path = os.path.join(self.tmpdir, "test.jsonl")
        with open(path, "w") as f:
            f.write("{}\n")
        mtime = os.path.getmtime(path)
        m = {"version": 1, "sessions": {path: {"source_mtime": mtime}}}
        self.assertFalse(session_sync.needs_sync(m, path))

    def test_needs_sync_force(self):
        path = os.path.join(self.tmpdir, "test.jsonl")
        with open(path, "w") as f:
            f.write("{}\n")
        mtime = os.path.getmtime(path)
        m = {"version": 1, "sessions": {path: {"source_mtime": mtime}}}
        self.assertTrue(session_sync.needs_sync(m, path, force=True))


# ---------------------------------------------------------------------------
# Test: render_markdown
# ---------------------------------------------------------------------------

class TestRenderMarkdown(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def _render(self, messages, include_subagents=False):
        """Helper: write messages to JSONL, render to string."""
        jsonl_path = make_synthetic_jsonl(messages, os.path.join(self.tmpdir, "session.jsonl"))
        from io import StringIO
        out = StringIO()
        session_sync.render_markdown(jsonl_path, out, include_subagents=include_subagents)
        return out.getvalue()

    def test_header(self):
        md = self._render([make_user_message("hello")])
        self.assertIn("# Session: abcd1234", md)
        self.assertIn("**Date:** 2026-02-24", md)
        self.assertIn("**Project:** project", md)
        self.assertIn("**Working Directory:** /home/user/project", md)
        self.assertIn("**Git Branch:** main", md)
        self.assertIn("**Claude Version:** 2.1.55", md)

    def test_user_text(self):
        md = self._render([
            make_user_message("hello world"),
        ])
        self.assertIn("## User", md)
        self.assertIn("hello world", md)

    def test_tool_pairing(self):
        messages = [
            make_user_message("run ls"),
            make_assistant_message([
                {"type": "tool_use", "id": "tool1", "name": "Bash",
                 "input": {"command": "ls", "description": "list files"}},
            ]),
            make_tool_result_message("tool1", "file1\nfile2"),
        ]
        md = self._render(messages)
        self.assertIn("### Tool: Bash", md)
        self.assertIn("```bash", md)
        self.assertIn("ls", md)
        self.assertIn("<details><summary>Result</summary>", md)
        self.assertIn("file1\nfile2", md)

    def test_thinking_in_details(self):
        messages = [
            make_user_message("think about this"),
            make_assistant_message([
                {"type": "thinking", "thinking": "Let me consider..."},
                {"type": "text", "text": "Here's my answer"},
            ]),
        ]
        md = self._render(messages)
        self.assertIn("<details><summary>Thinking</summary>", md)
        self.assertIn("Let me consider...", md)
        self.assertIn("Here's my answer", md)

    def test_bash_fenced_block(self):
        messages = [
            make_user_message("run it"),
            make_assistant_message([
                {"type": "tool_use", "id": "t1", "name": "Bash",
                 "input": {"command": "echo hello"}},
            ]),
        ]
        md = self._render(messages)
        self.assertIn("```bash\necho hello\n```", md)

    def test_local_command_skipped(self):
        messages = [
            make_user_message("hi"),
            make_system_message("Switching to claude-sonnet-4-5", subtype="local_command"),
        ]
        md = self._render(messages)
        self.assertNotIn("## System", md)

    def test_system_rendered(self):
        messages = [
            make_user_message("hi"),
            make_system_message("Important context here"),
        ]
        md = self._render(messages)
        self.assertIn("## System", md)
        self.assertIn("Important context here", md)

    def test_is_error_marker(self):
        messages = [
            make_user_message("try this"),
            make_assistant_message([
                {"type": "tool_use", "id": "t1", "name": "Bash",
                 "input": {"command": "bad_cmd"}},
            ]),
            make_tool_result_message("t1", "command not found", is_error=True),
        ]
        md = self._render(messages)
        self.assertIn("**Error**", md)

    def test_sidechain_annotation(self):
        messages = [
            make_user_message("hello"),
            make_assistant_message(
                [{"type": "text", "text": "branched response"}],
                sidechain=True,
            ),
        ]
        md = self._render(messages)
        self.assertIn("*(sidechain)*", md)

    def test_subagents_excluded_by_default(self):
        messages = [
            make_user_message("hello"),
            make_progress_message(),
        ]
        md = self._render(messages, include_subagents=False)
        self.assertNotIn("Subagent", md)

    def test_subagents_included(self):
        messages = [
            make_user_message("hello"),
            make_progress_message(prompt="Search for files"),
        ]
        md = self._render(messages, include_subagents=True)
        self.assertIn("Subagent", md)
        self.assertIn("Search for files", md)

    def test_subagents_details_wrapped(self):
        messages = [
            make_user_message("hello"),
            make_progress_message(),
        ]
        md = self._render(messages, include_subagents=True)
        self.assertIn("<details>", md)
        self.assertIn("</details>", md)

    def test_signature_stripped(self):
        messages = [
            make_user_message("hello"),
            make_assistant_message([
                {"type": "text", "text": "Answer\n\nCo-Authored-By: Claude <noreply@anthropic.com>"},
            ]),
        ]
        md = self._render(messages)
        self.assertNotIn("Co-Authored-By:", md)
        self.assertIn("Answer", md)


# ---------------------------------------------------------------------------
# Test: discover_sessions
# ---------------------------------------------------------------------------

class TestDiscoverSessions(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.orig_projects_dir = session_sync.CLAUDE_PROJECTS_DIR
        session_sync.CLAUDE_PROJECTS_DIR = self.tmpdir

    def tearDown(self):
        session_sync.CLAUDE_PROJECTS_DIR = self.orig_projects_dir
        shutil.rmtree(self.tmpdir)

    def _make_project(self, slug, sessions):
        """Create a project dir with JSONL files."""
        proj_dir = os.path.join(self.tmpdir, slug)
        os.makedirs(proj_dir, exist_ok=True)
        paths = []
        for name, cwd in sessions:
            path = os.path.join(proj_dir, name)
            make_synthetic_jsonl([make_user_message("hello", cwd=cwd)], path)
            paths.append(path)
        return paths

    def test_finds_jsonl(self):
        self._make_project("-home-user-project", [
            ("sess1.jsonl", "/home/user/project"),
        ])
        sessions = session_sync.discover_sessions()
        self.assertEqual(len(sessions), 1)

    def test_skips_non_jsonl(self):
        proj_dir = os.path.join(self.tmpdir, "-home-user-proj")
        os.makedirs(proj_dir)
        with open(os.path.join(proj_dir, "notes.txt"), "w") as f:
            f.write("not a session")
        sessions = session_sync.discover_sessions()
        self.assertEqual(len(sessions), 0)

    def test_project_filter(self):
        self._make_project("-home-user-project", [
            ("s1.jsonl", "/home/user/project"),
        ])
        self._make_project("-home-user-other", [
            ("s2.jsonl", "/home/user/other"),
        ])
        sessions = session_sync.discover_sessions(project_filter="/home/user/project")
        self.assertEqual(len(sessions), 1)

    def test_empty_dir(self):
        sessions = session_sync.discover_sessions()
        self.assertEqual(len(sessions), 0)


# ---------------------------------------------------------------------------
# Test: export-current autodetect
# ---------------------------------------------------------------------------

class TestExportCurrentAutodetect(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.destdir = tempfile.mkdtemp()
        self.orig_projects_dir = session_sync.CLAUDE_PROJECTS_DIR
        session_sync.CLAUDE_PROJECTS_DIR = self.tmpdir

    def tearDown(self):
        session_sync.CLAUDE_PROJECTS_DIR = self.orig_projects_dir
        shutil.rmtree(self.tmpdir)
        shutil.rmtree(self.destdir)

    def test_picks_most_recent(self):
        proj_dir = os.path.join(self.tmpdir, "-home-user-project")
        os.makedirs(proj_dir)

        # Create two sessions for same cwd, different mtimes
        old_path = make_synthetic_jsonl(
            [make_user_message("old", cwd="/home/user/project",
                               session_id="old00000-0000-0000-0000-000000000000",
                               timestamp="2026-02-20T10:00:00Z")],
            os.path.join(proj_dir, "old.jsonl"),
        )
        # Ensure different mtime
        os.utime(old_path, (1000000, 1000000))

        new_path = make_synthetic_jsonl(
            [make_user_message("new", cwd="/home/user/project",
                               session_id="new00000-0000-0000-0000-000000000000",
                               timestamp="2026-02-24T10:00:00Z")],
            os.path.join(proj_dir, "new.jsonl"),
        )

        # Simulate argparse namespace
        class Args:
            dest = self.destdir
            project_dir = "/home/user/project"
            format = "markdown"
            include_subagents = False

        result = session_sync.cmd_export_current(Args())
        self.assertEqual(result, 0)

        # Check the exported file is from the newer session
        files = os.listdir(os.path.join(self.destdir, "project"))
        self.assertEqual(len(files), 1)
        self.assertIn("new00000", files[0])

    def test_no_match_returns_1(self):
        proj_dir = os.path.join(self.tmpdir, "-home-user-other")
        os.makedirs(proj_dir)
        make_synthetic_jsonl(
            [make_user_message("hello", cwd="/home/user/other")],
            os.path.join(proj_dir, "s.jsonl"),
        )

        class Args:
            dest = self.destdir
            project_dir = "/home/user/nonexistent"
            format = "markdown"
            include_subagents = False

        result = session_sync.cmd_export_current(Args())
        self.assertEqual(result, 1)


# ---------------------------------------------------------------------------
# Test: Integration (subprocess)
# ---------------------------------------------------------------------------

class TestIntegration(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.destdir = os.path.join(self.tmpdir, "output")
        os.makedirs(self.destdir)
        self.script = os.path.join(os.path.dirname(__file__), "session_sync.py")
        # Create a synthetic JSONL
        self.jsonl = make_synthetic_jsonl([
            make_file_history_snapshot(),
            make_user_message("What is 2+2?"),
            make_assistant_message([
                {"type": "thinking", "thinking": "Simple math"},
                {"type": "text", "text": "2+2 = 4"},
            ]),
        ], os.path.join(self.tmpdir, "test-session.jsonl"))

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_export_markdown(self):
        result = subprocess.run(
            [sys.executable, self.script, "export", self.jsonl, self.destdir],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Exported:", result.stdout)

        # Check output file exists
        project_dir = os.path.join(self.destdir, "project")
        self.assertTrue(os.path.isdir(project_dir))
        files = os.listdir(project_dir)
        self.assertEqual(len(files), 1)
        self.assertTrue(files[0].endswith(".md"))

        # Check content
        with open(os.path.join(project_dir, files[0])) as f:
            content = f.read()
        self.assertIn("# Session:", content)
        self.assertIn("2+2 = 4", content)

    def test_export_raw(self):
        result = subprocess.run(
            [sys.executable, self.script, "export", self.jsonl, self.destdir, "--format", "raw"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

        project_dir = os.path.join(self.destdir, "project")
        files = os.listdir(project_dir)
        self.assertEqual(len(files), 1)
        self.assertTrue(files[0].endswith(".jsonl"))

    def test_sync_all_manifest(self):
        """Test that sync-all creates a manifest."""
        # We need to set up a fake projects dir — use monkeypatch via env isn't easy,
        # so we test via direct export and then check manifest
        result = subprocess.run(
            [sys.executable, self.script, "export", self.jsonl, self.destdir],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0)

        manifest_path = os.path.join(self.destdir, ".claude-sync-manifest.json")
        self.assertTrue(os.path.exists(manifest_path))
        with open(manifest_path) as f:
            manifest = json.load(f)
        self.assertEqual(manifest["version"], 1)
        self.assertIn(self.jsonl, manifest["sessions"])

    def test_status(self):
        result = subprocess.run(
            [sys.executable, self.script, "status"],
            capture_output=True, text=True,
        )
        # Should work even with no dest (just counts sessions)
        self.assertIn("Sessions:", result.stdout + result.stderr)

    def test_force_reexport(self):
        # First export
        subprocess.run(
            [sys.executable, self.script, "export", self.jsonl, self.destdir],
            capture_output=True, text=True,
        )
        # Second export without force — should say "up to date"
        result = subprocess.run(
            [sys.executable, self.script, "export", self.jsonl, self.destdir],
            capture_output=True, text=True,
        )
        self.assertIn("up to date", result.stdout)

        # Third export with force — should re-export
        result = subprocess.run(
            [sys.executable, self.script, "export", self.jsonl, self.destdir, "--force"],
            capture_output=True, text=True,
        )
        self.assertIn("Exported:", result.stdout)


if __name__ == "__main__":
    unittest.main()
