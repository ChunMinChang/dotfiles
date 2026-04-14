---
name: sherlock
description: >
  Root cause analysis for Firefox bugs with evidence-based code tracing,
  permanent source links, and proof tests. Two phases: diagnose, then discuss solutions.
argument-hint: "<bug-id> [output-dir] [report-path-or-dir]"
allowed-tools:
  - Bash(git:*)
  - Bash(jj:*)
  - Bash(searchfox-cli:*)
  - Bash(bmo-to-md:*)
  - Bash(./mach:*)
  - Bash(.claude/skills/sherlock/sherlock-config:*)
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - AskUserQuestion
  - WebFetch
  - TaskCreate
---

# Sherlock: Root Cause Analysis

Follow `references/source-permalinks.md` for ALL source and documentation references.
Follow `references/spec-check.md` when verifying web specification compliance.
Follow `references/gecko-architecture.md` for Gecko architecture lookups.

This skill has two phases:
1. **Root Cause Analysis** — evidence-based diagnosis with permanent source links,
   code path traces, and proof tests. Focus entirely on WHY the bug occurs.
2. **Solution Discussion** — propose and discuss solutions with the user. Only after
   the user agrees with the Phase 1 analysis.

**Arguments:** $0

Parse the arguments:
- First numeric token = **bug ID** (mandatory)
- Tokens containing `/` = path arguments. Disambiguate by checking the target:
  - If it's an existing directory → **output-dir**
  - If it's an existing file → **report-path**
  - If two path tokens are given, first = output-dir, second = report-path
  - If it's a non-existing path ending with `/` or looks like a directory → output-dir

---

## Gotchas

1. **Every claim needs evidence or `[Assumption]` label** — do not state hypotheses
   as facts. Read the code before making any claim about code behavior.
2. **ALWAYS use revision-pinned links** — read `references/source-permalinks.md`.
   Never use trunk/tip URLs (`mozilla-central/source/...`) in the analysis doc.
3. **Tests are PROOFS for root cause claims** — they must demonstrate the root cause
   is correct. They are reusable for TDD later, but their primary purpose here is evidence.
4. **Debug logs go in separate files** — never inline multi-line log output in the
   analysis doc. Store as `bug-{id}-debug-{desc}.log` and reference with relative links.
5. **Do NOT write solutions in Phase 1** — Phase 1 is purely diagnostic. Solutions
   come in Phase 2 after user agreement.
6. **Private bugs** — never log titles, descriptions, components, or root cause details
   outside the output directory. History log for private bugs: `date | bug_id | PRIVATE` only.
7. **Check normal/debug build BEFORE requiring ASan/TSan** — try reproducing in
   current build first, then debug build, then sanitizer builds.
8. **NEVER read, parse, or print any API key** — all API access goes through
   `sherlock-config` or `bmo-to-md`. Never read TOML config files containing keys.
   Never use `python3` to parse config files.

---

## Preliminary: Resolve Config and Inputs

### Check Setup

Run the setup check to verify all prerequisites:
```bash
.claude/skills/sherlock/sherlock-config --check-setup
```

This reports status of: API key availability, `bmo-to-md` installation,
`searchfox-cli` availability, and configured output directory.
If any prerequisite is missing, present options to the user.

### Resolve Output Directory

Priority:
1. CLI argument (if a path argument was identified as output-dir)
2. `sherlock-config --get-output-dir` (reads `~/.config/sherlock/config.toml`)
3. Ask the user via AskUserQuestion: "Where should I put the analysis report?"

```bash
mkdir -p <output-dir>
```

### Fetch Bug Report

**If report-path was provided**: read it directly. Look for `summary.md` or
`bug-*.md` files if it's a directory.

**If not provided**: use sherlock-config to fetch:
```bash
.claude/skills/sherlock/sherlock-config --fetch-bug <bug_id> -o <output-dir>/bug-<id>-report
```

The helper script orchestrates `bmo-to-md` (with API key export if needed) or
falls back to the Bugzilla REST API. See `sherlock-config --help` for details.

