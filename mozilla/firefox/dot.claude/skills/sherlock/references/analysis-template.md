# Bug {bug_id} Root Cause Analysis

## Summary
- **Bug**: [Bug {bug_id}](https://bugzilla.mozilla.org/show_bug.cgi?id={bug_id})
- **Title**: {title}
- **Component**: {component}
- **Severity/Priority**: {severity} / {priority}
- **Status**: {status}
- **Public**: {Yes/No}
- **Analysis Date**: {YYYY-MM-DD}
- **Searchfox Revision**: [`{short_hash}`](https://searchfox.org/mozilla-central/rev/{full_hash}) (pinned for all links in this document)

{2-3 sentence root cause finding. Update whenever root cause changes.}

## Build Requirements
{Standard debug build sufficient, OR:}
- **Build type**: ASan / TSan / Debug
- **Mozconfig**: See [`bug-{id}-mozconfig`](./bug-{id}-mozconfig) in this directory
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

## Code Path Trace

### Entry Point
[`EntryFunction`]({permanent-searchfox-link}) — {what it does}

### Trace
1. [`Namespace::Caller`]({permanent-link}#L{line}) — {description}
   - {What happens at this step, with evidence}
2. [`Namespace::Callee`]({permanent-link}#L{line}) — {description}
   - {What goes wrong here, citing specific lines}
3. ...

### Third-Party Code
> Include this subsection only if the trace enters vendored third-party code.

Library: {name} (vendored revision: `{hash}`)
- [`upstream_function`]({permanent-upstream-link}) — {description}
- Scope: {library bug / Firefox integration issue / Firefox local patch}

## Design Intention
{Study of HOW and WHY the root cause code was introduced.}

- **Introducing commit**: {hash} ([Bug {id}](bugzilla-link))
- **Original purpose**: {What problem this code was originally solving}
- **Design rationale**: {Why the author chose this approach}
- **Constraints/tradeoffs**: {What limitations shaped the design}
- **Function contract**: {Preconditions, postconditions, invariants}
- **How root cause relates**: {Does the bug violate the original design, or reveal a gap in it?}

## Root Cause
{Clear statement of WHY the bug occurs.}

### Verified Claims
- {Claim 1} — [`file:line`]({link})
- {Claim 2} — [`file:line`]({link})

### Assumptions
- [Assumption] {hypothesis 1} — needs {evidence} to confirm
- [Assumption] {hypothesis 2} — needs {evidence} to confirm

## Test Evidence

### Proof Tests
| Test | Framework | Purpose | Result |
|------|-----------|---------|--------|
| `{path/to/test}` | gtest/mochitest/WPT/crashtest | Demonstrates {what} | FAIL (confirms root cause) |

### Debug Logs
- [`bug-{id}-debug-{desc}.log`](./bug-{id}-debug-{desc}.log) — {what it shows}
- [`bug-{id}-test-run.log`](./bug-{id}-test-run.log) — {test execution output}

### Test Notes
{Any notes on test robustness, FuzzingFunctions conversion, or why a test was skipped.}

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
