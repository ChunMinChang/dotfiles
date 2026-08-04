# Universal report core

Every report this skill produces contains the same evidence, whatever the
library and whatever the destination. Only the *packaging* varies — see
[channel-profiles.md](channel-profiles.md).

Why a fixed core when almost no project publishes requirements? Because the two
that do — FFmpeg's ten items and libjpeg-turbo's rules — are not really project
preferences. They are a description of what any maintainer needs before they can
act. A project that asks only for a version string still needs the stack, the
input and the analysis; it just has not written that down.

A missing item is still reported explicitly. Never silently omit a field: write
`Unknown`, `Not available`, or `Not applicable` with a reason.

## The eleven core items

| # | Item | Minimum acceptable evidence |
| --- | --- | --- |
| 1 | Human reviewer(s) | Names or aliases of the person(s) who personally verified the report. A bot, fuzzer, or automation account is not a human reviewer. |
| 2 | Finder credit | Human finder name(s) or alias(es), or an explicit statement that the finder and reviewer are the same. |
| 3 | Reproducible testcase | A copy/paste command or complete harness, the expected unfixed result, and a uniquely named input. Include build prerequisites and configuration. |
| 4 | Source identifier | The vendored revision the report applies to, plus every other revision claimed. Full hash where the project pins a hash; the exact tag where it pins a tag. |
| 5 | Stack traces | Symbolized stack(s) with function names, source file, and line numbers, tied to one exact revision and build. |
| 6 | Analysis | Evidence-backed description of trigger, state transition, affected code, memory-safety consequence, and why the testcase reaches it. Separate verified facts from assumptions. |
| 7 | Introducing commit | The commit that introduced the behavior, if history establishes it. Otherwise "unknown" plus what was checked. |
| 8 | Input-generation script | A runnable script that emits the attached input, if one exists. Otherwise say so and explain why. |
| 9 | Proposed fix | A clean git-formatted patch, separate from the test patch, or an explicit statement that no patch is available. |
| 10 | CVE/related identifier | CVE, ticket, or other identifier, or "none assigned/known" at report time. Never invent one. |
| 11 | Human origination and AI disclosure | Who verified this by hand, and whether and where AI was used. |

Item 11 is not optional politeness. FFmpeg opens its security page by asking for
"careful human verification" after "a spike in AI generated, false positives".
libjpeg-turbo requires that reports "originate from a human" and that you
"always indicate whether and where AI was used" — automated reporting from a
bot account gets the account banned. Chromium bans accounts for repeated
low-quality AI reports. Three independent projects converged on this, so it
belongs in every report regardless of destination.

## Suggested report order

Keep this order unless the evidence demands another structure:

1. Title and one-paragraph impact summary.
2. Attribution and identifiers (reviewer, finder, AI disclosure, CVE).
3. Source revisions and build environment.
4. Reproduction instructions and the testcase/input map.
5. Numbered **Code Path Trace**. Each item: `function → function`, a short
   explanation, and revision-pinned source links with line anchors. Split READ
   and WRITE manifestations after the shared state path.
6. Stack traces, each labeled with revision, build, platform, and failure type.
7. Analysis/root cause, separating verified facts from assumptions.
8. Introducing commit and history evidence.
9. Input-generation script status.
10. Proposed fix.
11. Fixed/unfixed/latest validation matrix.
12. Explicit status for every item that is unavailable or not applicable.

## Evidence rules

- **Pin every source link to the vendored revision.** Use the forge template
  that `media_lib_facts.py` prints for the library. Never `/blob/master/`,
  `/+/main/`, `HEAD`, or any other moving ref.
- **A tag is a legitimate pin when the tree pins a tag.** libjpeg (`3.1.4.1`),
  libogg (`v1.3.6`), libpng (`v1.6.58`) and libsrtp (`v2.8.0`) are pinned by
  tag in `moz.yaml`; a link to that tag is correct for them. It is *not*
  correct for a library pinned to a hash, even one whose `vendoring.tracking`
  says `tag` — libwebp declares `tracking: tag` and pins a hash.
- Keep line anchors next to the claim they support. Link the function
  definition, the call site, and the exact state assignment or memory access.
- Show the complete state transition. For stateful or frame-threaded codecs,
  explain worker contexts, reference/frame state, format state, lifecycle or
  flush transitions, and the packet/frame sequence in plain language.
- For an out-of-bounds read or write, identify the first bad value, the
  arithmetic that carries it to the destination pointer, the final access, and
  why the access is out of bounds. Explain non-obvious pointer arithmetic
  rather than assuming the reader follows it.
- Prefer an unfixed/fixed/latest matrix over a single "works" claim. Record
  compiler, configure flags, sanitizer/guard-page mode, thread count, round
  count, exit code, and signal/sanitizer classification.
- Keep debug logging and temporary instrumentation out of the clean test and
  fix patches. Preserve raw logs as files rather than pasting them inline.

## Artifact naming

Unique names, always — `01-test-<desc>.patch`, `02-test-<desc>.patch`,
`03-fix-<desc>.patch`, `input-<desc>.<ext>`. Never `input.bin`, `testcase`, or
`crash.log`; a maintainer handling several reports cannot tell them apart.
Preserve the source extension.

Export patches with `git format-patch`; never attach an uncommitted working-tree
diff as the proposed fix. A test patch should apply and run independently; a fix
patch should apply on top of it.

How the input itself reaches the maintainer is a channel decision, not a
report decision. See [channel-profiles.md](channel-profiles.md) — on one channel
an attachment is mandatory, on another it is world-readable.

## Standalone-report hygiene

The recipient must be able to reproduce the library issue without downstream
infrastructure. Remove private tracker details, product-only call paths, local
absolute paths, credentials, and internal security ratings.

Concretely, an upstream report must not contain: `bugzilla.mozilla.org` links,
`searchfox.org` links (cite the upstream forge instead), Phabricator links,
`sec-critical`/`sec-high`/`sec-moderate`/`sec-low` ratings, or `/home/<user>/`
paths. `validate_media_report.py` fails the report on each of these.

It is fine to say the testcase originated in a downstream investigation. The
reproduction, source analysis, and proposed fix must stand on their own.

Two inversions of this rule are deliberate:

- For a **Bugzilla-restricted** report the hygiene scan is off — the report *is*
  the Bugzilla bug, so Firefox detail belongs there.
- For a component with **no upstream** (`psshparser`, `gmp-clearkey`, …) a
  revision-pinned `searchfox.org/mozilla-central/rev/<hash>/` link is *required*
  rather than forbidden. There is no other permanent way to cite the code.