**If sherlock-config fails**: try MCP for public bugs:
```
mcp__moz__get_bugzilla_bug(bug_id: {bug_id})
```

**Determine Public vs Private:**
- MCP returns content → **Public: Yes**
- MCP returns "Bug not found" or authorization error → **Public: No**

### Resolve Searchfox Revision (Session-Wide)

Pin a searchfox revision for the entire session so all links are permanent:

1. Get local HEAD: `git rev-parse HEAD`
2. Validate on searchfox: `WebFetch https://searchfox.org/mozilla-central/rev/<hash>/moz.configure`
   - If the page loads (200): use this hash as `$SHERLOCK_REV`
   - If 404 (not yet indexed): fetch `https://searchfox.org/mozilla-central/source/moz.configure`
     and extract the latest indexed revision from the page
3. Use `$SHERLOCK_REV` for ALL searchfox links in this session
4. For ESR/beta branches: repeat with the appropriate repo ID (e.g., `firefox-esr128`)

---

## Phase 1: Root Cause Analysis

### Step 1.1: Understand the Bug

Extract from the bug report:
- Bug title and description
- Component
- Steps to reproduce (STR)
- Expected vs actual behavior
- Recent comments and discussion
- Attached testcases or reproduction scripts
- Keywords (check for `sec-*` keywords: sec-high, sec-moderate, sec-low, sec-critical)
- Related bugs, duplicates, depends/blocks

If the bug has any `sec-*` keyword or is in a security group, the analysis doc
MUST include a **Security Rating** section.

### Step 1.2: Check Duplicates and Related Bugs

If the bug lists any duplicates, fetch each using:
```bash
.claude/skills/sherlock/sherlock-config --fetch-bug <duplicate_id> -o <output-dir>/bug-<duplicate_id>-report
```
Or MCP for public bugs.

Duplicates often contain:
- Additional STR or reproduction scripts
- Independent stack traces that confirm or refine the root cause
- Attached testcases (`testcase` keyword)
- Commenter analysis that narrows the failure condition
- Different affected versions or platforms

Merge all findings. If a duplicate adds a meaningfully different perspective,
note it under **Related Context** in the analysis doc.

### Step 1.3: Failure Pattern Analysis

Fetch the Treeherder API for failure distribution (last 7 days relative to today):
```
WebFetch: https://treeherder.mozilla.org/api/failuresbybug/?startday=YYYY-MM-DD&endday=YYYY-MM-DD&tree=all&bug=<id>
```

Extract:
- **Platforms** (e.g., Windows 11 only → OS-specific; Linux+Mac → cross-platform)
- **Test suites** (e.g., `mochitest-media-wmfme` → Windows Media Foundation Engine)
- **Build types** (debug/asan/opt)
- **Failure count and trees** (autoland, mozilla-central, try)

**Classify the failure pattern:**

| Pattern | Meaning | Approach |
|---------|---------|----------|
| **Always fails** | Code is wrong or missing | Find the broken code path |
| **Intermittent** | Race, resource, error-handling | Ask: what happens on rare failures? |

**For intermittent bugs, reason in this order:**
1. **Test robustness**: Does the test properly handle all error paths? `Promise.all`
   hangs if any promise never resolves/rejects.
2. **Error propagation gaps**: Missing `RejectPromises` call turns decode error into silent hang.
3. **Concurrent vs sequential**: Resource contention (hardware decoder session limits).
   Test by running items sequentially — if failure disappears, contention is confirmed.
4. **Platform-specific conditions**: Hardware, OS version, driver.

**Never assume** that because a test occasionally fails, the feature is broken.
If it passes 95% of the time, something rare causes the failure.

### Step 1.4: Research Code Paths

Use searchfox-cli for symbol lookups:
```bash
searchfox-cli --id <keyword> --cpp -l 50
searchfox-cli --define <ClassName>
searchfox-cli -q blob --path dom/media <search-term>
```

