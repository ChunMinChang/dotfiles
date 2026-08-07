# Bug {bug_id} Root Cause Analysis

## Summary
- **Bug**: [Bug {bug_id}](https://bugzilla.mozilla.org/show_bug.cgi?id={bug_id})
- **Title**: {title}
- **Component**: {component}
- **Severity/Priority**: {severity} / {priority}
- **Status**: {status}
- **Public**: {Yes/No}
- **Analysis Date**: {YYYY-MM-DD}
- **Searchfox Revision**: [`{short_hash}`](https://searchfox.org/firefox-main/rev/{full_hash}) (pinned for all links in this document)

{2-3 sentence root cause finding. Update whenever root cause changes.}

## Build Requirements
{Standard debug build sufficient, OR:}
- **Build type**: ASan / TSan / Debug
- **Mozconfig**: See [`bug-{bug_id}-mozconfig`](./firefox/debug/bug-{bug_id}-mozconfig)
- **Rationale**: {Why this build type is needed}

## Security Rating
> **Include this section ONLY for security bugs** (any `sec-*` keyword or security group). Delete for non-security bugs.

Suggested rating: **sec-{level}** because:
- {Primary reason: attacker capability, trigger conditions, preconditions}
- {Exploitation scope: what can an attacker do? Content process only, sandbox escape, RCE, info-leak, etc.}
- {Why not higher: what limits severity — sandbox, preconditions, limited heap-shaping window, etc.}
- {Why not lower: what makes it more serious than the next level down}

## Failure Pattern
- **Platforms**: {which platforms affected, from Treeherder}
- **Test suites**: {e.g., mochitest-media-wmfme, mochitest-media}
- **Build types**: {debug/asan/opt}
- **Failure rate**: {consistent / intermittent with percentage if known}
- **Pattern**: {consistent = code is wrong, intermittent = race/resource/error-handling}
- **Trees**: {autoland, mozilla-central, try}
- **Date range**: {last 7 days from YYYY-MM-DD to YYYY-MM-DD}

## Hypothesis Tree
> Built at `Diagnose.5` (at least three candidates — single-hypothesis RCAs anchor
> too early) and re-ranked at `Diagnose.12` against the gathered evidence. Keep the
> refuted and pruned rows: showing what was considered and ruled out is most of the
> value, and it stops a later reader re-treading them.

| Hypothesis | Failure mechanism | Confirming evidence | Refuting evidence | Probe cost | Status |
|------------|-------------------|---------------------|-------------------|------------|--------|
| H1 ({short name}) | {how the bug would manifest if this were the cause} | {what we'd see in code/logs/test if true} | {what we'd see if false} | {minutes / hours / build required} | {primary \| to-test \| refuted \| assumption-only} |
| H2 ({short name}) | ... | ... | ... | ... | ... |
| H3 ({short name}) | ... | ... | ... | ... | ... |

**Primary**: `{H<n>}` — chosen for the highest confirm/refute ratio per unit of probe cost.
**Re-ranking notes**: {any hypothesis revived or demoted during Synthesis, and the evidence that moved it.}

## Third-Party Library Classification
> Include this section ONLY when the root cause involves vendored third-party code (`Diagnose.9` active). Delete for Firefox-only bugs.

- **Library**: {name} (vendored at `media/{lib}/` or `third_party/{lib}/`)
- **Upstream repo**: {upstream URL}
- **Vendored revision**: `{hash}`
- **T3 diagnostic result**: {Reproduces upstream / Does NOT reproduce upstream / Reproduces differently}
- **Confirmed scope**: {(a) Library bug / (b) Firefox integration / (a+b) Split scope / (c) Firefox local patches}
- **Branch followed**: {A / B / C}
- **Upstream report**: [`bug-{bug_id}-upstream-{library}.md`](./{library}/bug-{bug_id}-upstream-{library}.md) *(Branch A and C only)*

## Code Path Trace

### Firefox Code Path
[`EntryFunction`]({permanent-searchfox-link}) — {what it does}

1. [`Namespace::Caller`]({permanent-searchfox-link}#L{line}) — {description}
   - {What happens at this step, with evidence}
2. [`Namespace::Callee`]({permanent-searchfox-link}#L{line}) — {description}
   - {What goes wrong here, citing specific lines}
3. ...

### Third-Party Library Code Path
> Include this subsection for Branch A, Branch C, or whenever the trace enters vendored third-party code. Use upstream permanent links.

Library: {name} (upstream revision: `{hash}`)

1. [`upstream_function`]({permanent-upstream-link}#L{line}) — {description}
   - {What happens in the library code}
2. [`next_function`]({permanent-upstream-link}#L{line}) — {description}
   - {Where the defect occurs in the library}
3. ...

### Integration Boundary
> Include this subsection for Branch B and Branch C. Document where Firefox calls into the library and how results/errors propagate back.

- **Firefox → Library**: [`wrapper_call`]({searchfox-link}) calls [`lib_api`]({upstream-link})
- **Library → Firefox**: return value / callback / error code at [`handler`]({searchfox-link})
- **Contract violation** (if any): {what the library expects vs what Firefox does}

## Design Intention

**Broken invariant**: {One sentence. The property that the function contract below
implies should always hold, and that the root cause shows does not. Written by the
main agent during synthesis — this is the hand-off into the Reframe phase, which
builds its invariant table on top of it. Do not leave it blank.}

### Firefox Side
> For Branch B, Branch C, or Firefox-only bugs.

- **Introducing commit**: {hash} ([Bug {other_bug_id}](bugzilla-link))
- **Original purpose**: {What problem this code was originally solving}
- **Design rationale**: {Why the author chose this approach}
- **Constraints/tradeoffs**: {What limitations shaped the design}
- **Function contract**: {Preconditions, postconditions, invariants}
- **How root cause relates**: {Does the bug violate the original design, or reveal a gap in it?}

### Library Side
> For Branch A and Branch C. Use upstream commit references.

- **Introducing commit**: `{upstream_hash}` ({upstream commit message summary})
- **Original purpose**: {What problem this library code was solving}
- **Design rationale**: {Why the library authors chose this approach}
- **API contract / assumptions**: {Threading model, preconditions, documented or undocumented}
- **How root cause relates**: {Library bug, missing validation, undocumented limitation?}

## Root Cause
{Clear statement of WHY the bug occurs.}

### Verified Claims
- {Claim 1} — [`file:line`]({link})
- {Claim 2} — [`file:line`]({link})

### Assumptions
- [Assumption] {hypothesis 1} — needs {evidence} to confirm
- [Assumption] {hypothesis 2} — needs {evidence} to confirm

## Test Evidence

### Firefox Proof Tests
| Test | Framework | Purpose | Result |
|------|-----------|---------|--------|
| `{path/to/test or "none"}` | gtest/mochitest/WPT/crashtest/alternative evidence | Demonstrates {what} | FAIL (confirms root cause) / skipped with rationale |

### Library Standalone Tests
> Include for Branch A and Branch C only. Delete for Firefox-only bugs.

| Test | Framework | Repo | Purpose | Result |
|------|-----------|------|---------|--------|
| `{path/in/lib/tests}` | googletest/meson/custom | {library_name} @ `{hash}` | Demonstrates {what} | FAIL/PASS |

### Debug Logs and Instrumentation

**Firefox** (`firefox/debug/`):
- [`firefox/debug/bug-{bug_id}-{proof_id}-test-run.log`](./firefox/debug/bug-{bug_id}-{proof_id}-test-run.log) — One execution log per proof
- [`firefox/debug/bug-{bug_id}-debug-{desc}.log`](./firefox/debug/bug-{bug_id}-debug-{desc}.log) — Debug output
- [`firefox/debug/{NN}-test-{proof_id}-{desc}.patch`](./firefox/debug/{NN}-test-{proof_id}-{desc}.patch) — Test/evidence patch
- [`firefox/debug/{NN}-debug-firefox-{proof_id}.patch`](./firefox/debug/{NN}-debug-firefox-{proof_id}.patch) — Instrumentation

**Library** (`{library}/debug/`) *(Branch A/C only)*:
- [`{library}/debug/bug-{bug_id}-debug-lib-{desc}.log`](./{library}/debug/bug-{bug_id}-debug-lib-{desc}.log) — Debug output
- [`{library}/debug/01-test-{desc}.patch`](./{library}/debug/01-test-{desc}.patch) — Test patch (may include injection)
- [`{library}/debug/02-debug-lib-instrumentation.patch`](./{library}/debug/02-debug-lib-instrumentation.patch) — Instrumentation

### Fix Patches

State the selected shape for each destination. Delete the inapplicable examples:

- **Non-security + benign proof**: `{NN}-test-*.patch` then `{NN}-fix-*.patch`.
- **Security + benign proof**: `{NN}-fix-*.patch` then `{NN}-test-*.patch`.
- **Injection-only proof**: fix patches only; the proof remains in `debug/`.
- **No stable proof test**: fix patches plus the alternative verification log.

**Firefox** (`firefox/fix/`): {list the actual files in application order}

**Library** (`{library}/fix/`) *(Branch A/C only)*:
{list the actual files in application order; for a Branch-C PASS/hardening case,
do not list a nonexistent FAIL→PASS test patch}

### Test Notes
{Any notes on test robustness, FuzzingFunctions conversion, or why a test was skipped.}

## How to Reproduce and Verify

### Firefox

Run every reproduction in a disposable worktree rooted at the recorded
`SHERLOCK_BASE`; never reset or clean the developer's working tree.

#### 1. Build Firefox from source
```bash
# Use the appropriate mozconfig (standard debug, ASan, or TSan)
# See Build Requirements section above
cp {mozconfig path or inline} .mozconfig
./mach build
```
Always build from source — do not use artifact builds. Use `./mach build` for a
full build. For incremental rebuilds after C++/Rust-only changes: `./mach build binaries`.

#### 2. Apply the debug proof patch and run
```bash
git worktree add <scratch-worktree> --detach <SHERLOCK_BASE>
cd <scratch-worktree>
git am -3 <run-dir>/firefox/debug/<NN>-test-<proof-id>-<desc>.patch
./mach build          # rebuild with test added
./mach test {test_path} --headless
```
Expected result: **FAIL** — {brief description of expected failure}

#### 3. Capture debug logs (optional)
```bash
git am -3 <run-dir>/firefox/debug/<NN>-debug-firefox-<proof-id>.patch
./mach build          # rebuild with instrumentation
./mach test {test_path} --headless 2>&1 | tee firefox-debug.log
```
Look for `SHERLOCK:` prefixed lines in the output. Discard the disposable
worktree when done; do not mutate the original checkout.

#### 4. Apply the fix and verify
```bash
# In a fresh disposable worktree, apply firefox/fix/*.patch in documented order.
git am -3 <run-dir>/firefox/fix/*.patch
./mach build
./mach test {test_path} --headless
```
Expected result: **PASS**

### Third-Party Library
> Include this subsection for Branch A and Branch C only. Delete for Firefox-only bugs.

Use a disposable worktree at `{upstream_revision_hash}`. Apply `debug/` evidence
there; apply `fix/` patches in a separate fresh worktree and in documented order.

#### 1. Set up the library build environment
```bash
git clone {upstream_repo_url}
cd {library_name}
git checkout {upstream_revision_hash}
```
{Library-specific prerequisites and build setup instructions.}

#### 2. Apply the test patch and run
```bash
git am -3 {library}/debug/01-test-<desc>.patch
{build command}
{test command}
```
Expected result: **FAIL** (Branch A) or **PASS** (Branch C with undocumented limitation)

#### 3. Capture debug logs (optional)
```bash
git am -3 {library}/debug/02-debug-lib-instrumentation.patch
{rebuild command}
{test command} 2>&1 | tee lib-debug.log
```
Discard the disposable worktree when done.

#### 4. Apply the fix and verify
```bash
git am -3 <run-dir>/{library}/fix/*.patch
{rebuild command}
{test command}
```
Expected result: **PASS**, or the documented hardening assertion/handling result
for a Branch-C diagnostic that already passed before the fix.

## Related Context
- **Duplicates**: [Bug {other_bug_id}](bugzilla-link), [Bug {other_bug_id}](bugzilla-link)
- **Related bugs**: [Bug {other_bug_id}](bugzilla-link)
- **Recent changes**: {relevant commit hashes with summaries}
- **Existing tests**: [`path/to/test`]({searchfox-link})

## Review #1 Response
> Filled at the end of the **Diagnosis Review** phase, before the root-cause gate.
> Reviewer R's own words live in the exact latest root-cause review linked below; this is
> *our* response to all three reviewers. A "pass with fix-ups" from Reviewer L still
> needs an entry — that is the case most easily dropped.

| Reviewer | Verdict | Concern | Accepted? | What changed |
|---|---|---|---|---|
| L (links) | pass / fail | {…} | yes/no | {…} |
| T (tests) | pass / fail | {…} | yes/no | {…} |
| R (red-pen) | {approve \| approve-with-concerns \| revise \| reject \| redesign \| needs-more-info} | {…} | yes/no | {…} |

**Full red-pen review**: [`review/{exact_latest_rootcause_review_filename}`](./review/{exact_latest_rootcause_review_filename})

## Solution Track

> This document is the **diagnosis**. Solutions live in their own documents so
> this one stays stable ground — the agreed statement of why the bug happens. It
> stays untouched through Design and Decide; Consolidate does correct it if
> implementation proved something in it wrong, but any such correction is called out
> rather than made silently. Fill the links below as each phase produces its
> artifact; leave a phase's line out entirely if the run has not reached it.

| Phase | Document | What it holds |
|-------|----------|---------------|
| Reframe | [`bug-{bug_id}-principles.md`](./bug-{bug_id}-principles.md) | Why this is a problem, invariants, elimination candidates, named design principles |
| Design | [`bug-{bug_id}-solutions.md`](./bug-{bug_id}-solutions.md) | The option set, comparison matrix, roadmaps, change log |
| Decide | [`bug-{bug_id}-evaluation.md`](./bug-{bug_id}-evaluation.md) | Criteria, scoring, recommendation, review response |
| Decide | [`bug-{bug_id}-review.md`](./bug-{bug_id}-review.md) | Independent red-pen review of the solutions |
| Implement | [`bug-{bug_id}-followups.md`](./bug-{bug_id}-followups.md) | Follow-up and blocking issues |

### Agreed Approach
{Filled at the end of the run: which option was implemented, one sentence on why,
and a link to the evaluation doc's recommendation. If the first choice was
implemented and then reverted, say so and name what shipped instead — the full
history is in the solutions-doc Change log.}
