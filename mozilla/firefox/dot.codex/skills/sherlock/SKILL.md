---
name: sherlock
description: >
  Firefox bug root-cause analysis for Codex. Use for Bugzilla bugs or Firefox failures where you need evidence-based diagnosis, revision-pinned source links, code-path tracing, proof tests, resumable run directories, and later solution discussion.
metadata:
  short-description: Root-cause Firefox bugs
---

# Sherlock: Root Cause Analysis

Follow the `source-permalinks` skill for ALL source and documentation references.
Follow `references/spec-check.md` when verifying web specification compliance.
Follow `references/gecko-architecture.md` for Gecko architecture lookups.
Follow `references/agent-teams.md` for the Codex subagent I/O contracts and prompts.

This skill has two phases:
1. **Root Cause Analysis** — evidence-based diagnosis with permanent source links,
   code path traces, and proof tests. Focus entirely on WHY the bug occurs.
2. **Solution Discussion** — propose and discuss solutions with the user. Only after
   the user agrees with the Phase 1 analysis.

Sherlock runs are **persistent and resumable**. Every run writes a `plan.md`
progress table to its run directory; each research team and each reviewer writes
its findings to a dedicated file. If a session halts (server unavailable, context
exhausted, power outage, kill), re-invoke with `--resume <run-dir>` (or just
`/sherlock <bug-id>` — the bug id locates the run dir) and the skill continues
from the first non-completed row. See **Phase 0** and `references/plan-template.md`.

**Arguments:** $0

Parse the arguments:
- `--resume <run-dir>` present → **resume mode** (skip fresh setup; see Phase 0).
- Otherwise:
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
2. **ALWAYS use revision-pinned links** — follow the `source-permalinks` skill.
   Never use trunk/tip URLs (`firefox-main/source/...`) in the analysis doc.
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
9. **Delegate research, not synthesis** — subagents do bounded fact-finding
   (bug fetch, code path tracing, git archaeology). The main agent decides
   what the facts mean. Never let a subagent declare the root cause.
10. **Three hypotheses minimum** — single-hypothesis RCAs anchor too early.
    Step 1.3b.5 is mandatory; do not skip it even when one cause feels obvious.
11. **The reviewer is independent** — when `red-pen` returns `revise`
    or `redesign`, do not argue with the verdict. Either fix the solution,
    escalate to the user (for `redesign`), or loop back to Phase 1 (for
    `reject` / `needs-more-info`). This applies to both the Phase-1 review
    team (root cause) and the Phase-2 red-pen (solutions).
12. **Persist every team output to disk** — each Phase-1 research team and each
    Phase-5 reviewer owns a named output file in the run dir (`teams/*.md`,
    `review/*.md`). Their findings live there, not just in the main-agent
    transcript. A halted session resumes by reading those files. Never rely on a
    subagent transcript to retain results.
13. **Update `plan.md` at every transition** — set a row to `in-progress`
    *before* starting the work and `completed` after the artifact is on disk.
    Never leave a row silently behind; the progress table is the hand-over
    document for `--resume`.

---

## Subagent delegation policy

The main agent's context is reserved for **synthesis** — connecting evidence,
forming and pruning hypotheses, deciding what is verified vs assumed,
articulating the root cause. Bounded research tasks are delegated to
subagents so the main context stays focused.

**Delegate** to a subagent when the task is:
- **Bounded**: clear input, clear output shape, no interactive judgment.
- **Voluminous**: produces a lot of intermediate text (raw bug comments,
  searchfox dumps, git log archaeology) that the main agent does not need
  in full.
- **Parallelizable**: e.g., trace Firefox + library simultaneously.

**Do NOT delegate**:
- Hypothesis selection or pruning (Team H is advisory; the tree is yours).
- "What does this evidence mean for the root cause?" — Synthesis (Step 1.7.5).
- The verdict, the root cause, and the design-relation sentence.
- Phase Gate / user-facing decisions.
- The structural self-check (Step 1.10.5).
- Any step that requires judging two competing claims.

Bounded research is delegated to **Codex subagent teams** using `spawn_agent`.
Use `worker` subagents for deterministic artifact production (bug digests,
code traces, test scouting) and `explorer` subagents for broad search or
hypothesis brainstorming. Sherlock's investigation is gated, so teams launch in
two waves (full contracts in `references/agent-teams.md`):

- **Stage 2a — intake teams** (run before any hypothesis exists, formalising the
  old Step 1.1): **Team B** (bug-context digest) and **Team H** (hypothesis
  brainstorm, advisory only).
- *(main-agent gate: failure-pattern classification, investigation plan,
  hypothesis tree, working branch — none delegated)*
- **Stage 2b — research teams** (run after the primary hypothesis is chosen,
  formalising the old Steps 1.5/1.6): **Team C** (Firefox code-trace), **Team L**
  (library code-trace, when third-party), **Team D** (design archaeology),
  **Team X** (cross-browser/spec), **Team T** (test-framework scout + draft).
- **Synthesis** (main agent reads all team files → verdict + root cause).

Each team **writes its full findings to a dedicated file** under `<run-dir>/teams/`
and returns only a ≤10-line summary. The main agent reads the files, never the
transcripts. Each invocation must:
- Pass inputs as **file paths and explicit values** — not as "the bug we're
  investigating".
- Specify the **output shape** and the target output file.
- Include the framing: *"return the requested artifact only; do not draw
  conclusions about the root cause."*

A team never declares the root cause, the verdict, or the hypothesis ranking.

---

## Phase 0 — Intake and resume

Every run lives in a **per-run subdirectory** `<output-dir>/bug-<id>/` (the
**run dir**). `plan.md` (the progress table, from `references/plan-template.md`)
and all artifacts live inside it. The bug id is the run identity — there is no
slug. Re-running the same bug resumes the existing run dir.

### Resume branch

Enter this branch if the invocation contains `--resume <run-dir>`, **or** if a
fresh invocation's `<output-dir>/bug-<id>/plan.md` already exists (in which case
ask the user directly: "Found an existing analysis for bug `<id>` at `<path>`.
Resume, or start fresh?" — "start fresh" archives or overwrites per the user).

1. `Read <run-dir>/plan.md`. Recover the bug id, the pinned **Searchfox
   revision**, and the progress table.
2. Restore session variables: set `$SHERLOCK_REV` from the plan.md revision line
   — **do NOT re-resolve it**; every link on disk depends on it. Re-resolve only
   `$SHERLOCK_AUTHOR` via `sherlock-config --get-patch-author` (deterministic).
3. Confirm the Firefox working branch still exists:
   `git rev-parse --verify sherlock/bug-<id>`. If missing, recreate it from the
   recorded revision and set row 8 back to `in-progress` in plan.md.
4. Announce in ≤2 lines: "Resuming sherlock bug `<id>` at `<run-dir>`; next task:
   `<first non-completed row>`."
