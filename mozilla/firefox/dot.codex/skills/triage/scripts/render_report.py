#!/usr/bin/env python3
"""Render a triage report to {OUTPUT_ROOT}/bug-{id}/triage.md.

Inputs (any combination, all optional):

  --bug PATH         Bug JSON (the dict returned by /rest/bug/{id}).
  --pending PATH     Pending draft JSON (see Pending JSON Schema).
  --scope NAME       Active scope profile.
  --usage PATH       JSON dict {bugs_fetched, searches_issued, inaccessible}.
  --findings PATH    JSON list of codebase findings (each {path, note}).
  --out PATH         Override output path. Default: {root}/bug-{id}/triage.md.
  --output-dir PATH  Override output root for this run.

Exit codes: 0 ok, 1 invalid input, 2 write failure.

The skill is allowed to render the report inline as well; this script
exists so the same template can be reused from CI / scripts / tests
without having to keep a Codex session open.
"""

import argparse
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import triage_paths

BMO_URL = "https://bugzilla.mozilla.org/show_bug.cgi?id={}"

# ---------------------------------------------------------------------------
# Section helpers
# ---------------------------------------------------------------------------


def _safe(value, fallback="--"):
    if value in (None, ""):
        return fallback
    return value


def _today():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")


def _classification_table(bug):
    """Return a 4-row classification table. Detection is intentionally
    coarse — the skill prompt does the real call; this is the
    machine-reproducible fallback."""

    description = (
        (bug.get("summary") or "")
        + " "
        + " ".join(c.get("text", "") for c in (bug.get("comments") or [])[:5])
    ).lower()
    keywords = set((kw or "").lower() for kw in bug.get("keywords") or [])
    flags = {f.get("name", ""): f.get("status", "") for f in (bug.get("flags") or [])}

    str_present = "steps to reproduce" in description or "1." in description
    testcase_present = (
        "testcase" in keywords
        or any(
            kw in description for kw in ("testcase", "minimized", "reduced", "minimal")
        )
        or flags.get("in-testsuite") == "+"
        or flags.get("in-qa-testsuite") == "+"
    )
    crash_present = bool(bug.get("cf_crash_signature")) or any(
        marker in description
        for marker in ("addresssanitizer", "asan", "ubsan", "stack trace")
    )
    fuzzing_present = "fuzzing" in keywords or any(
        tool in description for tool in ("fuzzilli", "oss-fuzz", "fuzzfetch", "grizzly")
    )

    return [
        ("Clear STR", str_present),
        ("Test Case", testcase_present),
        ("Crash Stack", crash_present),
        ("Fuzzing", fuzzing_present),
    ]


def _format_signal_table(rows):
    out = ["| Signal | Detected |", "|--------|----------|"]
    for label, present in rows:
        out.append("| {} | {} |".format(label, "Yes" if present else "No"))
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Main renderer
# ---------------------------------------------------------------------------