For architecture questions, follow `references/gecko-architecture.md` for structured
approaches to understanding Gecko control flow, ownership, and subsystem interactions.

For web-exposed features, consult `references/spec-check.md` to verify spec compliance.

Identify 3-5 key files. Check recent history:
```bash
jj log -r 'file(path/to/file)' -l 10
# or: git log --follow --oneline path/to/file | head -10
```

For third-party libraries, consult `references/upstream-libs.md`.

### Step 1.5: Trace Code Paths with Permanent Links

Read `references/source-permalinks.md` for URL patterns. For EVERY code reference,
produce a revision-pinned link using `$SHERLOCK_REV`.

Format as a numbered trace:
```
1. [`Class::Method`](https://searchfox.org/mozilla-central/rev/<hash>/path#line) — description
2. [`Next::Call`](link) — what happens, with evidence
```

For third-party code, use upstream permanent links from `references/upstream-libs.md`:
1. Read vendored revision: `git show HEAD:media/<lib>/moz.yaml | grep revision`
2. Construct upstream URL using the forge pattern from the library table

### Step 1.5b: Third-Party Library Sub-Workflow (Conditional)

If the root cause involves vendored third-party code (file paths matching
`references/upstream-libs.md`), activate this sub-workflow:

#### T1: Check for Local Upstream Repo

Ask the user via AskUserQuestion:
- "The issue involves {library} ({upstream_url}). Do you have a local clone?"
- If yes: "Where is it?"
- If no: "Should I clone it? Where?" (suggest `~/Work/{lib-name}`)

#### T2: Scope the Issue

Evaluate whether the bug is:
- **(a) In the library itself** — would reproduce with standalone upstream tests
- **(b) In Firefox's integration** — library works correctly but Firefox's wrapper
  code, IPC, threading, or lifecycle management causes the issue
- **(c) In Firefox's local patches** — check `media/{lib}/` for `.patch` files or
  diffs from the upstream revision

Document the classification in the analysis doc.

#### T3: Create Standalone Library Tests

If the issue may be in the library itself (scope a):
1. Navigate to the local library repo
2. Identify the library's test framework (see `references/upstream-libs.md`)
3. Create a minimal test case using the library's native test framework
4. Run the test to confirm: "Bug reproduces in upstream {lib} at revision {hash}"
   or "Bug does NOT reproduce upstream — Firefox integration issue"

#### T4: Divergent Fix Strategy

**For the library (upstream fix):**
- Analyze with broader scope — long-term, architecturally sound solutions
- Larger changes are acceptable for upstream
- Note: this fix needs to be submitted upstream then vendored

**For Firefox (integration fix / local patch):**
- Prefer smaller, well-scoped patches
- If Firefox already applies patches on top, a local patch may be more pragmatic
- Consider: can we work around the library bug in the integration layer?

Both strategies appear in Phase 2's Proposed Solutions with their own
Pros/Cons/Effort/Risk rows.

### Step 1.6: Study Design Intention

After identifying the root cause code, study HOW and WHY it was introduced:

1. **Find the introducing commit:**
   ```bash
   git log --oneline --follow -S "<key_symbol>" -- <file> | head -10
   git blame -L <line>,<line> <file>
   ```
   Or jj equivalents:
   ```bash
   jj annotate <file>
   jj log -r 'ancestors(trunk())' -T builtin_log_oneline -s -- <file> | head -30
   ```

2. **Read the full commit message and linked bug** for the introducing change.
   Understand: what problem was this code originally solving? What was the design
   rationale? What constraints or tradeoffs did the author face?

3. **Study the surrounding function/module design:**
   - What is the function's contract? (preconditions, postconditions)
   - What invariants does the module maintain?
   - Are there related functions that follow the same pattern?
   - Is this part of a larger state machine or protocol?

4. **Document in the analysis doc** under "Design Intention":
   - Original purpose of the code
   - Design constraints/tradeoffs the author faced
   - Why the current approach was chosen
   - How the root cause violates the original design intention (or reveals a gap)