5. Jump to the phase containing the first `pending`/`in-progress` row. Treat
   `in-progress` rows as un-finished — re-run them; their output file overwrites.
   Trust `completed` rows (read their artifacts, do not regenerate). Re-present
   `blocked-on-user` rows (e.g. the Phase Gate) to the user.
6. Skip the rest of Phase 0.

### Fresh-run branch

1. **Check setup:** `.codex/skills/sherlock/sherlock-config --check-setup`
   reports API key availability, `bmo-to-md`, `searchfox-cli`, and configured
   output dir. If any prerequisite is missing, present options to the user.
2. **Resolve output dir** (priority): CLI arg → `sherlock-config --get-output-dir`
   → ask the user directly, then persist with
   `sherlock-config --set-output-dir <path>`.
3. **Parse** bug id and optional report-path (see Arguments above).
4. **Create the run dir and subdirs:**
   ```bash
   mkdir -p <output-dir>/bug-<id>/teams
   mkdir -p <output-dir>/bug-<id>/review
   mkdir -p <output-dir>/bug-<id>/firefox/fix
   mkdir -p <output-dir>/bug-<id>/firefox/debug
   ```
   `<library>/` subdirs are created later, when Step 1.5b activates (T1).
   Hereafter `<run-dir>` = `<output-dir>/bug-<id>/`.
5. **Resolve `$SHERLOCK_REV`** (pin a searchfox revision for the whole run so all
   links are permanent):
   1. Get local HEAD: `git rev-parse HEAD`
   2. Validate on searchfox:
      fetch `https://searchfox.org/firefox-main/rev/<hash>/moz.configure`
      - 200 → use this hash as `$SHERLOCK_REV`
      - 404 (not yet indexed) → fetch
        `https://searchfox.org/firefox-main/source/moz.configure` and extract the
        latest indexed revision from the page
   3. For ESR/beta branches, repeat with the appropriate repo id
      (e.g. `firefox-esr128`).
6. **Resolve `$SHERLOCK_AUTHOR`:**
   `SHERLOCK_AUTHOR=$(.codex/skills/sherlock/sherlock-config --get-patch-author)`
   (reads `patch_author` from config, else `git config user.name`/`user.email`).
   All generated patches use this as the commit author.
7. **Write `plan.md`** from `references/plan-template.md` into `<run-dir>/`,
   substituting `{bug_id}`, `{start_timestamp}`, `{public_or_private}`,
   `{abs_run_dir}`, `{rev_short}`, `{rev_full}`. Row 1 `in-progress`, rest
   `pending`.
8. Mark row 1 `completed` and append a Notes line. Confirm to the user in ≤3
   lines: bug id, run-dir path, `$SHERLOCK_REV` short hash, "resume with
   `/sherlock --resume <run-dir>` if I stop".

> The bug report itself is fetched by **Team B** in Phase 1 (Step 1.1), not here
> — unless a `report-path` was provided, in which case read it directly and pass
> its path to Team B as a pointer instead of re-fetching.

### Output Directory Structure

The run dir uses a uniform layout. Firefox patches go in `firefox/`, third-party
patches go in `<library>/`. Both use identical `fix/` + `debug/` substructure.
Patches are numbered so they apply in order — test patches first, then fix
patches on top, so reviewers can verify tests go from FAIL to PASS.

```
<output-dir>/bug-<id>/                          # the run dir (resume key = bug-<id>)
  plan.md                                       # Progress table + resume doc
  bug-<id>-analysis.md                          # Primary analysis document
  bug-<id>-report/                              # Bug report from bmo-to-md (Team B)
  bug-<id>-attachments/                         # Attachments (Team B)
  bug-<id>-review.md                            # Phase-2 red-pen on solutions
  teams/                                        # Phase-1 team output files
    team-b-bug-context.md
    team-c-code-trace-firefox.md
    team-l-code-trace-library.md
    team-h-hypotheses.md
    team-d-design-archaeology.md
    team-x-cross-browser.md
    team-t-frameworks.md
    synthesis.md
  review/                                       # Phase-1 review-team files
    L.md   T.md   R.md
  firefox/
    fix/                                        # Clean patches for Firefox
      01-test-<desc>.patch                     #   Regression test
      02-fix-<desc>.patch                      #   Fix on top of test
    debug/                                      # Firefox debug artifacts
      01-test-<desc>.patch                     #   Same test patch(es)
      02-debug-firefox-instrumentation.patch   #   Instrumentation on top
      bug-<id>-test-run.log                    #   Test execution output
      bug-<id>-debug-<desc>.log                #   Captured debug output
  <library>/                                    # Only when third-party involved
    bug-<id>-upstream-<library>.md              # Upstream report (sanitized)
    fix/                                        # For upstream: clean, applicable
      01-test-<desc>.patch                     #   Standalone test (if no injection)
      02-fix-<desc>.patch                      #   Fix on top of test
    debug/                                      # For upstream: reproduction aid
      01-test-<desc>.patch                     #   Test (may include injection)
      02-debug-lib-instrumentation.patch       #   Logging on top of test
      bug-<id>-debug-lib-<desc>.log            #   Library debug output
```

The `<library>/` folder is created only when Step 1.5b is active (Branch A, B, or C).
For Branch B (Firefox integration bug), `<library>/` may contain only the T3
diagnostic logs — no `fix/` patches since the library has no bug.

The `<library>/` output structure mirrors three git branches in the local library
repo (see T3 for details):
- `sherlock/bug-<id>/test` — test commits (base for debug and fix)
- `sherlock/bug-<id>/debug` — instrumentation on top of test
- `sherlock/bug-<id>/fix` — fix on top of test (created in A4/C4)

The `firefox/` output structure mirrors the Firefox working branch (see Step 1.3c):
- `sherlock/bug-<id>` — test commits, then fix commits on top (Phase 2)
- `sherlock/bug-<id>/debug` — instrumentation on top of tests (temporary)

The Firefox fix may differ from the upstream fix (e.g., upstream takes a wider-scope
fix touching many files, while Firefox takes a less-aggressive local patch touching
one or two files).

**Patch ordering rules:**

Within each `fix/` folder:
- If the regression test can be created **without code injection** (reproducible with
  certain inputs in the built-in test framework), then test patches come first, fix
  patches on top.
- If the test requires **code injection** (e.g., custom malloc returning OOM, mocked
  syscalls), then only fix patches go in `fix/` — the injection-based tests go in
  `debug/` instead.

Within each `debug/` folder:
- Always contains test patches (including injection-based ones), with debug
  instrumentation patches on top.
- Goal: developers can apply these patches and immediately reproduce + confirm
  the issue.

**Numbering**: Use two-digit prefixes (`01-`, `02-`, ...) for apply order. Use
descriptive names after the prefix (e.g., `01-test-ogg-truncated-stream.patch`,
`02-fix-bounds-check-vorbis-window.patch`).

**Patch format**: Always use `git format-patch` so patches can be applied via
`git am -3` (with three-way merge) or `git apply`. This requires committing
changes before generating the patch.

