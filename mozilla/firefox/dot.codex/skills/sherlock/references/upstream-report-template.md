# {library_name}: {concise issue title}

## Summary
- **Library**: {library_name}
- **Version/Revision**: `{upstream_revision_hash}`
- **Reported**: {YYYY-MM-DD}

{2-3 sentence description of the bug from the library's perspective. No mention of
Firefox, browsers, or how the issue manifests in any specific consumer. Describe the
issue purely in terms of the library's API, behavior, or internal logic.}

## Reproduction
**Input**: {what input triggers the issue — file, data, API call sequence}
**Steps**:
1. {step 1}
2. {step 2}
3. ...

**Expected**: {what the library should do}
**Actual**: {what the library does instead — crash, wrong output, assertion, etc.}

## Code Path Trace
1. [`function_name`]({permanent-upstream-link}#L{line}) — {description}
   - {What happens at this step}
2. [`next_function`]({permanent-upstream-link}#L{line}) — {description}
   - {Where the defect occurs}
3. ...

## Root Cause
{Clear statement of why the bug occurs, using only library-internal concepts.
Every claim must be backed by a code reference.}

## Test Case
**File**: {path to the standalone test in the library's test framework}
**Framework**: {googletest / meson test / custom / etc.}
**Result**: {FAIL on revision `{hash}` — brief failure | PASS diagnostic exposing
an undocumented contract/need for hardening}

{For Branch A, describe the failing proof. For a Branch-C PASS/hardening report,
state what the passing diagnostic establishes, what contract remains undocumented,
and what hardening behavior is requested. Do not claim a FAIL→PASS transition. If
the test is short enough, include inline; otherwise reference it. For security
issues, omit the reproducer and coordinate privately as required by Sherlock.}

## How to Reproduce

### 1. Set up the build environment
```bash
git clone {upstream_repo_url}
cd {library_name}
git checkout {upstream_revision_hash}
```

{Library-specific build prerequisites, e.g., "Requires CMake 3.16+, nasm, and
a C11 compiler." Adapt based on the library's own build documentation.}

### 2. Apply the test patch and build in a disposable worktree
```bash
git am -3 debug/01-test-<desc>.patch
{build commands — e.g.:}
{  cmake -B build -DCMAKE_BUILD_TYPE=Debug}
{  cmake --build build}
```

### 3. Run the diagnostic
```bash
{test command — e.g.:}
{  ctest --test-dir build -R <test_name>}
```
Expected result: **{FAIL | PASS diagnostic}** — {brief expected output and what it proves}

### 4. Capture debug logs (optional)
To see detailed trace output confirming the code path:
```bash
git am -3 debug/02-debug-lib-instrumentation.patch
{rebuild command}
{test command} 2>&1 | tee debug-output.log
```
The instrumentation adds `SHERLOCK:` prefixed log lines at key points in the
code path. Discard the disposable worktree afterwards; do not reset the original
checkout.

### 5. Apply the fix and verify
```bash
# In a fresh disposable worktree, apply fix/*.patch in documented order.
# Non-security benign series: test -> fix.
# Security benign series: fix -> test. Injection-only series: fix only.
git am -3 fix/*.patch
{rebuild command}
{test command}
```
Expected result: **PASS**, or the requested hardening behavior for an initially
passing Branch-C diagnostic.

## Suggested Fix
> Optional — include only if a fix has been verified against the test case.

{Description of the fix approach, in terms the library maintainers would use.}

{If a patch is available:}
**Patch**: See `fix/02-fix-<desc>.patch`
**Verified**: Standalone test passes after applying this fix.