This understanding is critical for Phase 2: solutions that respect the original
design intention are more likely to be correct and maintainable than patches that
only address the symptom.

### Step 1.7: Verify All Claims

**Two-tier rule — every statement must be classified:**

| Tier | Label | Meaning | Requirement |
|------|-------|---------|-------------|
| **Verified** | *(no label)* | Confirmed by code, logs, or data | Cite the file:line or log entry |
| **Assumption** | `[Assumption]` | Plausible but unconfirmed | Label clearly; state what would confirm/refute |

**Before writing each claim, ask yourself:**
1. **Code behavior** — "Function X does Y": Did you read that code? If not, read it
   or label `[Assumption]`.
2. **Causation** — "X causes Y": Can you trace the exact call path? If inferring,
   label `[Assumption]`.
3. **Environment** — "Fails on some drivers": Do you have log evidence? If not,
   label `[Assumption: needs log analysis]`.
4. **Absolutes** — "always", "never", "only": Read the code to confirm.

**Mandatory checks before writing Root Cause:**
- [ ] Read every function in the described call path
- [ ] For each error code (HRESULT, nsresult), trace to source
- [ ] If you claim "X never Y", confirm no branch does Y
- [ ] For intermittency: distinguish known trigger vs plausible explanation

### Step 1.8: Evaluate and Create Proof Tests

Read `references/test-frameworks.md` for framework selection and FuzzingFunctions mapping.

#### 1.8a: Check Bug Attachments for Existing Testcases

```bash
.claude/skills/sherlock/sherlock-config --fetch-attachments <bug_id> -o <output-dir>/bug-<id>-attachments
```

If a testcase exists and uses `FuzzingFunctions`, apply the mapping table from
`references/test-frameworks.md`. Auto-convert to the appropriate framework.

#### 1.8b: Determine Test Framework

Use the decision tree from `references/test-frameworks.md`:
- Crash → crashtest (HTML-triggerable) or gtest (C++ only)
- Web-exposed + spec-defined → WPT (follow `references/spec-check.md` first)
- Web-exposed + Firefox-specific → mochitest
- Internal C++/Rust → gtest

#### 1.8c: Check Build Requirements BEFORE Writing Tests

1. Try reproducing in the **current build** first
2. If that fails, try a **standard debug build**
3. Only if needed: **ASan/TSan**

Signals for sanitizer builds:
- "data race" / "race condition" → TSan
- "heap-use-after-free" / "buffer-overflow" / ASan signature → ASan
- Bug report explicitly mentions sanitizer output

If a special build is needed:
- Read the mozconfig presets from `references/test-frameworks.md`
- Auto-generate a mozconfig file: `<output-dir>/bug-<id>-mozconfig`
- Present to user for review via AskUserQuestion before building
- The user can invoke `/mozconfig` for full interactive configuration if preferred

#### 1.8d: Write Proof Test

The test must:
- **FAIL without fix** — proving the bug exists (the root cause claim is correct)
- Be designed to **PASS after fix** — making it reusable for TDD development later
- Serve as **EVIDENCE** for the root cause claim

#### 1.8e: Add Debugging Instrumentation

Add targeted logging (MOZ_LOG, printf, `info()`) to confirm the traced code path
is actually hit during test execution. This produces the debug logs that verify
your code path trace.

#### When NOT to Write a Test

Skip the test entirely when:
- Data race with narrow, platform-gated race window (flaky test adds CI noise)
- Code can't be exercised from JS in standard CI configuration
- Detection rate in typical CI run would be well below 50%

Crashtest is acceptable (~50% detection) when:
- Bug causes outright crash in normal CI builds
- Can run on platforms where crash occurs
- Cheap to write (simple HTML page triggering crash path)

If no test: document rationale in Test Evidence section of the analysis doc.

### Step 1.9: Run Tests and Capture Debug Logs

Execute tests and capture output:
```bash
./mach test <path> --headless 2>&1 | tee <output-dir>/bug-<id>-test-run.log
```