Patch generation pattern (commits stay on the branch; `$SHERLOCK_AUTHOR` resolved
in Phase 0):
```bash
git add <files>
git commit --author="$SHERLOCK_AUTHOR" -m "<descriptive message>"
git format-patch -1 --stdout > <run-dir>/<path>/<NN>-<desc>.patch
```
The commit message should describe what the patch does (e.g.,
"Add gtest for OOB read in vorbis window function" or "Add debug
instrumentation for decode path tracing"). Commits are kept on the working
branch — do NOT reset. The branch history IS the ordered patch series:
`test-1 → test-2 → ... → fix-1 → fix-2 → ...`

`<library>/` subdirectories are created when Step 1.5b activates and the library
is identified (T1): `mkdir -p <run-dir>/<library>/fix <run-dir>/<library>/debug`.

---

## Phase 1: Root Cause Analysis

### Step 1.1: Understand the Bug — Stage 2a teams (Team B + Team H)

Launch the **Stage 2a intake teams** with `spawn_agent` subagents, in parallel
when the runtime supports it. Full I/O contracts and prompt templates are in
`references/agent-teams.md`:

- **Team B — bug-context digest.** Fetches the main bug + each duplicate +
  attachments + Treeherder failure-distribution, and writes the digest to
  `<run-dir>/teams/team-b-bug-context.md` (sections: Identity, STR, Attachments,
  Duplicates, Treeherder, Pointers). This single fetch serves Steps 1.2
  (duplicates), 1.3 (failure pattern), and 1.8a (attachments) — read the file,
  do not re-fetch. If a `report-path` was provided in Phase 0, pass it as a
  pointer so Team B skips the main fetch.
- **Team H — hypothesis brainstorm (advisory).** Brainstorms ≥3 candidate
  hypotheses (mechanism / confirming / refuting / probe cost) to *feed* the
  main agent's hypothesis tree (Step 1.3b.5). It writes
  `<run-dir>/teams/team-h-hypotheses.md`. **It does not rank or pick a primary
  hypothesis** — that is main-agent work (anti-anchoring, Gotcha #10). Seed it
  with the bug identity/STR/stack you already have (pass inline).

Set plan.md rows 2 (Team B) and 3 (Team H) `in-progress` before launching. As
each returns, verify its output file is non-empty and mark its row `completed`;
if a team aborts, leave its row `in-progress` so `--resume` re-runs it.

Then `Read <run-dir>/teams/team-b-bug-context.md` and extract for the analysis
doc:
- Bug title and description (condensed)
- Component
- Steps to reproduce (STR)
- Expected vs actual behavior
- Attached testcases or reproduction scripts
- Keywords (check for `sec-*` keywords: sec-high, sec-moderate, sec-low, sec-critical)
- Related bugs, duplicates, depends/blocks

If the bug has any `sec-*` keyword or is in a security group, the analysis doc
MUST include a **Security Rating** section.

### Step 1.2: Check Duplicates and Related Bugs

Mark plan.md row 4 `in-progress`. Team B's digest already includes duplicate
fetches and a "Duplicates" section. Read that section.

Duplicates are valuable when they contain:
- Additional STR or reproduction scripts
- Independent stack traces that confirm or refine the root cause
- Attached testcases (`testcase` keyword)
- Commenter analysis that narrows the failure condition
- Different affected versions or platforms

If the digest's duplicate summary is thin and a duplicate seems important,
read the raw report from `<run-dir>/bug-<duplicate_id>-report/` directly
— targeted Read, not full re-ingestion. If a duplicate adds a meaningfully
different perspective, note it under **Related Context** in the analysis doc.
Mark row 4 `completed`.

### Step 1.3: Failure Pattern Analysis

Mark plan.md row 5 `in-progress`. Team B's digest has the Treeherder block. From
it, extract:
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
If it passes 95% of the time, something rare causes the failure. Write the
Failure Pattern section into the analysis doc and mark row 5 `completed`.

### Step 1.3b: Plan the Investigation

Mark plan.md row 6 `in-progress`. **Enter plan mode** before starting the deep
investigation. Use `update_plan` to draft an investigation plan based on what
Steps 1.1-1.3 (and Team H's candidate hypotheses) revealed.

The plan should cover:
- **Hypothesis**: Initial theory about the root cause (to be confirmed or refuted)
- **Code areas to investigate**: Which files/subsystems to trace (from bug report,
  stack traces, component, test suite names)
- **Third-party involvement**: Whether vendored library code is likely involved
  (if yes, which library and why)
- **Build requirements**: Whether a special build (debug/ASan/TSan) is likely needed
- **Test strategy**: What kind of proof test is likely appropriate
- **Open questions**: What information is still missing

Present the plan to the user for review. The user may refine the hypothesis,
suggest additional code areas, or redirect the investigation. Use `update_plan`
after the user approves or provides feedback. Record plan decisions in plan.md
Notes and mark row 6 `completed`.

### Step 1.3b.5: Build the Hypothesis Tree

Mark plan.md row 7 `in-progress`. Read `<run-dir>/teams/team-h-hypotheses.md` for
Team H's candidates, then **build the tree yourself** — Team H is advisory; you
own selection, ranking, and pruning. **Enumerate at least three** candidate
root-cause hypotheses — even when one already feels obvious. Single-hypothesis
RCAs anchor too early; the cost of generating two extra candidates is minutes,
the cost of anchoring on the wrong one is hours.

For each hypothesis, fill in:

| Hypothesis | Failure mechanism | Confirming evidence | Refuting evidence | Probe cost |
|------------|-------------------|---------------------|-------------------|------------|
| H1 ({short name}) | {how the bug would manifest if this were the cause} | {what we'd see in code/logs/test if true} | {what we'd see if false} | {minutes / hours / build required} |
| H2 ({short name}) | ... | ... | ... | ... |
| H3 ({short name}) | ... | ... | ... | ... |

Pick the hypothesis with the highest **confirm/refute ratio per unit of
probe cost** as the **primary**; keep the others alive in reserve. Save
this table to the analysis doc under a `## Hypothesis Tree` section so
reviewers can see what was considered and pruned.

When investigation surfaces evidence that revives a pruned hypothesis, do
not silently re-anchor — re-rank the table and update the analysis doc. Mark
row 7 `completed`.

### Step 1.3c: Create Firefox Working Branch

Mark plan.md row 8 `in-progress`. Create a working branch in the Firefox tree for
all sherlock test and fix commits:
```bash
git checkout -b sherlock/bug-<id> HEAD
```

All test commits go on this branch first, then fix commits on top (Phase 2):
```
HEAD
  └── sherlock/bug-<id>               ← test-1 → test-2 → ... → fix-1 → fix-2 → ...
        └── sherlock/bug-<id>/debug   ← instrumentation on top of tests (temporary)
```

The `sherlock/bug-<id>/debug` branch is created later (Step 1.8e or B1.4) when
instrumentation is needed. It forks from the last test commit and is used only for
debug capture — it is not part of the final patch series. Mark row 8 `completed`.

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

### Step 1.5: Stage 2b research teams (C, L, D, X, T)

Once the primary hypothesis and entry symbols are chosen (Steps 1.3b.5/1.4),
launch the **Stage 2b research teams** with `spawn_agent` subagents, in parallel
when the runtime supports it. Full I/O contracts and prompt templates are in
`references/agent-teams.md`. All Stage 2b teams are **read-only** — none of them
build. Set each applicable team's plan.md row `in-progress` before launching:

- **Team C — Firefox code-trace** (row 9). Numbered, revision-pinned trace of the
  call path for the primary hypothesis → `teams/team-c-code-trace-firefox.md`.
- **Team L — library code-trace** (row 10). Only when Step 1.5b applies; same
  contract with upstream permalinks → `teams/team-l-code-trace-library.md`.
  Vendored revision: `git show HEAD:media/<lib>/moz.yaml | grep revision`.
- **Team D — design archaeology** (row 11). Git-history archaeology of the suspect
  code → `teams/team-d-design-archaeology.md`. **Skip (row `skipped`) when Step
  1.5b is active** — design intention is covered in the branch workflow
  (A1/B1/C1).
- **Team X — cross-browser / spec** (row 12). Spec citation + cross-engine
  behaviour table → `teams/team-x-cross-browser.md`. Skip (row `skipped`) for
  internal-only bugs with no web surface.
- **Team T — test-framework scout + draft** (row 13). Per live hypothesis: pick a
  framework, find a neighbour test, and draft the proof-test source →
  `teams/team-t-frameworks.md`. Team T does NOT build (builds serialize — see
  Step 1.8/1.9).

As each team returns, verify its output file is non-empty and mark its row
`completed`; if a team aborts, leave its row `in-progress` for `--resume`. The
main agent **reads the files** (not transcripts) during Synthesis and reasons
about which trace steps correspond to the primary hypothesis. Read
the `source-permalinks` skill for URL patterns; every code reference is
revision-pinned with `$SHERLOCK_REV`.

### Step 1.5b: Third-Party Library Sub-Workflow (Conditional)

If the root cause does **not** involve vendored third-party code, mark plan.md
rows 14 and 10 (Team L) `skipped` and continue at Step 1.6/1.7.5.

If the root cause involves vendored third-party code (file paths matching
`references/upstream-libs.md`), activate this sub-workflow. It is **plan.md row
14 — a gate**. T1/T2/T3 are sequential and main-agent-driven (NOT teams): T1 needs
user input; T3 is a serialized diagnostic build whose result chooses the branch.

Ordering with the Stage 2b teams: the read-only traces (Team C + Team L) launched
in Step 1.5 run **before** T3's build, so the trace informs which path to test.
After T3 resolves scope, **write the scope verdict (Branch A / B / C) into plan.md
Notes** and **append the branch sub-rows** under row 14 (see
`references/plan-template.md` "Dynamic rows"). Recording the verdict in Notes lets
a resume that halts after T3 but before the rows are written reconstruct them.
Mark row 14 `in-progress` now; mark it `completed` once the scope is recorded and
the branch rows are appended. Branch downstream work then runs against those
appended rows.

#### T1: Check for Local Upstream Repo

Ask the user directly:
- "The issue involves {library} ({upstream_url}). Do you have a local clone?"
- If yes: "Where is it?"
- If no: "Should I clone it? Where?" (suggest `~/Work/{lib-name}`)

#### T2: Initial Scope Hypothesis

Form an initial hypothesis about where the bug lives:
- **(a) In the library itself** — would reproduce with standalone upstream tests
- **(b) In Firefox's integration** — library works correctly but Firefox's wrapper
  code, IPC, threading, or lifecycle management causes the issue
- **(c) In Firefox's local patches** — Firefox applies patches on top of the vendored
  library that introduce or expose the problem. Check `media/{lib}/` for `.patch`
  files or diffs from the upstream revision.

This is a hypothesis — T3 will confirm or refute it.

#### T3: Diagnostic — Reproduce in Upstream Library

**This step is mandatory regardless of the T2 hypothesis.** Even if you suspect a
Firefox integration issue, always attempt to reproduce in the upstream library
first. This eliminates false assumptions about where the bug lives.

**Branch structure in the local library repo:**

Work in the library repo uses three branches forked from the upstream revision.
This keeps test, debug, and fix work cleanly separated with proper git history:

```
upstream HEAD (vendored revision)
  └── sherlock/bug-<id>/test     ← test commits
        ├── sherlock/bug-<id>/debug  ← debug instrumentation on top of test
        └── sherlock/bug-<id>/fix    ← fix commits on top of test (created in A4/C4)
```

**1. Create the test branch and write the standalone test:**

```bash
# In the local library repo
git checkout -b sherlock/bug-<id>/test <vendored-revision>
```

Create a minimal test case in the library's native test framework (see the
Library Test Frameworks table in `references/upstream-libs.md`). The test should
exercise the suspected failure condition.

```bash
git add <test files>
git commit --author="$SHERLOCK_AUTHOR" -m "Add standalone test for <desc>"
```

Generate the test patch:
```bash
git format-patch -1 --stdout > <run-dir>/<library>/debug/01-test-<desc>.patch
```

**2. Create the debug branch and add instrumentation:**

```bash
git checkout -b sherlock/bug-<id>/debug
```

Add targeted logging to confirm the traced code path is hit during test execution.

Common instrumentation patterns for C/C++ libraries:
- `fprintf(stderr, "SHERLOCK: %s:%d reached\\n", __FILE__, __LINE__);`
- `fprintf(stderr, "SHERLOCK: value=%d\\n", variable);`
- Library-specific debug macros if available (e.g., `aom_internal_error`, `dav1d_log`)

```bash
git add <instrumented files>
git commit --author="$SHERLOCK_AUTHOR" -m "Add debug instrumentation for <desc>"
git format-patch -1 --stdout > <run-dir>/<library>/debug/02-debug-lib-instrumentation.patch
```

**3. Code path trace**: Read and trace the suspected code path in the library's own
source files. Produce a numbered trace using permanent upstream links (e.g.,
`https://gitlab.xiph.org/xiph/vorbis/-/blob/{hash}/lib/sharedbook.c#L355`).

**4. Build and run** (on the debug branch — has both test + instrumentation):
```bash
<build-command> 2>&1 | tee <run-dir>/<library>/debug/bug-<id>-debug-lib-build.log
<test-command> 2>&1 | tee <run-dir>/<library>/debug/bug-<id>-debug-lib-<desc>.log
```

**5. Switch back to the test branch** for clean state:
```bash
git checkout sherlock/bug-<id>/test
```
The debug and test branches are preserved for later use. The fix branch (A4/C4)
will be created on top of the test branch.

**The T3 result determines the scope and which branch to follow:**

| T3 Result | Scope | Next Step |
|-----------|-------|-----------|
| Bug **reproduces** in upstream library | **(a) Library bug** | → Branch A |
| Bug **does NOT reproduce** upstream | **(b) Firefox integration** | → Branch B |
| Bug reproduces **differently** (e.g., different behavior, partial failure, or only under specific threading/config that Firefox uses) | **(a+b) Split scope** | → Branch C |

Document the T3 result and confirmed scope in the analysis doc. **Write the scope
verdict into plan.md Notes and append the branch sub-rows** under row 14 (Branch A
→ A1/A2/A3/A4; Branch B → B1/B2; Branch C → the two-layer rows), per
`references/plan-template.md` "Dynamic rows". Then mark row 14 `completed`.

---

#### Branch A: Library Bug (scope a)

The bug exists in the upstream library. Investigation and fix happen primarily in
the library repo. Use upstream permanent links for all code references.

**A1. Complete library investigation:**
- **Design intention**: Study git history in the library repo (`git log`, `git blame`,
  commit messages). Understand why the code was written this way, what constraints
  the authors faced. This replaces Step 1.6 for third-party code.
- **Verify claims**: Apply the two-tier rule (Verified vs `[Assumption]`) to all
  claims about the library code.

**A2. Create Firefox-side regression test:**

Create a test in the Firefox tree that reproduces the issue through Firefox's
integration layer. This proves Firefox is affected AND will verify that vendoring
the upstream fix resolves the problem in Firefox.

1. Use the PoC from the bug report (test.html, attached testcases) as the basis
2. Choose the appropriate Firefox test framework:
   - **gtest** — C/C++ internal paths that call library APIs directly
   - **crashtest** — crash-only via web-facing paths (`<audio>`, `<video>`, etc.)
   - **WPT** — web-exposed, spec-defined behavior
   - **mochitest** — web-exposed, Firefox-specific behavior
3. The test MUST fail without the fix and pass with it
4. Register the test in the appropriate manifest
5. Commit the test on the Firefox working branch and generate the patch:
   ```bash
   git checkout sherlock/bug-<id>
   git add <test files>
   git commit --author="$SHERLOCK_AUTHOR" -m "Add regression test for <desc>"
   git format-patch -1 --stdout > <run-dir>/firefox/fix/01-test-<desc>.patch
   cp <run-dir>/firefox/fix/01-test-<desc>.patch <run-dir>/firefox/debug/01-test-<desc>.patch
   ```
   The commit stays on the branch — do NOT reset.
6. Build and run against the unfixed tree:
   ```bash
   ./mach build
   ./mach test <path> --headless 2>&1 | tee <run-dir>/firefox/debug/bug-<id>-test-run.log
   ```

**A3. Generate upstream report:**

Generate a second, concise analysis document for reporting to the upstream library
maintainers. Read `references/upstream-report-template.md` for the template.

Write to `<run-dir>/<library>/bug-<id>-upstream-<library>.md`.

**Critical rules for the upstream report:**
- Use ONLY upstream permanent links — no searchfox, no Firefox paths
- Do NOT mention Firefox, Gecko, or any browser-specific context
- Do NOT include security exploitation details, sec-* ratings, or how the bug
  can be triggered via web content
- Do NOT include Bugzilla links or Firefox bug numbers
- Describe the issue purely in terms of the library's API and internal behavior
- Include the T3 standalone test case (or reference it)
- Include the library-side code path trace from A1
- If a fix is verified (A4), include it as a suggested fix

This report should be suitable for filing as an upstream bug report or attaching
to a pull request / issue tracker entry.

**A4. Fix strategy:**

First, copy the test patch to `fix/` (now that scope (a) is confirmed and the test
FAILS). Only copy if the test requires no code injection:
```bash
cp <run-dir>/<library>/debug/01-test-<desc>.patch <run-dir>/<library>/fix/01-test-<desc>.patch
```

Create the fix branch on top of the test branch in the library repo:
```bash
git checkout sherlock/bug-<id>/test
git checkout -b sherlock/bug-<id>/fix
# ... implement the fix ...
git add <fix files>
git commit --author="$SHERLOCK_AUTHOR" -m "Fix <desc>"
git format-patch -1 --stdout > <run-dir>/<library>/fix/02-fix-<desc>.patch
```

Verify:
1. Build and run the T3 test on the fix branch — confirm it now passes
2. Apply the fix to the vendored copy in Firefox (`media/{lib}/` or `third_party/{lib}/`)
3. `./mach build` and verify the A2 Firefox test now passes
4. Update the upstream report with the suggested fix if verified

Phase 2 solutions should include:
- **Upstream fix**: submit to upstream, then update vendored copy via `./mach vendor`
  or manual update. Preferred for long-term health. Larger scope acceptable.
- **Local Firefox patch** (if urgent): apply as a patch on top of the vendored
  library pending upstream acceptance. Smaller scope, faster to land.

Both appear in the Proposed Solutions with Pros/Cons/Effort/Risk.

---

#### Branch B: Firefox Integration Bug (scope b)

The library works correctly — the bug is in how Firefox uses it (wrapper code, IPC
actors, threading model, lifecycle management, error handling around library calls).

**B1. Pivot investigation to Firefox code:**

Resume the standard investigation steps, focused on the integration layer:

1. **Code path trace** (Step 1.5): Trace the Firefox integration code using searchfox
   revision-pinned links. Include the boundary where Firefox calls into the library
   and how results/errors propagate back.

2. **Design intention** (Step 1.6): Study the Firefox integration code's git history.
   Why was the wrapper written this way? What assumptions does it make about the
   library's behavior?

3. **Proof test** (Step 1.8): Create a Firefox test that reproduces the integration
   bug. Follow A2 steps 1-6: choose framework, register in manifest, commit on
   `sherlock/bug-<id>`, generate patch to `firefox/fix/` and `firefox/debug/`,
   build and run. No separate library test needed — the library is correct.

4. **Debug instrumentation** (Step 1.8e): Create `sherlock/bug-<id>/debug` branch
   from the test commit. Add instrumentation, commit, generate
   `firefox/debug/02-debug-firefox-instrumentation.patch`.

5. **Run with instrumentation** (Step 1.9): Build on the debug branch (`./mach build`),
   run tests, capture debug logs to `firefox/debug/`. Switch back to
   `sherlock/bug-<id>` (working branch with test commits only).

**B2. Fix strategy (Phase 2):**

The fix is entirely in Firefox's integration layer. Typical fixes:
- Correct threading assumptions (e.g., library is not thread-safe but Firefox calls
  it from multiple threads)
- Fix lifecycle management (e.g., using library object after shutdown)
- Add missing error handling around library calls
- Correct IPC serialization of library types

No upstream submission needed. The T3 result ("library works correctly") should be
documented to prevent future misattribution.

---

#### Branch C: Split Scope (scope a+b, or scope c)

The root cause spans both the library and Firefox's integration. Common patterns:
- Library has an undocumented API contract; Firefox violates it
- Library has a threading assumption; Firefox's threading model breaks it
- Firefox's local patches (`media/{lib}/*.patch`) introduce a bug not in upstream
- Library returns an error that upstream callers handle but Firefox's wrapper doesn't

**C1. Investigate both layers:**

You need TWO code path traces, TWO design intention studies, and TWO sets of
permanent links:

- **Library side**: Code path trace with upstream permanent links. Design intention
  from library git history. Document what the library expects (API contracts,
  threading model, preconditions).
- **Firefox side**: Code path trace with searchfox links. Design intention from
  Firefox git history. Document where Firefox violates the library's expectations
  or fails to handle a library-side edge case.

For **scope (c)** (Firefox local patches): compare the vendored code against the
upstream revision to identify what the patches changed and whether the patch
introduced the bug:
```bash
# Diff vendored copy against upstream
git diff HEAD:media/<lib>/src/file.c <local-lib-repo>/src/file.c
# Or check for explicit patch files
ls media/<lib>/*.patch
```

**C2. Create and run tests for BOTH layers:**

- **Library test** (from T3): Already created and run in T3. The result (PASS or
  FAIL) indicates whether the library itself has a bug or just an undocumented
  limitation.
- **Firefox test** (A2 pattern): Create a Firefox-side test that demonstrates the
  integration aspect (e.g., the contract violation, the missing error handling).
  Follow A2 steps 1-6: choose framework, register in manifest, generate patch to
  `firefox/fix/` and `firefox/debug/`, run against the unfixed tree and capture
  output to `firefox/debug/`. This test MUST fail without fix.

**C3. Generate upstream report (if library-side fix needed):**

If the library has a bug, undocumented limitation, or missing hardening that
contributes to the issue, generate an upstream report following the same rules
as Branch A step A3. Read `references/upstream-report-template.md`.

Write to `<run-dir>/<library>/bug-<id>-upstream-<library>.md`.

**For split-scope reports, frame the issue from the library's perspective:**
- If the library has a bug: report it as a bug
- If the library has an undocumented API contract: frame as a documentation or
  hardening request ("library should validate X" or "document that callers must Y")
- Do NOT reveal the Firefox-side contract violation or exploitation path
- Do NOT include Firefox security ratings or Bugzilla links

**C4. Fix strategy (Phase 2):**

If the T3 library test FAILS and requires no code injection, copy it to `fix/`:
```bash
cp <run-dir>/<library>/debug/01-test-<desc>.patch <run-dir>/<library>/fix/01-test-<desc>.patch
```
If the test PASSES (undocumented limitation), only the hardening fix goes in `fix/`
— no test patch, since there's no FAIL→PASS transition to demonstrate.

Create the library fix branch (same as A4):
```bash
git checkout sherlock/bug-<id>/test
git checkout -b sherlock/bug-<id>/fix
# ... implement the fix ...
git add <fix files>
git commit --author="$SHERLOCK_AUTHOR" -m "Fix <desc>"
git format-patch -1 --stdout > <run-dir>/<library>/fix/02-fix-<desc>.patch
```

Present separate strategies for each layer:

| Layer | Fix Type | Scope |
|-------|----------|-------|
| Library | Harden API, add validation, document contract | Long-term, submit upstream |
| Firefox | Respect API contract, add error handling, fix threading | Smaller scope, land in Firefox |

Both fixes may be needed. The analysis doc should clarify:
- Which fix is **necessary** (without it the bug persists)
- Which fix is **defensive** (hardens against the class of bug)
- Landing order: Firefox fix can land immediately; library fix goes upstream then
  gets vendored later

For **scope (c)**: evaluate whether to fix the local patch, replace it with
a better patch, or remove it entirely (if upstream now handles the case).

---

#### Summary: Required Tests by Scope

| Scope | Library Test (T3) | Firefox Test | Notes |
|-------|-------------------|--------------|-------|
| **(a) Library bug** | Yes — must FAIL | Yes (A2) — must FAIL | Both required |
| **(b) Firefox integration** | Diagnostic only (PASSES) | Yes (B1) — must FAIL | Only Firefox test is proof |
| **(a+b/c) Split** | Yes — may PASS or FAIL | Yes (C2) — must FAIL | Both required, separate evidence |

### Step 1.6: Study Design Intention (Team D)

Design archaeology is **Team D**, launched in the Stage 2b wave (Step 1.5). Its
full contract and prompt are in `references/agent-teams.md`; it writes
`teams/team-d-design-archaeology.md` (introducing commit, original purpose, design
rationale, constraints, function contract, related code, drift signals) and does
NOT claim how the root cause relates to the design.

**Skip Team D when Step 1.5b is active** (set row 11 `skipped`) — design intention
is covered within the branch workflow: Branch A in A1, Branch B in B1, Branch C in
C1.

During Synthesis (Step 1.10 area) the main agent reads the Team D file and writes
the Design Intention section in the analysis doc, **adding the sentence the team
declined to write: how the current root cause relates to (violates / reveals a gap
in / drifts from) the original design intention.** That synthesis is reserved for
the main agent and is critical for Phase 2 — solutions that respect the original
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

### Step 1.7.5: Synthesis (main agent, not delegated)

Mark plan.md row 15 `in-progress`. Read **all** Stage 2b team files (C, L, D, X,
T) and the Stage 2a files (B, H) — the files, not the subagent transcripts — and
write `<run-dir>/teams/synthesis.md`:

1. Merged code-trace + design-intention narrative; note any drift.
2. Re-rank the hypothesis tree against the gathered evidence. Revive any pruned
   hypothesis the evidence warrants — do not silently re-anchor.
3. Classify each hypothesis as `to-test` / `refuted` / `assumption-only`, citing
   the Team C/L/D/X evidence that drove the classification.
4. State the **verified root cause** with two-tier labels (Step 1.7), plus the
   sentence on how it relates to the design intention (Step 1.6).
5. **Append one row 16.x to plan.md per `to-test` hypothesis**, naming the target
   proof-test patch and log paths (see `references/plan-template.md`). **If Step
   1.5b is active**, the proof tests are tracked by the Branch rows under row 14
   (A2/T3/C2) instead — append no 16.x rows and mark row 16 `skipped`.

A team never declares the root cause — this synthesis is the main agent's. Mark
row 15 `completed`.

### Step 1.8: Evaluate and Create Proof Tests

This step processes the **row 16.x** entries Synthesis appended — one per
`to-test` hypothesis. **Builds serialize**: Team T already scouted the framework
and drafted the test source in parallel (`teams/team-t-frameworks.md`); the main
agent now writes, builds, and runs each test **one at a time**. Mark each row 16.x
`in-progress` before its build and `completed` after the result is captured.

**Note:** If Step 1.5b is active, skip this step — proof tests are already created
within the branch workflow:
- **Branch A**: T3 (library test) + A2 (Firefox test)
- **Branch B**: B1 (Firefox proof test)
- **Branch C**: C2 (both library and Firefox tests)

Read `references/test-frameworks.md` for framework selection and FuzzingFunctions mapping.

#### 1.8a: Check Bug Attachments for Existing Testcases

Team B already fetched attachments to `<run-dir>/bug-<id>-attachments` — read from
there (do not re-fetch). If a testcase exists and uses `FuzzingFunctions`, apply
the mapping table from `references/test-frameworks.md`. Auto-convert to the
appropriate framework.

#### 1.8b: Determine Test Framework

Team T already chose a framework and found a neighbour test per hypothesis
(`teams/team-t-frameworks.md`). Confirm its choice against the decision tree in
`references/test-frameworks.md`:
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
- Auto-generate a mozconfig file: `<run-dir>/firefox/debug/bug-<id>-mozconfig`
- Present to the user for review before building
- The user can invoke `/mozconfig` for full interactive configuration if preferred

#### 1.8d: Write Proof Test

Start from Team T's drafted test in `teams/team-t-frameworks.md` (adapt it; do not
build inside Team T). Write the test into the tree, commit it on
`sherlock/bug-<id>`, then **build it serialized** (one `./mach build` at a time; FE-only
tests use `./mach build faster`). The test must:
- **FAIL without fix** — proving the bug exists (the root cause claim is correct)
- Be designed to **PASS after fix** — making it reusable for TDD development later
- Serve as **EVIDENCE** for the root cause claim

#### 1.8e: Add Debugging Instrumentation

Create a debug branch from the current test commit for instrumentation:

```bash
git checkout -b sherlock/bug-<id>/debug
```

Add targeted logging to confirm the traced code path is actually hit during test
execution. Commit and generate the patch:

```bash
git add <instrumented files>
git commit --author="$SHERLOCK_AUTHOR" -m "Add debug instrumentation for <desc>"
git format-patch -1 --stdout > <run-dir>/firefox/debug/02-debug-firefox-instrumentation.patch
```

Common instrumentation patterns for Firefox C++/JS:
- **MOZ_LOG**: `MOZ_LOG(gMediaDecoderLog, LogLevel::Debug, ("SHERLOCK: %s:%d", __FILE__, __LINE__));`
- **printf** (quick and dirty): `printf("SHERLOCK: reached %s:%d\n", __FILE__, __LINE__);`
- **Mochitest JS**: `info("SHERLOCK: state=" + variable);`
- **GTest**: `GTEST_LOG_(INFO) << "SHERLOCK: value=" << variable;`

The debug branch is temporary — it's used for the build+run+capture cycle in
Step 1.9, then you switch back to the main working branch.

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

**Note:** If Step 1.5b is active, skip this step — tests are already run and debug
logs captured within the branch workflow:
- **Branch A**: T3 ran the library test; A2 ran the Firefox test
- **Branch B**: B1 ran the Firefox test with debug instrumentation
- **Branch C**: T3 ran the library test; C2 ran the Firefox test

**1. Build and run on the debug branch** (has test commits + instrumentation).
Builds serialize — one at a time:
```bash
# Should already be on sherlock/bug-<id>/debug from Step 1.8e
./mach build   # or: ./mach build faster   (FE-only proof tests)
./mach test <path> --headless 2>&1 | tee <run-dir>/firefox/debug/bug-<id>-test-run.log
```

Additional debug logs go in the `firefox/debug/` directory:
```
<run-dir>/firefox/debug/bug-<id>-debug-<description>.log
```

**2. Switch back to the working branch:**
```bash
git checkout sherlock/bug-<id>
```
The debug branch is preserved. The working branch has only test commits (clean,
ready for fix commits in Phase 2).

**3. Generate test patches** from the branch history:
```bash
# Export all test commits as numbered patches
git format-patch HEAD~N --stdout   # where N = number of test commits
# Or export individually and copy to debug/:
git format-patch -1 <commit> --stdout > <run-dir>/firefox/fix/01-test-<desc>.patch
cp <run-dir>/firefox/fix/01-test-<desc>.patch <run-dir>/firefox/debug/01-test-<desc>.patch
```

**4. Evaluate results** (mark each row 16.x `completed` with its result in Notes):
- Test **FAILS as expected** → confirms root cause, record as evidence
- Test **PASSES** (contradicts hypothesis) → re-examine root cause, loop back to 1.4
- Test **inconclusive** → note as `[Assumption]`, document what would make it conclusive

### Step 1.10: Generate Analysis Documents

Mark plan.md row 17 `in-progress`.

**Primary analysis document** (always required):

Read `references/analysis-template.md` for the template structure. Source content
from `synthesis.md` and the team files. Use the Write tool to create
`<run-dir>/bug-<id>-analysis.md`.

Requirements:
- Fill ALL sections with actual content (no placeholders)
- Verify with Read tool after creation
- Verify all links are revision-pinned (not trunk URLs)
- Ensure the Design Intention section is present and filled (including the
  main-agent sentence on how the root cause relates to the design)

Mark row 17 `completed`.

**Upstream report** (required for Branch A and Branch C with library-side fix):

If Step 1.5b produced a Branch A (library bug) or Branch C (split scope with
library-side component), the upstream report should already have been generated
in step A3 or C3. Verify it exists at `<run-dir>/<library>/bug-<id>-upstream-<library>.md`.

If not yet created, generate it now using `references/upstream-report-template.md`.
The upstream report must:
- Contain NO Firefox/browser/Bugzilla references
- Contain NO security exploitation details or sec-* ratings
- Use ONLY upstream permanent links
- Be self-contained and suitable for filing with the library's issue tracker

### Step 1.10.5: Structural self-check

Before launching the review team, the main agent does a quick **structural**
self-check (not the full audit — that is now the review team's job):

- [ ] Every analysis-doc section is filled with real content (no placeholders).
- [ ] The Design Intention section ends with the sentence stating how the root
  cause relates to the original design (violation / gap / drift). Without it,
  Phase 2 has nothing to design against.
- [ ] The Hypothesis Tree reflects the final ranking from Synthesis.

If a check fails, fix it before launching the review team.

## Phase 5: Review team (L / T / R)

The deep audit is done by an **independent review team**, not by the main agent
grading its own work. Set plan.md rows 18/19/20 `in-progress` and launch the three
reviewers with independent `worker` subagents (full contracts in
`references/agent-teams.md`). Each
writes a dedicated file under `<run-dir>/review/`:

- **Reviewer L (links / citations)** → `review/L.md`. Opens every code link in the
  analysis doc via `Read`; confirms the cited file:line still says what the doc
  claims; replaces any trunk URL with a `$SHERLOCK_REV` link.
- **Reviewer T (test re-runner)** → `review/T.md`. Re-reads
  `firefox/debug/bug-<id>-test-run.log` (and, if cheap, re-applies each
  `firefox/fix/*.patch` and rebuilds); confirms the proof test FAILs on the bug,
  not on a test-setup error.
- **Reviewer R (red-pen on root cause)** → `review/R.md`. Spawn an independent
  `worker` reviewer with `<abs path to bug-<id>-analysis.md>`; it challenges
  the root cause, the hypothesis-tree ranking, and the assumption labels.

> Reviewer R judges the **root cause** (Phase 1). The Phase-2 `red-pen` (Step 2.3)
> judges the **solutions**. Different targets — both fire.

As each reviewer returns, verify its file exists and mark its row `completed`.
Handle failures by looping back (offending row → `in-progress`, artifact
rewritten); do not argue with the reviewer (Gotcha #11):

- Reviewer L fail → Step 1.10 (re-edit doc + relink).
- Reviewer T fail → Step 1.8/1.9 (fix/re-run the test) or Step 1.7.5 (correct the
  verdict).
- Reviewer R `revise` → Step 1.10. `redesign` → escalate to the user.
  `reject` / `needs-more-info` → back to Stage 2b (gather more evidence).

Only when all three reviewers pass (or their concerns are resolved) proceed to the
Phase Gate.

---

## Phase Gate: User Review

Mark plan.md row 21 `blocked-on-user`. Present a summary of the Phase 1 findings
to the user:
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

On agreement, mark row 21 `completed`.

---

## Phase 2: Solution Discussion

**Enter plan mode before proposing solutions.** Use `update_plan` to structure
the solution design. The plan file serves as the working draft for solution
proposals — the analysis doc remains untouched until the user explicitly approves.

### Step 2.1: Read Analysis Doc and Enter Plan Mode

Mark plan.md row 22 `in-progress`. Re-read the analysis doc. Note the verified root
cause, design intention, and proof test results. These ground the solution
discussion.

Then enter plan mode:
```
update_plan
```

### Step 2.2: Draft Solutions

Draft solutions in the plan file. For each viable approach, present:
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

These are **drafts**. They go in front of the independent reviewer (Step
2.3) before they go in front of the user.

### Step 2.3: Mandatory Independent Review

Sherlock does not present its own first-draft solutions to the user. Before
the user sees anything, the drafts go through the `red-pen` skill,
which spawns an isolated reviewer with no shared memory and asks for an
independent second opinion — including the freedom to propose a redesign
that the original drafts missed.

Spawn an independent `worker` reviewer:

```
spawn_agent(
  role: "worker",
  task: "red-pen review of <absolute path to bug-<id>-analysis.md> and <absolute path to plan/draft solutions doc>"
)
```

The reviewer will:
1. Read the analysis doc and the draft solutions, verify
   citations against source, and writes a structured review to
   `<run-dir>/bug-<id>-review.md`.
2. Return a 4-line summary (verdict + headline + path + iteration).

Do **not** invoke the reviewer multiple times in parallel; one review per
draft set. Do **not** pass conclusions to the reviewer — the skill enforces
file-path-only inputs.

### Step 2.4: Consider the Review

Read the review doc at `<run-dir>/bug-<id>-review.md`. Handle by verdict:

| Verdict | Action |
|---------|--------|
| `approve` | Proceed to Step 2.5. |
| `approve-with-concerns` | Apply the cited concerns to the drafts. If changes are non-trivial, re-invoke `red-pen` (Step 2.3). Otherwise proceed. |
| `revise <option>` | Apply the cited changes to that option. If the diff is non-trivial, re-invoke `red-pen`. Otherwise proceed. |
| `redesign` | **Stop. Do not silently expand scope.** The reviewer has proposed a structurally different fix that resolves the root cause and other latent issues. Surface the redesign to the user explicitly: include the latent-issue list and the scope estimate from the review doc, and ask whether to (a) pursue the redesign (loop back to Phase 1 with the broader scope so the analysis doc captures the new framing), (b) take a smaller fix anyway (note the redesign in *Related Context* for future work), or (c) split into two changes. Do not proceed until the user picks a direction. |
| `reject` | Loop back to Phase 1 Step 1.4 with the reviewer's open questions. Likely the root cause needs more work. |
| `needs-more-info` | Answer the reviewer's open questions (may require more Phase 1 work or a user clarification), then re-invoke. |

When you re-invoke the reviewer after revisions, treat that as a separate
review run — the review doc gets a `-N` suffix, both reviews are kept on disk.

### Step 2.5: Present Solutions to User

Now — and only now — present the (revised, reviewed) solutions to the user.
The presentation must include:

1. The vetted solutions (description, pros, cons, effort, risk).
2. An **Independent review** subsection citing the verdict, headline
   finding, and a relative link to the review doc on disk. Do not paraphrase
   the review's reasoning — let the user read it directly if they want
   detail.

### Step 2.6: Discussion Loop

Interactive discussion with the user. They may:
- Ask for more detail on a solution
- Reject all solutions and ask for alternatives
- Request more Phase 1 research (loop back to relevant step)
- Share their own analysis or opinions
- Disagree with the reviewer (in which case: ask the user to articulate
  why, and decide together whether to override the verdict — do not
  argue with the reviewer in the analysis doc)

**Do NOT update the analysis doc during discussion.** It remains stable
ground — the last agreed-upon state. Only update when the user gives
explicit approval.

### Step 2.7: Write Solutions to Analysis Doc

Only on explicit user signal ("write it down", "update the doc",
"document this", etc.).

Exit plan mode first:
```
update_plan
```

Then append the **## Proposed Solutions** section to the analysis doc with:
- Each option described with pros/cons
- Comparison table (Pros, Cons, Effort, Risk columns)
- **Independent Review** subsection: verdict + headline finding + link to
  the review doc on disk
- **Agreed Approach** section documenting the selected solution and
  reasoning, including any explicit user override of the reviewer's verdict
  (and why)

Mark plan.md row 22 `completed` once the solution review concludes, and row 23
`completed` once the solutions are written to the analysis doc. The run is then
fully `completed`/`skipped` in plan.md.

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
- For vendored third-party library bugs: always run the T3 diagnostic first to
  determine scope. Then follow the appropriate branch:
  - **Branch A** (library bug): library test + Firefox test, upstream fix
  - **Branch B** (Firefox integration): Firefox test only, integration fix
  - **Branch C** (split): both tests, fixes in both layers
- **Subagent teams run in waves**: launch all Stage 2a teams (B, H), then all
  applicable Stage 2b teams (C, L, D, X, T), then the Phase-5 reviewers
  (L, T, R). Use `worker` for artifact-producing teams and `explorer` for broad
  search or hypothesis generation. Each team owns a file under
  `teams/` or `review/`; the main agent reads files, never transcripts. See
  `references/agent-teams.md`.
- **Read the review doc, don't restate it**: when surfacing the
  `red-pen` result to the user, link the review doc instead of
  paraphrasing — paraphrasing dilutes the reviewer's exact wording and
  defeats the point of the independent second opinion.
