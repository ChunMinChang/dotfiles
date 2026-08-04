# FFmpeg security-report checklist

Use this checklist with the current [FFmpeg security page](https://ffmpeg.org/security.html).
The page requires ten pieces of information. A missing optional artifact is still
reported explicitly; do not silently omit the field.

## Ten required fields

| # | Report field | Minimum acceptable evidence |
| --- | --- | --- |
| 1 | Human reviewer(s) | Names or aliases of the person(s) who personally verified the report. Do not count a bot, fuzzer, or automation account as a human reviewer. |
| 2 | Finder credit | Human finder name(s) or alias(es), or an explicit statement that the finder and reviewer are the same. |
| 3 | Reproducible testcase | A copy/paste command or complete API/FATE harness, expected unfixed result, and uniquely named input attachments. Include build prerequisites and configuration. |
| 4 | Source identifier | Full 40-hex git commit hash for every claimed reproduction. Record separate hashes for the original, latest-upstream, and fixed runs when they differ. |
| 5 | Stack traces | Symbolized stack(s) with function names, source file, and line numbers, tied to the exact source hash and build. Keep raw logs as attachments when useful. |
| 6 | Analysis | Evidence-backed description of trigger, state transition, affected code, memory-safety consequence, and why the testcase reaches it. Separate verified facts from assumptions. |
| 7 | Introducing commit | The commit that introduced the behavior, if established by history. Include the full hash and explain the `git log`/blame comparison; otherwise write “unknown” and say what was checked. |
| 8 | Input-generation script | A runnable script that emits the attached input, if one exists. If no independent generator is available or can be verified, state that explicitly and explain why. |
| 9 | Proposed fix | A clean git-formatted patch, separate from the test patch, or an explicit statement that no patch is available. Verify that it applies to the named source revision. |
| 10 | CVE/related identifier | CVE, FFmpeg ticket/PR, or another relevant identifier, or “none assigned/known” at report time. Do not invent one. |

## Suggested report order

Keep this order unless the evidence demands another structure:

1. Title and one-paragraph impact summary.
2. Attribution and identifiers (reviewer, finder, CVE/related ID).
3. Source revisions and build environment.
4. Reproduction instructions and testcase attachment map.
5. Numbered **Code Path Trace**. Each item contains `function → function`, a
   short explanation, and revision-pinned source links with line anchors. Split
   READ and WRITE manifestations after the shared state path.
6. Stack traces, each labeled with revision, build, platform, and failure type.
7. Analysis/root cause and the distinction between verified facts and assumptions.
8. Introducing commit and history evidence.
9. Input-generation script status and attachment.
10. Proposed fix and git patch attachment.
11. Fixed/unfixed/latest validation matrix.
12. Explicit status for every checklist item that is unavailable or not applicable.

## Evidence rules

- Use full commit hashes, not branch names, tags without hashes, `HEAD`, or
  `master`. A report can cite multiple hashes, but every stack and source link
  must identify which one it belongs to.
- Use permanent source URLs. For the GitHub FFmpeg mirror, use
  `https://github.com/FFmpeg/FFmpeg/blob/<full-hash>/<path>#L<line>`.
  Every FFmpeg source URL in the report must use a full commit hash; never use
  `/blob/master/`, `/source/`, or another moving URL. Ordinary documentation,
  tracker, or identifier links do not need an FFmpeg commit hash.
- Keep line anchors close to the claim they support. Link the function definition,
  the call site, and the exact state assignment or memory access when those are
  important to the argument.
- Show the complete state transition. For stateful or frame-threaded codecs,
  explain worker contexts, reference/frame state, format state, lifecycle or
  flush transitions, and the packet/frame sequence in plain language.
- For an out-of-bounds read or write, identify the first bad value, the arithmetic
  that carries it to the destination pointer/allocation, the final access, and
  why the access is out of bounds. Explain non-obvious pointer arithmetic instead
  of assuming the reader knows it.
- Prefer an unfixed/fixed/latest matrix over a single “works” claim. Record
  compiler, configure flags, sanitizer/guard-page mode, thread count, round count,
  exit code, and signal/sanitizer classification.
- Keep debug logging and temporary instrumentation separate from the clean test
  and fix patches. Preserve raw logs as files rather than pasting huge logs into
  the report.

## Attachment rules

- Use unique names, for example `01-test-codec-read.patch`,
  `02-test-codec-write.patch`, `03-fix-codec.patch`, and
  `input-codec-trigger.bin`.
- Export patches with `git format-patch`; do not attach an uncommitted working-tree
  diff as the proposed fix. A test patch should apply and run independently; a
  fix patch should apply on top of the test patch.
- Include the input itself when possible. Embedded base64 is acceptable when the
  patch contains a complete reproducible harness; still state that no external
  file is required.
- If a script generated the input, include the script and its invocation. If no
  verified script is available, state that instead of presenting a guessed generator.

## Standalone-report hygiene

The recipient should be able to reproduce the library issue without downstream
infrastructure. Remove private tracker details, product-only call paths, local
absolute paths, credentials, and internal security ratings. It is fine to say
that the testcase originated in a downstream investigation, but the reproduction,
source analysis, and proposed fix must stand on their own.
