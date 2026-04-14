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
**Result**: FAIL on revision `{hash}` — {brief description of failure}

{If the test is short enough, include inline. Otherwise reference the file.}

## Suggested Fix
> Optional — include only if a fix has been verified against the test case.

{Description of the fix approach, in terms the library maintainers would use.}

{If a patch is available:}
**Patch**: {link to branch/commit in the local repo, or inline diff}
**Verified**: T3 standalone test passes after applying this fix.
