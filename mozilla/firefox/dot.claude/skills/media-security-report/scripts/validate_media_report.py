#!/usr/bin/env python3
"""Check the structure of a standalone media-library security report.

A pre-submission aid, not a substitute for human review or a real
reproduction. It checks concepts rather than one exact Markdown template,
because reports may describe CLI, API, harness or FATE reproductions.

Three tiers of requirement apply to every report: the universal evidence core,
whatever the destination channel needs, and whatever the specific library's
published policy demands. FFmpeg's ten are not special-cased here -- they are
the core plus two rows of ``LIBRARY_REQUIREMENTS["ffvpx"]``.

Beyond requirements it enforces the rules that are easiest to get wrong by
hand: every link into the library's own repository must be pinned to the
vendored revision, every numbered crash stack must be complete and consecutive,
no downstream Firefox detail may leak into an upstream report, and metadata one
channel wants may be metadata another forbids.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import channel_policy  # noqa: E402
import media_lib_facts  # noqa: E402


FULL_HASH = re.compile(r"(?<![0-9a-f])[0-9a-f]{40}(?![0-9a-f])", re.I)
LINE_ANCHOR = re.compile(r"#L?\d+(?:-L?\d+)?\b")
STACK_FRAME = re.compile(r"#\d+[^\n]*(?:\.[A-Za-z0-9_+-]+:\d+|:\d+)")
STACK_FRAME_LINE = re.compile(r"(?m)^[ \t]*#(?P<number>\d+)(?:[ \t]+|$)")
STACK_OMISSION_LINE = re.compile(
    r"^\s*(?:\.{3}(?:.*\.{3})?|…|[<\[].*(?:omitted|skipped|elided).*[>\]])\s*$",
    re.I,
)
STACK_UNAVAILABLE = re.compile(r"stack\s+trace.*(?:not available|unknown)", re.I | re.S)
CODE_FENCE = re.compile(r"```.*?```", re.S)


def _find(text, patterns):
    return any(re.search(pattern, text, re.I | re.S) for pattern in patterns)


def _normalize_repo(url):
    """Strip scheme and trailing slash so two spellings of a repo compare equal."""
    if not url:
        return None
    return re.sub(r"^https?://", "", url).rstrip("/").lower()


def acceptable_ref(ref, facts, expected):
    """Is a source link pinned tightly enough?

    A full hash is always fine. The exact vendored revision string is fine too
    -- that is how a tag pin such as ``v1.3.6`` is admitted without loosening
    anything for a library that pins a hash, and why this compares against the
    live revision rather than trusting ``vendoring.tracking`` (libwebp declares
    ``tracking: tag`` yet pins a hash). A short-hash prefix is accepted only
    where the tree itself records a short hash.
    """
    lowered = ref.lower()
    if lowered in channel_policy.MOVING_REFS or lowered.startswith("refs/heads/"):
        return False
    if FULL_HASH.fullmatch(ref):
        return True
    if expected and ref == expected:
        return True
    kind = getattr(facts, "revision_kind", None) if facts else None
    if kind == "short-hash" and expected and re.fullmatch(r"[0-9a-f]{7,40}", lowered):
        lowered_expected = expected.lower()
        return lowered.startswith(lowered_expected) or lowered_expected.startswith(
            lowered
        )
    return False


# A correct report for an inline-only channel has to use the word "attachment"
# to explain the rule it is following ("not uploaded: attachments would be
# world-readable"). So match the shapes that *claim* something is attached
# rather than the bare word.
ATTACH_CLAIMS = re.compile(
    r"""
    \bsee\s+the\s+attached\b
    | \battached\s+(?:as|file|input|here|below|to\s+this|is\b)
    | \b(?:is|are|was|were)\s+attached\b
    | \battaching\s+(?:the|a|an|it)\b
    | \bI(?:'ve|\s+have)\s+attached\b
    | ^\s*attachments?\s*:
    """,
    re.I | re.M | re.X,
)


def _claims_attachment(text):
    """True when the report says the input is attached, ignoring caveats."""
    return bool(ATTACH_CLAIMS.search(CODE_FENCE.sub("", text)))


def _stack_blocks(text):
    """Return ``(frame_numbers, has_omission_marker)`` for each stack block."""
    blocks = []
    current = []
    has_omission = False
    for line in text.splitlines():
        match = STACK_FRAME_LINE.match(line)
        if match:
            number = int(match.group("number"))
            if current and number in (0, 1) and number <= current[-1]:
                blocks.append((current, has_omission))
                current = []
                has_omission = False
            current.append(number)
            continue
        if current and STACK_OMISSION_LINE.match(line):
            has_omission = True
            continue
        if current and (
            not line.strip() or re.match(r"^\s*(?:`{3,}|~{3,}|#{1,6}\s)", line)
        ):
            blocks.append((current, has_omission))
            current = []
            has_omission = False
    if current:
        blocks.append((current, has_omission))
    return blocks


def _check_stack_completeness(text):
    """Reject crash stacks that omit, duplicate, or reorder numbered frames."""
    errors = []
    for index, (frames, has_omission) in enumerate(_stack_blocks(text), start=1):
        if has_omission:
            errors.append(
                f"crash stack {index} uses an omission marker; include every "
                "numbered frame through the last frame"
            )
            continue
        first = frames[0]
        if first not in (0, 1):
            errors.append(
                f"crash stack {index} starts at frame #{first}; include every frame "
                "from #0 or #1 through the last frame"
            )
            continue
        for previous, current in zip(frames, frames[1:]):
            if current == previous + 1:
                continue
            if current > previous + 1:
                missing = ", ".join(
                    f"#{number}" for number in range(previous + 1, current)
                )
                errors.append(
                    f"crash stack {index} skips frame(s) {missing}; include the "
                    "full consecutive stack"
                )
            else:
                errors.append(
                    f"crash stack {index} has duplicate or out-of-order frame "
                    f"#{current} after #{previous}; preserve the original sequence"
                )
            break
    return errors


def check_report(text, library_id, profile_id, facts=None, expected_revision=None):
    """Return ``(errors, warnings)`` for one report body."""
    errors: list[str] = []
    warnings: list[str] = []

    if not text.strip():
        return ["report is empty"], []

    lib = channel_policy.LIBRARIES.get(library_id)
    has_upstream = lib.has_upstream if lib else True
    expected = expected_revision or getattr(facts, "revision", None)

    for req in channel_policy.requirements_for(library_id, profile_id):
        if not _find(text, req.patterns):
            message = f"missing {req.label} ({req.evidence})"
            (errors if req.severity == "error" else warnings).append(message)

    for rule in channel_policy.prohibitions_for(library_id, profile_id):
        if re.search(rule.pattern, text, re.I):
            message = f"{rule.label} must not appear here: {rule.reason}"
            (errors if rule.severity == "error" else warnings).append(message)

    if has_upstream:
        if expected and expected != "in-tree":
            if expected not in text:
                errors.append(
                    f"the vendored revision {expected} is never named in the report"
                )
        elif not FULL_HASH.search(text):
            errors.append("no full commit hash found and no vendored revision supplied")
    hashes = {h.lower() for h in FULL_HASH.findall(text)}
    if len(hashes) > 1:
        warnings.append(
            "report names multiple source hashes; verify each stack and result is labeled"
        )

    errors.extend(
        _check_source_links(text, lib, facts, expected, has_upstream, warnings)
    )

    if not STACK_FRAME.search(text) and not STACK_UNAVAILABLE.search(text):
        errors.append("no stack frame with a source line number found")
    errors.extend(_check_stack_completeness(text))
    if not LINE_ANCHOR.search(text):
        warnings.append("no line anchor found in a source link")

    if not re.search(
        r"(?:unknown|not available|not assigned|none\s+(?:assigned|known)|not applicable)",
        text,
        re.I,
    ):
        warnings.append(
            "report has no explicit unavailable/unknown marker; confirm all optional "
            "fields are present"
        )

    profile = channel_policy.PROFILES.get(profile_id)
    if (
        profile
        and profile.input_delivery == "inline-base64"
        and _claims_attachment(text)
    ):
        errors.append(
            "attachments on this channel are world-readable even on a confidential "
            "issue; deliver the input inline as base64 and do not describe it as attached"
        )
    for unknown in profile.known_unknowns if profile else ():
        warnings.append(f"unresolved for this channel: {unknown}")

    return errors, warnings


def _check_source_links(text, lib, facts, expected, has_upstream, warnings):
    """Every link into the library's own repository must be revision-pinned."""
    errors: list[str] = []

    if not has_upstream:
        # There is no upstream to cite: the code lives only in Firefox, so a
        # revision-pinned searchfox link is the correct citation here. This is
        # the one context where searchfox is required rather than forbidden.
        if not re.search(channel_policy.SEARCHFOX_REV, text, re.I):
            errors.append(
                "no revision-pinned searchfox link found (this component has no upstream, "
                "so cite mozilla-central at a fixed revision)"
            )
        return errors

    forge = getattr(facts, "forge", None) or (lib.forge if lib else None)
    repo = getattr(facts, "repo_url", None) or (lib.repo_url if lib else None)
    if not forge or forge not in channel_policy.FORGE_PATTERNS:
        warnings.append("forge is unknown, so source links were not checked")
        return errors

    base = _normalize_repo(repo)
    pattern = re.compile(channel_policy.FORGE_PATTERNS[forge], re.I)
    matched = 0
    for match in pattern.finditer(text):
        url = match.group(0)
        if base and not _normalize_repo(url).startswith(base + "/"):
            continue  # a link to some other project; not ours to police
        matched += 1
        # A commit or tree URL ends at the ref, so a Markdown link hands us the
        # closing delimiter and whatever punctuation follows it.
        ref = match.group("ref").rstrip(").,;:'\"")
        if not acceptable_ref(ref, facts, expected):
            errors.append(f"source link is not pinned to the vendored revision: {url}")
    if matched == 0:
        errors.append(
            f"no {forge} source link to {repo} found; cite the code you are reporting on"
        )
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("report", type=Path, help="the Markdown report to check")
    parser.add_argument("--library", required=True, help="library id or tree path")
    parser.add_argument("--profile", help="override the channel profile")
    parser.add_argument("--firefox", help="checkout root (default: walk up from cwd)")
    parser.add_argument(
        "--revision", help="expected vendored revision (skips tree lookup)"
    )
    parser.add_argument(
        "--no-tree", action="store_true", help="structure only; do not read a checkout"
    )
    args = parser.parse_args(argv)

    library_id, note = channel_policy.resolve_library(args.library)
    if library_id is None:
        print(f"ERROR: {note}", file=sys.stderr)
        print(
            "Known ids: " + ", ".join(sorted(channel_policy.LIBRARIES)), file=sys.stderr
        )
        return 2

    facts = None
    if not args.no_tree:
        root = media_lib_facts.find_checkout(args.firefox)
        if root is None:
            print("WARNING: no Firefox checkout found; checking structure only")
        else:
            facts = media_lib_facts.collect(library_id, root)

    profile_id = args.profile or channel_policy.profile_for(library_id)
    if profile_id not in channel_policy.PROFILES:
        print(f"ERROR: unknown profile {profile_id!r}", file=sys.stderr)
        return 2

    try:
        text = args.report.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"ERROR: cannot read report: {exc}", file=sys.stderr)
        return 2

    errors, warnings = check_report(text, library_id, profile_id, facts, args.revision)

    print(f"library: {library_id}    channel: {profile_id}")
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
