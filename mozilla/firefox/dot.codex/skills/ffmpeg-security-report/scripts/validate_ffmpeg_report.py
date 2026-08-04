#!/usr/bin/env python3
"""Check the minimum structure of a standalone FFmpeg security report.

This is a pre-submission aid, not a substitute for human review or a real
reproduction. It deliberately checks concepts rather than requiring one exact
Markdown template, because reports may describe CLI, API, FATE, or custom
harness reproductions.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit


REQUIREMENTS = [
    (
        "human reviewer",
        (r"human\s+reviewer", r"reviewer\s*[:)]", r"reviewed\s+by"),
        "name or an explicit unavailable/unknown status",
    ),
    (
        "finder credit",
        (r"finder\s+credit", r"credited?\s+(?:to|for)", r"human.*find"),
        "finder name or an explicit unavailable/unknown status",
    ),
    (
        "reproducible testcase",
        (r"reproduc", r"test\s*case", r"testcase", r"fate-", r"command\s+line"),
        "copy/paste command or complete harness description",
    ),
    (
        "source identifier",
        (
            r"source\s+(?:identifier|revision)",
            r"version\s*/?\s*revision",
            r"git\s+commit",
        ),
        "source/revision field plus a full commit hash",
    ),
    (
        "stack trace",
        (r"stack\s+trace", r"observed\s+crash", r"asan", r"sanitizer", r"#\d+"),
        "stack or explicit unavailable/unknown status",
    ),
    (
        "analysis/description",
        (r"analysis", r"root\s+cause", r"code\s+path", r"impact", r"description"),
        "evidence-backed issue description",
    ),
    (
        "introducing commit",
        (r"introduc(?:ing|ed)", r"first\s+affected", r"originat(?:ing|ed)", r"unknown"),
        "commit/history statement or explicit unknown status",
    ),
    (
        "input-generation script",
        (
            r"input[- ]generation",
            r"input\s+generator",
            r"generat(?:or|ing)\s+script",
            r"no\s+independent",
        ),
        "script or explicit unavailable status",
    ),
    (
        "git-formatted proposed fix",
        (
            r"git[- ]formatted",
            r"proposed\s+fix",
            r"suggested\s+fix",
            r"fix\s+patch",
            r"\.patch",
        ),
        "patch or explicit unavailable status",
    ),
    (
        "CVE/related identifier",
        (
            r"\bcve\b",
            r"related\s+identifier",
            r"none\s+(?:assigned|known)",
            r"not\s+assigned",
        ),
        "identifier or explicit none/unknown status",
    ),
]

FULL_HASH = re.compile(r"(?<![0-9a-f])[0-9a-f]{40}(?![0-9a-f])", re.I)
FFMPEG_SOURCE_URL = re.compile(
    r"https?://github\.com/FFmpeg/FFmpeg/(?:blob|commit|tree)/[^\s<>()\[\]\\\"']+",
    re.I,
)
LINE_ANCHOR = re.compile(r"#L\d+(?:-L?\d+)?")
STACK_FRAME = re.compile(r"#\d+[^\n]*(?:\.[A-Za-z0-9_+-]+:\d+|:\d+)")


def find_requirement(text: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, text, re.I | re.S) for pattern in patterns)


def check_report(path: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"cannot read report: {exc}"], []

    if not text.strip():
        errors.append("report is empty")
        return errors, warnings

    for label, patterns, evidence in REQUIREMENTS:
        if not find_requirement(text, patterns):
            errors.append(f"missing {label} ({evidence})")

    hashes = FULL_HASH.findall(text)
    if not hashes:
        errors.append("no full 40-hex git commit hash found")
    elif len(set(h.lower() for h in hashes)) > 1:
        warnings.append(
            "report names multiple source hashes; verify each stack and result is labeled"
        )

    source_urls = FFMPEG_SOURCE_URL.findall(text)
    if not source_urls:
        errors.append("no FFmpeg GitHub source/commit URL found")
    else:
        for source_url in source_urls:
            path_parts = urlsplit(source_url).path.split("/")
            # /FFmpeg/FFmpeg/{blob,commit,tree}/{full-commit-hash}/...
            source_ref = path_parts[4] if len(path_parts) > 4 else ""
            if not re.fullmatch(r"[0-9a-f]{40}", source_ref, re.I):
                errors.append(
                    f"FFmpeg source link is not pinned to a full commit hash: {source_url}"
                )
    if not LINE_ANCHOR.search(text):
        warnings.append("no #L line anchor found in a source link")
    if not STACK_FRAME.search(text) and not re.search(
        r"stack\s+trace.*(?:not available|unknown)", text, re.I | re.S
    ):
        errors.append("no stack frame with a source line number found")

    if not re.search(
        r"(?:unknown|not available|not assigned|none\s+(?:assigned|known)|not applicable)",
        text,
        re.I,
    ):
        warnings.append(
            "report has no explicit unavailable/unknown marker; confirm all optional fields are present"
        )

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="standalone FFmpeg Markdown report")
    args = parser.parse_args()

    errors, warnings = check_report(args.report)

    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}")
    if errors:
        print(f"FAILED: {len(errors)} error(s), {len(warnings)} warning(s)")
        return 1
    print(f"PASS: report satisfies structural checks ({len(warnings)} warning(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