Additional debug logs go in separate files:
```
<output-dir>/bug-<id>-debug-<description>.log
```

**Evaluate results:**
- Test **FAILS as expected** → confirms root cause, record as evidence
- Test **PASSES** (contradicts hypothesis) → re-examine root cause, loop back to 1.4
- Test **inconclusive** → note as `[Assumption]`, document what would make it conclusive

### Step 1.10: Generate Analysis Document

Read `references/analysis-template.md` for the template structure.

**Create the file:**
```bash
mkdir -p <output-dir>
```
Use the Write tool to create `<output-dir>/bug-<id>-analysis.md`.

**IMPORTANT:**
- Fill ALL sections with actual content (no placeholders)
- Verify with Read tool after creation
- Verify all links are revision-pinned (not trunk URLs)
- Ensure the Design Intention section is present and filled

### Step 1.11: Log to History

Append one line to `<output-dir>/history.log`:

**If Public:**
```bash
echo "$(date +%Y-%m-%d) | <bug_id> | PUBLIC | <component> | <root_cause_brief>" >> <output-dir>/history.log
```

**If Private:**
```bash
echo "$(date +%Y-%m-%d) | <bug_id> | PRIVATE" >> <output-dir>/history.log
```

Where `root_cause_brief` is 3-5 words (e.g., "missing promise rejection").
For private bugs: log ONLY `date | bug_id | PRIVATE`. No title, component, or details.

---

## Phase Gate: User Review

Present a summary of the Phase 1 findings to the user:
- Root cause (1-2 sentences)
- Key evidence (code path trace highlights)
- Test results
- Path to the analysis doc

Ask: **"Does this root cause analysis look correct? Say 'yes' to discuss solutions,
or tell me what needs more investigation."**

**This is a hard gate:**
- If user disagrees → loop back to the relevant Phase 1 step, update the analysis doc
- If user wants changes → make the changes, re-present
- Do NOT proceed to Phase 2 without explicit user agreement

---

## Phase 2: Solution Discussion

### Step 2.1: Read Analysis Doc

Re-read the analysis doc. Note the verified root cause, design intention, and
proof test results. These ground the solution discussion.

### Step 2.2: Propose Solutions

For each viable approach, present:
- **Description** of the approach
- **PROS** (list)
- **CONS** (list)
- **Effort**: Low / Medium / High
- **Risk**: Low / Medium / High

**Key principles:**
- Treat any suggested fixes from the bug report as **REFERENCES**, not solutions.
  Always analyze independently.
- Lean toward the best **long-term** solutions regardless of effort.
- Solutions should respect the **design intention** documented in Phase 1.
- For third-party library issues: present both upstream and Firefox-side fix strategies.

### Step 2.3: Discussion Loop

Interactive discussion with the user. They may:
- Ask for more detail on a solution
- Reject all solutions and ask for alternatives
- Request more Phase 1 research (loop back to relevant step)
- Share their own analysis or opinions
- Ask you to do further research

**Do NOT update the analysis doc during discussion.** It remains stable ground —
the last agreed-upon state. Only update when the user gives explicit approval.

### Step 2.4: Write Solutions to Analysis Doc

Only on explicit user signal ("write it down", "update the doc", "document this", etc.).

Append the **## Proposed Solutions** section to the analysis doc with:
- Each option described with pros/cons
- Comparison table (Pros, Cons, Effort, Risk columns)
- Agreed Approach section documenting the selected solution and reasoning

---

## Tips

- For security bugs, include a **## Security Rating** section in the analysis doc
- Private bugs: log ONLY `bug_id` to history — no titles, components, or details
- Suggested fixes in bug comments are **REFERENCES**, not solutions
- When creating commits, do NOT add "Co-Authored-By" lines
- If an existing investigation file exists for this bug, read it as input context
  (don't redo work that's already done)
- Compare multiple failure instances (at least 2 task IDs) before forming a root
  cause hypothesis for intermittent failures
- The test suite name in Treeherder is often the fastest clue to the root cause area