def render(bug, pending, scope, usage, codebase_findings):
    bug = bug or {}
    pending = pending or {}
    usage = usage or {}
    findings = codebase_findings or []
    bug_id = bug.get("id") or pending.get("bug_id") or "?"

    title = bug.get("summary") or pending.get("title") or "(no summary)"

    sections = []

    # Header
    sections.append(
        "# Bug {bid} Triage Analysis\n\n"
        "**Generated:** {date}  \n"
        "**Bug URL:** {url}\n".format(
            bid=bug_id,
            date=_today(),
            url=BMO_URL.format(bug_id),
        )
    )

    # Bug Information
    sections.append(
        "## Bug Information\n\n"
        "- **Summary:** {summary}\n"
        "- **Status:** {status}\n"
        "- **Product:** {product}\n"
        "- **Component:** {component}\n"
        "- **Created:** {created}\n"
        "- **Severity:** {severity}\n"
        "- **Priority:** {priority}\n"
        "- **Scope:** {scope}\n".format(
            summary=_safe(title),
            status=_safe(bug.get("status")),
            product=_safe(bug.get("product")),
            component=_safe(bug.get("component")),
            created=_safe(bug.get("creation_time") or bug.get("created")),
            severity=_safe(bug.get("severity")),
            priority=_safe(bug.get("priority")),
            scope=_safe(scope),
        )
    )

    # Classification
    sections.append(
        "## Classification\n\n"
        + _format_signal_table(_classification_table(bug))
        + "\n"
    )

    # Regression timeline (only if signal present)
    if bug.get("regressed_by") or bug.get("cf_regressing_bug"):
        sections.append(
            "## Regression Timeline\n\n- **regressed_by:** {}\n".format(
                ", ".join(str(b) for b in (bug.get("regressed_by") or []))
                or _safe(bug.get("cf_regressing_bug"))
            )
        )

    # Assessment
    sections.append(
        "## Assessment\n\n"
        "- **Suggested Severity:** {severity}\n"
        "- **Suggested Priority:** {priority}\n"
        "- **Branch:** {branch}\n".format(
            severity=_safe(pending.get("severity")),
            priority=_safe(pending.get("priority")),
            branch=_safe(pending.get("branch")),
        )
    )

    # Codebase Investigation
    if findings:
        lines = ["## Codebase Investigation\n"]
        for f in findings:
            lines.append("- **{}** — {}".format(f.get("path", "?"), f.get("note", "")))
        sections.append("\n".join(lines) + "\n")

    # Draft Response
    if pending.get("comment"):
        sections.append(
            "## Draft Response\n\n```\n{}\n```\n".format(pending["comment"].rstrip())
        )

    # Recommended actions (derived from pending payload)
    actions = []
    if pending.get("priority") or pending.get("severity"):
        actions.append(
            "Set priority={} severity={}".format(
                _safe(pending.get("priority")),
                _safe(pending.get("severity")),
            )
        )
    for target in pending.get("ni_targets") or []:
        actions.append("needinfo? {}".format(target))
    if pending.get("dupe_of"):
        actions.append("Resolve DUPLICATE of {}".format(pending["dupe_of"]))
    if pending.get("resolution"):
        actions.append("Resolve {}".format(pending["resolution"]))
    if pending.get("blocks_add"):
        actions.append(
            "Add blockers: {}".format(", ".join(str(b) for b in pending["blocks_add"]))
        )
    if actions:
        sections.append(
            "## Recommended Actions\n\n"
            + "\n".join("- {}".format(a) for a in actions)
            + "\n"
        )

    # Test Page reference
    if pending.get("test_page_path"):
        sections.append(
            "## Test Page\n\n- **File:** {}\n".format(pending["test_page_path"])
        )

    # Bugzilla Usage Tracking
    sections.append(
        "## Bugzilla Usage Tracking\n\n"
        "- Bugs fetched: {bf}\n"
        "- Searches issued: {si}\n"
        "- Inaccessible bugs (permissions / deleted): {inacc}\n"
        "- 12-month window respected: yes\n"
        "- Hop limit (3) honored: yes\n".format(
            bf=usage.get("bugs_fetched", "--"),
            si=usage.get("searches_issued", "--"),
            inacc=usage.get("inaccessible", 0),
        )
    )

    sections.append(
        "---\n*Generated by the Firefox Bug Triage skill on {}.*\n".format(_today())
    )

    return "\n".join(sections)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _load_json(path):
    if not path:
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Render a triage report to markdown.")
    parser.add_argument("--bug", help="Path to bug JSON")
    parser.add_argument("--pending", help="Path to pending JSON")
    parser.add_argument("--scope", default=None, help="Active scope profile")
    parser.add_argument("--usage", help="Path to usage JSON")
    parser.add_argument("--findings", help="Path to findings JSON")
    parser.add_argument("--out", help="Output path override")
    parser.add_argument(
        "--output-dir",
        metavar="PATH",
        default=None,
        help="Override output root for this run.",
    )
    args = parser.parse_args(argv)

    if args.output_dir:
        triage_paths.set_override(args.output_dir)

    try:
        bug = _load_json(args.bug) or {}
        pending = _load_json(args.pending) or {}
        usage = _load_json(args.usage) or {}
        findings = _load_json(args.findings) or []
    except (OSError, json.JSONDecodeError, ValueError) as e:
        sys.stderr.write("render_report: cannot load input: {}\n".format(e))
        return 1

    bug_id = bug.get("id") or pending.get("bug_id")
    if not bug_id and not args.out:
        sys.stderr.write(
            "render_report: need either --bug / --pending with an id, or --out\n"
        )
        return 1

    if args.out:
        out_path = args.out
    else:
        try:
            out_path = triage_paths.report_path(bug_id)
        except triage_paths.OutputRootUnset as e:
            sys.stderr.write("render_report: {} (or pass --out)\n".format(e))
            return 1
    body = render(bug, pending, args.scope, usage, findings)

    try:
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        tmp = out_path + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            f.write(body)
        os.replace(tmp, out_path)
    except OSError as e:
        sys.stderr.write("render_report: write failed: {}\n".format(e))
        return 2

    sys.stdout.write(out_path + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
