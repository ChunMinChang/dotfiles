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
- **Mozconfig**: See [`bug-{id}-mozconfig`](./firefox/debug/bug-{id}-mozconfig)
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

## Third-Party Library Classification
> Include this section ONLY when the root cause involves vendored third-party code (Step 1.5b active). Delete for Firefox-only bugs.

- **Library**: {name} (vendored at `media/{lib}/` or `third_party/{lib}/`)
- **Upstream repo**: {upstream URL}
- **Vendored revision**: `{hash}`
- **T3 diagnostic result**: {Reproduces upstream / Does NOT reproduce upstream / Reproduces differently}
- **Confirmed scope**: {(a) Library bug / (b) Firefox integration / (a+b) Split scope / (c) Firefox local patches}
- **Branch followed**: {A / B / C}
- **Upstream report**: [`bug-{id}-upstream-{library}.md`](./{library}/bug-{id}-upstream-{library}.md) *(Branch A and C only)*

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

### Firefox Side
> For Branch B, Branch C, or Firefox-only bugs.

- **Introducing commit**: {hash} ([Bug {id}](bugzilla-link))
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
| `{path/to/test}` | gtest/mochitest/WPT/crashtest | Demonstrates {what} | FAIL (confirms root cause) |

### Library Standalone Tests
> Include for Branch A and Branch C only. Delete for Firefox-only bugs.

| Test | Framework | Repo | Purpose | Result |
|------|-----------|------|---------|--------|
| `{path/in/lib/tests}` | googletest/meson/custom | {library_name} @ `{hash}` | Demonstrates {what} | FAIL/PASS |

### Debug Logs and Instrumentation

**Firefox** (`firefox/debug/`):
- [`firefox/debug/bug-{id}-test-run.log`](./firefox/debug/bug-{id}-test-run.log) — Test execution output
- [`firefox/debug/bug-{id}-debug-{desc}.log`](./firefox/debug/bug-{id}-debug-{desc}.log) — Debug output
- [`firefox/debug/01-test-{desc}.patch`](./firefox/debug/01-test-{desc}.patch) — Test patch
- [`firefox/debug/02-debug-firefox-instrumentation.patch`](./firefox/debug/02-debug-firefox-instrumentation.patch) — Instrumentation

**Library** (`{library}/debug/`) *(Branch A/C only)*:
- [`{library}/debug/bug-{id}-debug-lib-{desc}.log`](./{library}/debug/bug-{id}-debug-lib-{desc}.log) — Debug output
- [`{library}/debug/01-test-{desc}.patch`](./{library}/debug/01-test-{desc}.patch) — Test patch (may include injection)
- [`{library}/debug/02-debug-lib-instrumentation.patch`](./{library}/debug/02-debug-lib-instrumentation.patch) — Instrumentation

### Fix Patches

**Firefox** (`firefox/fix/`):
- [`firefox/fix/01-test-{desc}.patch`](./firefox/fix/01-test-{desc}.patch) — Regression test
- [`firefox/fix/02-fix-{desc}.patch`](./firefox/fix/02-fix-{desc}.patch) — Fix (on top of test)

**Library** (`{library}/fix/`) *(Branch A/C only)*:
- [`{library}/fix/01-test-{desc}.patch`](./{library}/fix/01-test-{desc}.patch) — Standalone test (if no injection needed)
- [`{library}/fix/02-fix-{desc}.patch`](./{library}/fix/02-fix-{desc}.patch) — Fix (on top of test)

### Test Notes
{Any notes on test robustness, FuzzingFunctions conversion, or why a test was skipped.}

## How to Reproduce and Verify

### Firefox

#### 1. Build Firefox from source
```bash
# Use the appropriate mozconfig (standard debug, ASan, or TSan)
# See Build Requirements section above
cp {mozconfig path or inline} .mozconfig
./mach build
```
Always build from source — do not use artifact builds. Use `./mach build` for a
full build. For incremental rebuilds after C++/Rust-only changes: `./mach build binaries`.

#### 2. Apply the test patch and run
```bash
git am -3 firefox/fix/01-test-<desc>.patch
./mach build          # rebuild with test added
./mach test {test_path} --headless
```
Expected result: **FAIL** — {brief description of expected failure}

#### 3. Capture debug logs (optional)
```bash
git am -3 firefox/debug/02-debug-firefox-instrumentation.patch
./mach build          # rebuild with instrumentation
./mach test {test_path} --headless 2>&1 | tee firefox-debug.log
```
Look for `SHERLOCK:` prefixed lines in the output.
To revert instrumentation:
```bash
git reset HEAD~1
git checkout -- .
```

#### 4. Apply the fix and verify
```bash
# Start from a clean tree with only the test patch applied
git am -3 firefox/fix/01-test-<desc>.patch
git am -3 firefox/fix/02-fix-<desc>.patch
./mach build
./mach test {test_path} --headless
```
Expected result: **PASS**

### Third-Party Library
> Include this subsection for Branch A and Branch C only. Delete for Firefox-only bugs.

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
To revert: `git reset HEAD~1 && git checkout -- .`

#### 4. Apply the fix and verify
```bash
git checkout .
git am -3 {library}/fix/01-test-<desc>.patch
git am -3 {library}/fix/02-fix-<desc>.patch
{rebuild command}
{test command}
```
Expected result: **PASS**

## Related Context
- **Duplicates**: [Bug {id}](bugzilla-link), [Bug {id}](bugzilla-link)
- **Related bugs**: [Bug {id}](bugzilla-link)
- **Recent changes**: {relevant commit hashes with summaries}
- **Existing tests**: [`path/to/test`]({searchfox-link})

## Proposed Solutions
> This section is empty in Phase 1. Filled during Phase 2 after user agrees with the root cause analysis.

### Option A: {name}
{Description of the approach.}

**Pros:**
- {pro 1}
- {pro 2}

**Cons:**
- {con 1}
- {con 2}

### Option B: {name}
{Description.}

**Pros:**
- {pro 1}

**Cons:**
- {con 1}

### Comparison
| Criterion | Option A | Option B |
|-----------|----------|----------|
| Pros | {summary} | {summary} |
| Cons | {summary} | {summary} |
| Effort | Low/Medium/High | Low/Medium/High |
| Risk | Low/Medium/High | Low/Medium/High |

### Agreed Approach
{Which option was selected and why, after Phase 2 discussion.}
