---
name: sherlock
description: >
  First-principles problem solving for Firefox bugs. Evidence-based root cause
  analysis with permanent source links and proof tests, then invariant-driven
  solution design, independent evaluation, implementation, and documentation.
argument-hint: "<bug-id> [output-dir] [report-path-or-dir] | --resume <run-dir>"
allowed-tools:
  - Bash(git:*)
  - Bash(jj:*)
  - Bash(searchfox-cli:*)
  - Bash(bmo-to-md:*)
  - Bash(./mach:*)
  - Bash(.claude/skills/sherlock/sherlock-config:*)
  - Bash(mkdir:*)
  - Bash(cp:*)
  - Bash(ls:*)
  - Bash(find:*)
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - AskUserQuestion
  - WebFetch
  - TaskCreate
  - EnterPlanMode
  - ExitPlanMode
  - Agent
  - Skill
---

# Sherlock: Root Cause Analysis and Solution Design

Follow the `source-permalinks` skill for ALL source and documentation references.
Follow `references/spec-check.md` when verifying web specification compliance.
Follow `references/gecko-architecture.md` for Gecko architecture lookups.
Follow `references/agent-teams.md` for the agent-team I/O contracts and prompts.
Follow `references/first-principles.md` for the Reframe phase's method.
Follow `references/impl-skill-discovery.md` for the Implement phase's skill discovery.

## Phases

Phases are **named, not numbered** — they do not always run in a straight line,
and the numbering used to lie about that.

| Phase | Question it answers | Ends with |
|---|---|---|
| **Intake** | Where does this run live? | Run dir + pinned revision |
| **Diagnose** | *Why* does this bug happen? | Verified root cause + proof tests |
| **Diagnosis Review** | Is that root cause actually right? | **Review #1** (L / T / R) |
| *Gate* | — | User agrees the root cause |
| **Reframe** | What must be **true** so this cannot happen? | Named design principles + invariants |
| *Gate* | — | User adopts principles |
| **Design** | What are all the ways to get there? | Option set + roadmaps + comparison |
| *Gate* | — | User agrees the option set |
| **Decide** | Which one, given reality? | Ranked recommendation |
| *Gate* | — | User reviews the evaluation, before red-pen |
| **Decide** (cont.) | Does an independent reviewer agree? | **Review #2** + response |
| *Gate* | — | User approves the implementation choice |
| **Implement** | Make it real. | Patches, FAIL→PASS proof, follow-up list |
| **Consolidate** | What did we learn? | Every doc reconciled, run FINISHED |

Two independent reviews are mandatory and judge different things: **Reviewer R**
challenges the root cause; the **Decide red-pen** challenges the solutions.

### The gate contract

All five gates behave identically, and every one of them must do all four steps —
a gate that only handles agreement leaves the run stuck in `blocked-on-user` the
moment the user pushes back, and a crash there re-presents a summary that no longer
matches the artifacts:

1. Set the gate's row `blocked-on-user` **before** presenting.
2. On agreement → row `completed`, proceed.
3. On disagreement → record the objection **verbatim** in plan.md Notes, set the
   gate row back to `pending`, set the named upstream rows `in-progress`, and re-run
   forward from there. Re-present the gate only once the artifact has been rewritten.
4. Never proceed past a gate on inferred consent. Silence is not agreement.

| Gate | Row | On disagreement, reopen |
|---|---|---|
| Root cause agreed | 21 | the offending Diagnose rows (4/5/7/8.5/15/16.x/16.5/17) **and** re-run reviewers 18/19/20 |
| Principles agreed | 28 | 27 (and 23–26 if new evidence is needed) |
| Option set agreed | 34 | 31/32/33 — **append** an option, never rewrite one |
| Evaluation reviewed | 37 | 35 if the criteria or weights change, else 36 |
| Implementation approved | 40 | 36 and 39 — take the next-preferred option |

The generate/judge split is deliberate. Reframe and Design deliberately ignore
cost — architecture revamps are on the table, reviewer pushback is not a
consideration. Practicality enters only in Decide. Collapsing the two produces
the smallest local patch every time, which is the failure mode this workflow
exists to prevent.

Sherlock runs are **persistent and resumable**. Every run writes a `plan.md`
progress table to its run directory; each team and each reviewer writes its
findings to a dedicated file. If a session halts (server unavailable, context
exhausted, power outage, kill), re-invoke with `--resume <run-dir>` (or just
`/sherlock <bug-id>` — the bug id locates the run dir) and the skill continues
from the first non-completed row. See **Intake** and `references/plan-template.md`.

**Arguments:** $0

Parse the arguments:
- `--resume <run-dir>` present → **resume mode** (skip fresh setup; see Intake).
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
   as facts. Read the code before making any claim about code behavior. This
   applies in every phase, including the first-principles ones.
2. **ALWAYS use revision-pinned links** — follow the `source-permalinks` skill.
   Never use trunk/tip URLs (`firefox-main/source/...`) in any document.
3. **Tests are PROOFS for root cause claims** — they must demonstrate the root cause
   is correct. They are reusable for TDD later, but their primary purpose here is evidence.
4. **Debug logs go in separate files** — never inline multi-line log output in the
   analysis doc. Store under `firefox/debug/` (or `<library>/debug/`) as
   `bug-<id>-debug-<desc>.log` and reference with relative links.
5. **Do NOT write solutions in Diagnose** — Diagnose is purely diagnostic.
6. **Do NOT write patches in Reframe** — Reframe produces invariants, elimination
   candidates and design principles: what must be *true*, not what code to write.
   If you are writing a diff, you are in the wrong phase.
7. **Cost is not an argument before Decide** — "too big", "the reviewer will
   object", "we'd never land that" are out of scope in Reframe and Design. A
   pre-filtered design space makes the Decide phase useless.
8. **Private bugs** — never log titles, descriptions, components, or root cause details
   outside the output directory. History log for private bugs: `date | bug_id | PRIVATE` only.
9. **Check normal/debug build BEFORE requiring ASan/TSan** — try reproducing in
   current build first, then debug build, then sanitizer builds.
10. **NEVER read, parse, or print any API key** — all API access goes through
    `sherlock-config` or `bmo-to-md`. Never read TOML config files containing keys.
    Never use `python3` to parse config files.
11. **Delegate research, not synthesis** — subagents do bounded fact-finding
    (bug fetch, code path tracing, git archaeology, invariant enumeration). The
    main agent decides what the facts mean. Never let a subagent declare the root
    cause, name the design principles, or pick the solution.
12. **Three hypotheses minimum** — single-hypothesis RCAs anchor too early.
    `Diagnose.5` is mandatory; do not skip it even when one cause feels obvious.
13. **The reviewers are independent** — when `red-pen` returns `revise`
    or `redesign`, do not argue with the verdict. Either fix the artifact,
    escalate to the user (for `redesign`), or loop back. This applies to both
    Reviewer R (root cause) and the Decide red-pen (solutions).
14. **Fleet F must never see Reframe artifacts** — the free-mind fleet's isolation
    is the anti-anchoring control on the whole Reframe phase. Name the forbidden
    paths in its prompt, and never paste principles content into it.
15. **Persist every team output to disk** — each team and each reviewer owns a
    named output file in the run dir (`teams/*.md`, `review/*.md`). Their findings
    live there, not just in the main-agent transcript. A halted session resumes by
    reading those files. Never rely on a subagent transcript to retain results.
16. **Update `plan.md` at every transition** — set a row to `in-progress`
    *before* starting the work and `completed` after the artifact is on disk.
    Never leave a row silently behind; the progress table is the hand-over
    document for `--resume`.
17. **Loop-backs append, never rewrite** — a new option is appended to the
    solutions doc with a bumped revision; a reverted implementation is recorded in
    the change log. The documents are the run's history as well as its state.
18. **Never file a bug silently** — `sherlock-config` cannot create bugs. A
    follow-up is only `completed` when it has a real bug id or was explicitly
    handed to the user.

---

## Subagent delegation policy

The main agent's context is reserved for **synthesis** — connecting evidence,
forming and pruning hypotheses, deciding what is verified vs assumed,
articulating the root cause, naming the design principles, categorising options,
and judging. Bounded research tasks are delegated to subagents so the main
context stays focused.

**Delegate** to a subagent when the task is:
- **Bounded**: clear input, clear output shape, no interactive judgment.
- **Voluminous**: produces a lot of intermediate text (raw bug comments,
  searchfox dumps, git log archaeology, call-site censuses) that the main agent
  does not need in full.
- **Parallelizable**: e.g., trace Firefox + library simultaneously; brainstorm
  one approach per principle.

**Do NOT delegate**:
- Hypothesis selection or pruning (Team H is advisory; the tree is yours).
- "What does this evidence mean for the root cause?" — Synthesis (`Diagnose.12`).
- The verdict, the root cause, and the design-relation sentence.
- The Reframe framing answers (Q1/Q2) and the naming of design principles.
- Design categorisation — clustering, merging, roadmap sequencing.
- The entire Decide phase — criteria, weights, scoring, recommendation.
- Gates and user-facing decisions.
- The structural self-check (`Diagnose.16`).
- Any step that requires judging two competing claims.

Bounded research is delegated to **agent teams** — multiple `Agent` calls in a
single message that run concurrently. Sherlock's workflow is gated, so teams
launch in four waves (full contracts in `references/agent-teams.md`):

- **Wave 1 — intake teams** (`Diagnose.1`, before any hypothesis exists):
  **Team B** (bug-context digest) and **Team H** (hypothesis brainstorm,
  advisory only).
- *(main-agent gate: failure-pattern classification, investigation plan,
  hypothesis tree, working branch — none delegated)*
- **Wave 2 — research teams** (`Diagnose.8`, after the primary hypothesis is
  chosen): **Team C** (Firefox code-trace), **Team L** (library code-trace, when
  third-party), **Team D** (design archaeology), **Team X**
  (cross-browser/spec), **Team T** (test-framework scout + draft).
- *(main agent: Synthesis → verdict + root cause + broken invariant)*
- **Wave 3 — Reframe teams** (`Reframe.2`): **Team P** (problem framing),
  **Team E** (elimination scan + call-site census), **Team I** (invariant
  discovery), **Team W** (widening & unification).
- *(main agent: principles doc)*
- **Wave 4 — Design fleets** (`Design.1`): **Fleet G** (guided, one agent per
  adopted principle), **Fleet F** (free-mind, isolated). Then **Team M**
  (comparison matrix) at `Design.3`.

Each team **writes its full findings to a dedicated file** under `<run-dir>/teams/`
and returns only a ≤10-line summary. The main agent reads the files, never the
transcripts. Each invocation must:
- Pass inputs as **file paths and explicit values** — not as "the bug we're
  investigating".
- Specify the **output shape** and the target output file.
- Include the framing appropriate to its wave: *"return the requested artifact
  only"*, plus the wave's prohibition (no root cause for Waves 1–2, no patches
  for Wave 3, no ranking for Wave 4).

A team never declares the root cause, the verdict, the hypothesis ranking, or the
chosen solution.

---

## Phase: Intake

Every run lives in a **per-run subdirectory** `<output-dir>/sherlock-bug-<id>/`
(the **run dir**; the `sherlock-` prefix keeps it from colliding with other
per-bug skills sharing an output root, e.g. `/triage`, which uses
`triage-bug-<id>/`). `plan.md` (the progress table, from `references/plan-template.md`)
and all artifacts live inside it. The bug id is the run identity — there is no
slug. Re-running the same bug resumes the existing run dir.

### Resume branch

Enter this branch if the invocation contains `--resume <run-dir>`, **or** if a
fresh invocation's `<output-dir>/sherlock-bug-<id>/plan.md` already exists (in which case
ask via `AskUserQuestion`: "Found an existing analysis for bug `<id>` at `<path>`.
Resume, or start fresh?" — "start fresh" archives or overwrites per the user).

1. `Read <run-dir>/plan.md`. Recover the bug id, the pinned **Searchfox
   revision**, the progress table, and the Notes.
2. Restore session variables: set `$SHERLOCK_REV` from the plan.md revision line
   — **do NOT re-resolve it**; every link on disk depends on it. Re-resolve only
   `$SHERLOCK_AUTHOR` via `sherlock-config --get-patch-author` (deterministic).
3. Confirm the Firefox working branch still exists:
   `git rev-parse --verify sherlock/bug-<id>`. If it is missing, **do not silently
   recreate it** — an empty branch alongside `completed` rows 16.x/17 means the run
   believes proof tests exist that are gone, and the FAIL→PASS evidence the whole
   workflow rests on has quietly evaporated. Instead:
   1. Try to recover the tip by SHA: the **Branch tip** field in plan.md, then
      `git reflog`. If found, `git branch sherlock/bug-<id> <sha>` and carry on.
   2. If unrecoverable, set row 8 **and every 16.x row and row 17** back to
      `pending`, and tell the user the proof tests must be rebuilt. Never continue
      past a missing branch with 16.x still `completed`.
   Note `$SHERLOCK_REV` is not a valid recreation point — it may be a searchfox
   revision that does not exist locally. `SHERLOCK_BASE` in plan.md is the branch point.
3b. Before re-running any `in-progress` **Implement** row, check for work in flight:
   `git status --porcelain` and `git log --oneline "$SHERLOCK_BASE"..HEAD`. Present
   uncommitted changes to the user rather than re-implementing over them.
4. Announce in ≤2 lines: "Resuming sherlock bug `<id>` at `<run-dir>`; next task:
   `<first non-completed row>`."
5. Jump to the phase containing the first `pending`/`in-progress` row. Treat
   `in-progress` rows as un-finished — re-run them; their output file overwrites.
   Trust `completed` rows (read their artifacts, do not regenerate). Re-present
   `blocked-on-user` rows (the gates) to the user.
6. If resuming into the Implement phase, re-run skill discovery (the tree may
   have changed) but carry forward the recorded pick — see
   `references/impl-skill-discovery.md`.
7. Skip the rest of Intake.

### Fresh-run branch

1. **Check setup:** `.claude/skills/sherlock/sherlock-config --check-setup`
   reports API key availability, `bmo-to-md`, `searchfox-cli`, and configured
   output dir. If any prerequisite is missing, present options to the user.
2. **Resolve output dir** (priority): CLI arg → `sherlock-config --get-output-dir`
   → ask via `AskUserQuestion`, then persist with
   `sherlock-config --set-output-dir <path>`.
3. **Parse** bug id and optional report-path (see Arguments above).
4. **Create the run dir and subdirs:**
   ```bash
   mkdir -p <output-dir>/sherlock-bug-<id>/teams
   mkdir -p <output-dir>/sherlock-bug-<id>/review
   mkdir -p <output-dir>/sherlock-bug-<id>/firefox/fix
   mkdir -p <output-dir>/sherlock-bug-<id>/firefox/debug
   ```
   `<library>/` subdirs are created later, when `Diagnose.9` activates (T1).
   Hereafter `<run-dir>` = `<output-dir>/sherlock-bug-<id>/`.
5. **Resolve `$SHERLOCK_REV`** (pin a searchfox revision for the whole run so all
   links are permanent):
   1. Get local HEAD: `git rev-parse HEAD`
   2. Validate on searchfox:
      `WebFetch https://searchfox.org/firefox-main/rev/<hash>/moz.configure`
      - 200 → use this hash as `$SHERLOCK_REV`
      - 404 (not yet indexed) → fetch
        `https://searchfox.org/firefox-main/source/moz.configure` and extract the
        latest indexed revision from the page
   3. For ESR/beta branches, repeat with the appropriate repo id
      (e.g. `firefox-esr128`).
6. **Resolve `$SHERLOCK_AUTHOR`:**
   `SHERLOCK_AUTHOR=$(.claude/skills/sherlock/sherlock-config --get-patch-author)`
   (reads `patch_author` from config, else `git config user.name`/`user.email`).
   All generated patches use this as the commit author.
7. **Write `plan.md`** from `references/plan-template.md` into `<run-dir>/`,
   substituting `{bug_id}`, `{start_timestamp}`, `{public_or_private}`,
   `{abs_run_dir}`, `{rev_short}`, `{rev_full}`. Row 1 `in-progress`, rest
   `pending`.
8. Mark row 1 `completed` and append a Notes line. Confirm to the user in ≤3
   lines: bug id, run-dir path, `$SHERLOCK_REV` short hash, "resume with
   `/sherlock --resume <run-dir>` if I stop".

> The bug report itself is fetched by **Team B** in `Diagnose.1`, not here
> — unless a `report-path` was provided, in which case read it directly and pass
> its path to Team B as a pointer instead of re-fetching.

### Output Directory Structure

The run dir uses a uniform layout. Firefox patches go in `firefox/`, third-party
patches go in `<library>/`. Both use identical `fix/` + `debug/` substructure.
Patches are numbered so they apply in order.

```
<output-dir>/sherlock-bug-<id>/                 # the run dir (resume key = bug-<id>)
  plan.md                                       # Progress table + resume doc
  bug-<id>-analysis.md                          # Diagnose: the root cause
  bug-<id>-principles.md                        # Reframe: invariants + design principles
  bug-<id>-solutions.md                         # Design: option set + roadmaps
  bug-<id>-evaluation.md                        # Decide: criteria + ranking + review response
  bug-<id>-review.md                            # Decide: red-pen on solutions (-N per re-run)
  bug-<id>-followups.md                         # Implement: follow-up + blocking issues
  bug-<id>-report/                              # Bug report from bmo-to-md (Team B)
  bug-<dup_id>-report/                          # One per duplicate (Team B)
  bug-<id>-attachments/                         # Attachments (Team B)
  teams/                                        # Team output files
    team-b-bug-context.md                       #   Wave 1
    team-h-hypotheses.md                        #   Wave 1
    team-c-code-trace-firefox.md                #   Wave 2
    team-l-code-trace-library.md                #   Wave 2
    team-d-design-archaeology.md                #   Wave 2
    team-x-cross-browser.md                     #   Wave 2
    team-t-frameworks.md                        #   Wave 2
    synthesis.md                                #   main agent
    team-p-problem-framing.md                   #   Wave 3
    team-e-elimination.md                       #   Wave 3
    team-i-invariants.md                        #   Wave 3
    team-w-widening.md                          #   Wave 3
    design-g-<principle-slug>.md                #   Wave 4 (one per adopted principle)
    design-f<N>-freemind.md                     #   Wave 4 (one per lens)
    analysis-for-fleet-f.md                     #   Wave 4 (stripped analysis doc)
    team-m-comparison.md                        #   Wave 4
  review/                                       # Diagnosis Review files
    L.md   T.md   R.md                          #   Reviewer verdicts
    bug-<id>-rootcause-review.md                #   Full red-pen review (REVIEW #1)
  firefox/
    fix/                                        # Clean patches for Firefox
      01-test-<desc>.patch                      #   Regression test
      02-fix-<desc>.patch                       #   Fix on top of test
      bug-<id>-verify-run.log                   #   FAIL→PASS verification (Implement.4)
    debug/                                      # Firefox debug artifacts
      01-test-<desc>.patch                      #   Same test patch(es)
      02-debug-firefox-instrumentation.patch    #   Instrumentation on top
      bug-<id>-mozconfig                        #   Special build config, if needed
      bug-<id>-test-run.log                     #   Test execution output
      bug-<id>-debug-<desc>.log                 #   Captured debug output
  <library>/                                    # Only when third-party involved
    bug-<id>-upstream-<library>.md              # Upstream report (sanitized)
    fix/                                        # For upstream: clean, applicable
      01-test-<desc>.patch                      #   Standalone test (if no injection)
      02-fix-<desc>.patch                       #   Fix on top of test
    debug/                                      # For upstream: reproduction aid
      01-test-<desc>.patch                      #   Test (may include injection)
      02-debug-lib-instrumentation.patch        #   Logging on top of test
      bug-<id>-debug-lib-build.log              #   Library build output
      bug-<id>-debug-lib-<desc>.log             #   Library debug output
```

The `<library>/` folder is created only when `Diagnose.9` is active (Branch A, B,
or C). For Branch B (Firefox integration bug), `<library>/` may contain only the
T3 diagnostic logs — no `fix/` patches since the library has no bug.

The `<library>/` output structure mirrors three git branches in the local library
repo (see T3 for details):
- `sherlock/bug-<id>/test` — test commits (base for debug and fix)
- `sherlock/bug-<id>/debug` — instrumentation on top of test
- `sherlock/bug-<id>/fix` — fix on top of test (created in A4/C4)

The `firefox/` output structure mirrors the Firefox working branch (see `Diagnose.6`):
- `sherlock/bug-<id>` — test commits, then fix commits on top (Implement)
- `sherlock/bug-<id>-debug` — instrumentation on top of tests (temporary)

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
- **Security bugs invert the order** at implementation time — see `Implement.3`.

Within each `debug/` folder:
- Always contains test patches (including injection-based ones), with debug
  instrumentation patches on top.
- Goal: developers can apply these patches and immediately reproduce + confirm
  the issue.

**Numbering**: Use two-digit prefixes (`01-`, `02-`, ...) for apply order,
allocated **globally across the whole run**, not per hypothesis — two `to-test`
hypotheses must not both produce an `01-test-*.patch`, or `git am` order becomes
ambiguous. Test patches take the low numbers in hypothesis order
(`01-test-h1-…`, `02-test-h2-…`); fix patches continue from the next free number.
Use descriptive names after the prefix (e.g., `01-test-ogg-truncated-stream.patch`,
`02-fix-bounds-check-vorbis-window.patch`).

**Patch format**: Always use `git format-patch` so patches can be applied via
`git am -3` (with three-way merge) or `git apply`. This requires committing
changes before generating the patch.

Patch generation pattern (commits stay on the branch; `$SHERLOCK_AUTHOR` resolved
in Intake):
```bash
git add <files>
git commit --author="$SHERLOCK_AUTHOR" -m "<descriptive message>"
git format-patch -1 --stdout > <run-dir>/<path>/<NN>-<desc>.patch
```
The commit message should describe what the patch does (e.g.,
"Add gtest for OOB read in vorbis window function" or "Add debug
instrumentation for decode path tracing"). Commits are kept on the working
branch — do NOT reset. The branch history IS the ordered patch series.

`<library>/` subdirectories are created when `Diagnose.9` activates and the library
is identified (T1): `mkdir -p <run-dir>/<library>/fix <run-dir>/<library>/debug`.

---

## Phase: Diagnose

Focus entirely on WHY the bug occurs. No solutions, no invariant design — those
are later phases with their own gates.

### `Diagnose.1`: Understand the Bug — Wave 1 teams (Team B + Team H)

Launch the **Wave 1 intake teams in one message** (two `Agent` calls) so they
run concurrently. Full I/O contracts and prompt templates are in
`references/agent-teams.md`:

- **Team B — bug-context digest.** Fetches the main bug + each duplicate +
  attachments + Treeherder failure-distribution + the per-branch status flags,
  and writes the digest to `<run-dir>/teams/team-b-bug-context.md` (sections:
  Identity, STR, Attachments, Duplicates, Treeherder, Branch status, Pointers).
  This single fetch serves `Diagnose.2` (duplicates), `Diagnose.3` (failure
  pattern), `Diagnose.13a` (attachments) and `Decide.1` (uplift pressure) —
  read the file, do not re-fetch. If a `report-path` was provided in Intake, pass
  it as a pointer so Team B skips the main fetch.
- **Team H — hypothesis brainstorm (advisory).** Brainstorms ≥3 candidate
  hypotheses (mechanism / confirming / refuting / probe cost) to *feed* the
  main agent's hypothesis tree (`Diagnose.5`). It writes
  `<run-dir>/teams/team-h-hypotheses.md`. **It does not rank or pick a primary
  hypothesis** — that is main-agent work (anti-anchoring, Gotcha #12). Seed it
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
- Per-branch status flags (carried forward to `Decide.1`)

If the bug has any `sec-*` keyword or is in a security group, the analysis doc
MUST include a **Security Rating** section.

### `Diagnose.2`: Check Duplicates and Related Bugs

Mark plan.md row 4 `in-progress`.

**Create the analysis doc now**, from `references/analysis-template.md`, with every
section still a placeholder. Rows 4, 5 and 7 each fill one section of it, and from
here on the doc is only ever **edited** — never re-created with `Write`, which would
truncate the earlier sections. `Diagnose.15` completes the remaining sections rather
than authoring the file.

This ordering exists so those three rows have a real on-disk artifact when they are
marked `completed`. Otherwise a resume trusts them and the duplicate findings, the
failure-pattern classification, and the hypothesis tree are silently gone — and the
hypothesis tree is what `Diagnose.12` re-ranks and `Diagnose.16` checks.

Team B's digest already includes duplicate fetches and a "Duplicates" section. Read
that section.

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

### `Diagnose.3`: Failure Pattern Analysis

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

### `Diagnose.4`: Plan the Investigation

Mark plan.md row 6 `in-progress`. **Enter plan mode** before starting the deep
investigation. Use `EnterPlanMode` to draft an investigation plan based on what
`Diagnose.1`–`Diagnose.3` (and Team H's candidate hypotheses) revealed.

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
suggest additional code areas, or redirect the investigation. Use `ExitPlanMode`
after the user approves or provides feedback. Record plan decisions in plan.md
Notes and mark row 6 `completed`.

### `Diagnose.5`: Build the Hypothesis Tree

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

### `Diagnose.6`: Create Firefox Working Branch

Mark plan.md row 8 `in-progress`. Create a working branch in the Firefox tree for
all sherlock test and fix commits:
```bash
git checkout -b sherlock/bug-<id> HEAD
```

All test commits go on this branch first, then fix commits on top (Implement):
```
HEAD
  └── sherlock/bug-<id>               ← test-1 → test-2 → ... → fix-1 → fix-2 → ...
        └── sherlock/bug-<id>-debug   ← instrumentation on top of tests (temporary)
```

The `sherlock/bug-<id>-debug` branch is created later (`Diagnose.13e` or B1.4) when
instrumentation is needed. It forks from the last test commit and is used only for
debug capture — it is not part of the final patch series.

> **Why the hyphen.** Git stores branches as files under `refs/heads/`, so
> `sherlock/bug-<id>` and `sherlock/bug-<id>/debug` **cannot coexist** — the second
> `git checkout -b` fails with `cannot lock ref … 'sherlock/bug-<id>' exists`. Hence
> `-debug` as a sibling, not `/debug` as a child. The *library* repo uses
> `sherlock/bug-<id>/test|debug|fix` and that is fine, because there is no bare
> `sherlock/bug-<id>` ref in that repo. Do not "tidy" the Firefox name to match.

**Record the branch point.** The reorder in `Implement.3` and the recovery path in
Intake both need the commit this branch was cut from, and `$SHERLOCK_REV` will not
serve — it may be an older *searchfox-indexed* revision, not local HEAD:

```bash
SHERLOCK_BASE=$(git rev-parse HEAD)   # BEFORE creating the branch
```

Write `SHERLOCK_BASE` into plan.md's header block. Mark row 8 `completed`.

### `Diagnose.7`: Research Code Paths

Mark plan.md row 8.5 `in-progress`. This is the row loop-backs target when the
investigation has to be reopened (`Diagnose.14` on an unexpected PASS, a red-pen
`reject`, `Decide.2` on a moved root cause, `Implement.4` when the test fails to
flip) — so it must exist as a row, not just as a step.

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

For third-party libraries, consult `references/upstream-libs.md`. **Decide here
whether `Diagnose.9` will activate** — do the suspect files match a path in that
reference? Record the yes/no in plan.md Notes; `Diagnose.8` needs the answer to know
whether to launch Team L and whether to skip Team D. Mark row 8.5 `completed`.

### `Diagnose.8`: Wave 2 research teams (C, L, D, X, T)

Once the primary hypothesis and entry symbols are chosen (`Diagnose.5`/`Diagnose.7`),
launch the **Wave 2 research teams in one message** (multiple `Agent` calls) so
they run concurrently. Full I/O contracts and prompt templates are in
`references/agent-teams.md`. All Wave 2 teams are **read-only** — none of them
build. Set each applicable team's plan.md row `in-progress` before launching:

- **Team C — Firefox code-trace** (row 9). Numbered, revision-pinned trace of the
  call path for the primary hypothesis → `teams/team-c-code-trace-firefox.md`.
- **Team L — library code-trace** (row 10). Only when `Diagnose.9` applies; same
  contract with upstream permalinks → `teams/team-l-code-trace-library.md`.
  Vendored revision: `git show HEAD:media/<lib>/moz.yaml | grep revision`.
- **Team D — design archaeology** (row 11). Git-history archaeology of the suspect
  code → `teams/team-d-design-archaeology.md`. **Skip (row `skipped`) when
  `Diagnose.9` is active** — design intention is covered in the branch workflow
  (A1/B1/C1). Its **function contract** output is the primary input to the
  Reframe phase, so extract it precisely.
- **Team X — cross-browser / spec** (row 12). Spec citation + cross-engine
  behaviour table → `teams/team-x-cross-browser.md`. Skip (row `skipped`) for
  internal-only bugs with no web surface.
- **Team T — test-framework scout + draft** (row 13). Per live hypothesis: pick a
  framework, find a neighbour test, and draft the proof-test source →
  `teams/team-t-frameworks.md`. Team T does NOT build (builds serialize — see
  `Diagnose.13`/`Diagnose.14`).

As each team returns, verify its output file is non-empty and mark its row
`completed`; if a team aborts, leave its row `in-progress` for `--resume`. The
main agent **reads the files** (not transcripts) during Synthesis and reasons
about which trace steps correspond to the primary hypothesis. Read
the `source-permalinks` skill for URL patterns; every code reference is
revision-pinned with `$SHERLOCK_REV`.

### `Diagnose.9`: Third-Party Library Sub-Workflow (Conditional)

If the **suspected failing path** does not touch vendored third-party code, mark
plan.md rows 14 and 10 (Team L) `skipped` and continue at `Diagnose.10`/`Diagnose.12`.

The test is the *suspected* path, not the confirmed root cause — the root cause is
not established until `Diagnose.12`, well after this row, and `Diagnose.8` already
needs the answer to decide whether to launch Team L and whether to skip Team D. Make
the call at the end of `Diagnose.7` by checking the suspect files against
`references/upstream-libs.md`, and record the yes/no in plan.md Notes.

If the root cause involves vendored third-party code (file paths matching
`references/upstream-libs.md`), activate this sub-workflow. It is **plan.md row
14 — a gate**. T1/T2/T3 are sequential and main-agent-driven (NOT teams): T1 needs
user input; T3 is a serialized diagnostic build whose result chooses the branch.

Ordering with the Wave 2 teams: the read-only traces (Team C + Team L) launched
in `Diagnose.8` run **before** T3's build, so the trace informs which path to test.
After T3 resolves scope, **write the scope verdict (Branch A / B / C) into plan.md
Notes** and **append the branch sub-rows** under row 14 (see
`references/plan-template.md` "Dynamic rows"). Recording the verdict in Notes lets
a resume that halts after T3 but before the rows are written reconstruct them.
Mark row 14 `blocked-on-user` while T1 waits on the user, `in-progress` once T2/T3
are running, and `completed` once the scope is recorded and the branch rows are
appended. Getting that first transition right matters: left as `in-progress`, a
crash during T1 makes resume re-run the whole gate including T3's diagnostic build. Branch downstream work then runs against those
appended rows.

#### T1: Check for Local Upstream Repo

Ask the user via AskUserQuestion:
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
  the authors faced. This replaces `Diagnose.10` for third-party code — write the
  findings to `teams/team-d-design-archaeology.md` using the same section shape Team D
  would have produced (introducing commit, original purpose, rationale, constraints,
  **function contract**, related code, drift signals). Wave 3 depends on that path.
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
- Include the T3 standalone test case (or reference it) — **but see the security
  exception below**
- Include the library-side code path trace from A1
- If a fix is verified (A4), include it as a suggested fix

> **Security exception — this overrides the bullet above.** If the bug carries any
> `sec-*` keyword, do **not** attach the T3 reproducer. For a memory-safety bug the
> reproducer *is* the exploitation detail, and this report is written to be filed
> publicly — which would disclose the vulnerability before any fix ships, the exact
> thing `Implement.3`'s commit ordering exists to prevent. Instead: describe the
> failing condition abstractly, hold the reproducer for the library's security
> contact, note in plan.md Notes that the report was filed in reduced form, and
> **ask the user before filing anything upstream on a security bug.**

This report should be suitable for filing as an upstream bug report or attaching
to a pull request / issue tracker entry.

**A4. Fix strategy (Implement phase):**

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

The Design phase should surface both:
- **Upstream fix**: submit to upstream, then update vendored copy via `./mach vendor`
  or manual update. Preferred for long-term health. Larger scope acceptable.
- **Local Firefox patch** (if urgent): apply as a patch on top of the vendored
  library pending upstream acceptance. Smaller scope, faster to land.

---

#### Branch B: Firefox Integration Bug (scope b)

The library works correctly — the bug is in how Firefox uses it (wrapper code, IPC
actors, threading model, lifecycle management, error handling around library calls).

**B1. Pivot investigation to Firefox code:**

Resume the standard investigation steps, focused on the integration layer:

1. **Code path trace** (`Diagnose.8`): Trace the Firefox integration code using
   searchfox revision-pinned links. Include the boundary where Firefox calls into
   the library and how results/errors propagate back.

2. **Design intention** (`Diagnose.10`): Study the Firefox integration code's git
   history. Why was the wrapper written this way? What assumptions does it make
   about the library's behavior?

3. **Proof test** (`Diagnose.13`): Create a Firefox test that reproduces the
   integration bug. Follow A2 steps 1-6: choose framework, register in manifest,
   commit on `sherlock/bug-<id>`, generate patch to `firefox/fix/` and
   `firefox/debug/`, build and run. No separate library test needed — the library
   is correct.

4. **Debug instrumentation** (`Diagnose.13e`): Create `sherlock/bug-<id>-debug`
   branch from the test commit. Add instrumentation, commit, generate
   `firefox/debug/02-debug-firefox-instrumentation.patch`.

5. **Run with instrumentation** (`Diagnose.14`): Build on the debug branch
   (`./mach build`), run tests, capture debug logs to `firefox/debug/`. Switch back
   to `sherlock/bug-<id>` (working branch with test commits only).

**B2. Fix strategy (Implement phase):**

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

**C4. Fix strategy (Implement phase):**

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

### `Diagnose.10`: Study Design Intention (Team D)

Design archaeology is **Team D**, launched in the Wave 2 wave (`Diagnose.8`). Its
full contract and prompt are in `references/agent-teams.md`; it writes
`teams/team-d-design-archaeology.md` (introducing commit, original purpose, design
rationale, constraints, function contract, related code, drift signals) and does
NOT claim how the root cause relates to the design.

**Team D is replaced, not dropped, when `Diagnose.9` is active** (set row 11
`skipped`). Design intention is instead recovered inside the branch workflow —
Branch A in A1, Branch B in B1, Branch C in C1 — but that work **must still be
written to `teams/team-d-design-archaeology.md`**, in the same section shape.

The filename is a contract, not a byproduct: `Reframe.1` reads it unconditionally,
and Team P and Team I both take it as a required input path. A third-party run that
leaves it absent hands Wave 3 three agents pointing at a file that does not exist.

During Synthesis the main agent reads the Team D file and writes the Design
Intention section in the analysis doc, **adding the two sentences the team
declined to write**: how the current root cause relates to (violates / reveals a
gap in / drifts from) the original design intention, and the **broken invariant**
(the property the contract implies should always hold, which the root cause shows
does not). Both are reserved for the main agent, and both are load-bearing for the
Reframe phase — solutions that respect the original design intention are more
likely to be correct and maintainable than patches that only address the symptom.

### `Diagnose.11`: Verify All Claims

Mark plan.md row 16.5 `in-progress`; mark it `completed` once every claim destined
for the analysis doc carries either a citation or an `[Assumption]` label.

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

### `Diagnose.12`: Synthesis (main agent, not delegated)

Mark plan.md row 15 `in-progress`. Read **all** Wave 2 team files (C, L, D, X,
T) and the Wave 1 files (B, H) — the files, not the subagent transcripts — and
write `<run-dir>/teams/synthesis.md`:

1. Merged code-trace + design-intention narrative; note any drift.
2. Re-rank the hypothesis tree against the gathered evidence. Revive any pruned
   hypothesis the evidence warrants — do not silently re-anchor.
3. Classify each hypothesis as `to-test` / `refuted` / `assumption-only`, citing
   the Team C/L/D/X evidence that drove the classification.
4. State the **verified root cause** with two-tier labels (`Diagnose.11`), plus the
   sentence on how it relates to the design intention (`Diagnose.10`).
5. State the **broken invariant** in one sentence — the property Team D's function
   contract implies should always hold, and that the root cause shows does not.
   This is the hand-off into Reframe; without it, Reframe re-derives the contract
   from scratch. It goes into the analysis doc's Design Intention section.
6. **Append one row 16.x to plan.md per `to-test` hypothesis**, naming the target
   proof-test patch and log paths (see `references/plan-template.md`). **If
   `Diagnose.9` is active**, the proof tests are tracked by the Branch rows under
   row 14 (A2/T3/C2) instead — append no 16.x rows and mark row 16 `skipped`.

A team never declares the root cause — this synthesis is the main agent's. Mark
row 15 `completed`.

### `Diagnose.13`: Evaluate and Create Proof Tests

This step processes the **row 16.x** entries Synthesis appended — one per
`to-test` hypothesis. **Builds serialize**: Team T already scouted the framework
and drafted the test source in parallel (`teams/team-t-frameworks.md`); the main
agent now writes, builds, and runs each test **one at a time**. Mark each row 16.x
`in-progress` before its build and `completed` after the result is captured.

**Note:** If `Diagnose.9` is active, skip this step — proof tests are already
created within the branch workflow:
- **Branch A**: T3 (library test) + A2 (Firefox test)
- **Branch B**: B1 (Firefox proof test)
- **Branch C**: C2 (both library and Firefox tests)

Read `references/test-frameworks.md` for framework selection and FuzzingFunctions mapping.

#### `Diagnose.13a`: Check Bug Attachments for Existing Testcases

Team B already fetched attachments to `<run-dir>/bug-<id>-attachments` — read from
there (do not re-fetch). If a testcase exists and uses `FuzzingFunctions`, apply
the mapping table from `references/test-frameworks.md`. Auto-convert to the
appropriate framework.

#### `Diagnose.13b`: Determine Test Framework

Team T already chose a framework and found a neighbour test per hypothesis
(`teams/team-t-frameworks.md`). Confirm its choice against the decision tree in
`references/test-frameworks.md`:
- Crash → crashtest (HTML-triggerable) or gtest (C++ only)
- Web-exposed + spec-defined → WPT (follow `references/spec-check.md` first)
- Web-exposed + Firefox-specific → mochitest
- Internal C++/Rust → gtest

#### `Diagnose.13c`: Check Build Requirements BEFORE Writing Tests

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
- Present to user for review via AskUserQuestion before building
- The user can invoke `/mozconfig` for full interactive configuration if preferred

#### `Diagnose.13d`: Write Proof Test

Start from Team T's drafted test in `teams/team-t-frameworks.md` (adapt it; do not
build inside Team T). Write the test into the tree, commit it on
`sherlock/bug-<id>`, then **build it serialized** (one `./mach build` at a time; FE-only
tests use `./mach build faster`). The test must:
- **FAIL without fix** — proving the bug exists (the root cause claim is correct)
- Be designed to **PASS after fix** — making it reusable for TDD development later
- Serve as **EVIDENCE** for the root cause claim

#### `Diagnose.13e`: Add Debugging Instrumentation

Create a debug branch from the current test commit for instrumentation:

```bash
git checkout -b sherlock/bug-<id>-debug
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
`Diagnose.14`, then you switch back to the main working branch.

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

### `Diagnose.14`: Run Tests and Capture Debug Logs

**Note:** If `Diagnose.9` is active, skip this step — tests are already run and
debug logs captured within the branch workflow:
- **Branch A**: T3 ran the library test; A2 ran the Firefox test
- **Branch B**: B1 ran the Firefox test with debug instrumentation
- **Branch C**: T3 ran the library test; C2 ran the Firefox test

**1. Build and run on the debug branch** (has test commits + instrumentation).
Builds serialize — one at a time:
```bash
# Should already be on sherlock/bug-<id>-debug from Diagnose.13e
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
ready for fix commits in the Implement phase).

**3. Generate test patches** from the branch history:
```bash
# Export each test commit to its own file. Always redirect — a bare
# `git format-patch --stdout` dumps the entire series into the transcript.
git format-patch -1 <commit> --stdout > <run-dir>/firefox/fix/01-test-<desc>.patch
cp <run-dir>/firefox/fix/01-test-<desc>.patch <run-dir>/firefox/debug/01-test-<desc>.patch
```

**For a `sec-*` bug, the proof-test patch goes only to `firefox/debug/`** at this
point — not to `firefox/fix/`. It enters the fix series in `Implement.3`, after the
fix commits, so a vulnerability-demonstrating test is never sitting first in the
landing order.

**4. Evaluate results** (mark each row 16.x `completed` with its result in Notes):
- Test **FAILS as expected** → confirms root cause, record as evidence
- Test **PASSES** (contradicts hypothesis) → re-examine root cause, loop back to `Diagnose.7` (row 8.5)
- Test **inconclusive** → note as `[Assumption]`, document what would make it conclusive

### `Diagnose.15`: Generate Analysis Documents

Mark plan.md row 17 `in-progress`.

**Primary analysis document** (always required):

The analysis doc already exists — `Diagnose.2` created it from
`references/analysis-template.md`, and rows 4/5/7 filled Related Context, Failure
Pattern and the Hypothesis Tree. **Complete the remaining sections with `Edit`**;
do not `Write` over the file. Source content from `synthesis.md` and the team files.

Requirements:
- Fill ALL sections with actual content (no placeholders)
- Preserve what rows 4/5/7 already wrote
- Verify with Read tool after creation
- Verify all links are revision-pinned (not trunk URLs)
- Ensure the Design Intention section is present and filled, including both the
  root-cause-relation sentence and the **broken invariant** line

Mark row 17 `completed`.

**Upstream report** (required for Branch A and Branch C with library-side fix):

If `Diagnose.9` produced a Branch A (library bug) or Branch C (split scope with
library-side component), the upstream report should already have been generated
in step A3 or C3. Verify it exists at `<run-dir>/<library>/bug-<id>-upstream-<library>.md`.

If not yet created, generate it now using `references/upstream-report-template.md`.
The upstream report must:
- Contain NO Firefox/browser/Bugzilla references
- Contain NO security exploitation details or sec-* ratings
- Use ONLY upstream permanent links
- Be self-contained and suitable for filing with the library's issue tracker

### `Diagnose.16`: Structural self-check

Mark plan.md row 17.5 `in-progress`. Before launching the review team, the main
agent does a quick **structural** self-check (not the full audit — that is the review team's job):

- [ ] Every analysis-doc section is filled with real content (no placeholders).
- [ ] The Design Intention section states how the root cause relates to the
  original design (violation / gap / drift). Without it, Reframe has nothing to
  design against.
- [ ] The **broken invariant** line is filled. This is the single most important
  hand-off into the Reframe phase.
- [ ] The Hypothesis Tree reflects the final ranking from Synthesis.

If a check fails, fix it before launching the review team. Record the checklist
result in plan.md Notes and mark row 17.5 `completed`.

---

## Phase: Diagnosis Review (REVIEW #1)

The deep audit is done by an **independent review team**, not by the main agent
grading its own work. Set plan.md rows 18/19/20 `in-progress` and launch the three
reviewers **in one message** (full contracts in `references/agent-teams.md`). Each
writes a dedicated file under `<run-dir>/review/`:

- **Reviewer L (links / citations)** → `review/L.md`. Opens every code link in the
  analysis doc via `Read`; confirms the cited file:line still says what the doc
  claims; replaces any trunk URL with a `$SHERLOCK_REV` link.
- **Reviewer T (test re-runner)** → `review/T.md`. Re-reads
  `firefox/debug/bug-<id>-test-run.log` and confirms the proof test FAILs on the
  bug, not on a test-setup error. To re-verify the patches, use
  `git range-diff "$SHERLOCK_BASE..sherlock/bug-<id>"` against the exported patches,
  or apply them onto a detached `$SHERLOCK_BASE` in a scratch worktree — **never**
  `git am` them onto the working branch, which already contains those commits and
  would fail with "patch does not apply", producing a false negative and a spurious
  loop back to `Diagnose.13`.
- **Reviewer R (red-pen on root cause)** → `review/R.md`. Invokes red-pen with an
  **explicit output path** so this review cannot collide with the `Decide.5` one:
  ```
  Skill(red-pen, "<run-dir>/bug-<id>-analysis.md <run-dir>/review/bug-<id>-rootcause-review.md")
  ```
  It challenges the root cause, the hypothesis-tree ranking, and the assumption
  labels, then writes its own verdict + a pointer to the full review into
  `review/R.md`.

> **Why the explicit path.** red-pen derives its output from the analysis doc
> basename, so `bug-<id>-analysis.md` resolves to `bug-<id>-review.md` — the file
> `Decide.5` uses for the *solutions* review. Left implicit, whichever review ran
> second would be pushed to `bug-<id>-review-1.md`, and `Decide.6` would then read
> the root-cause review instead of the solutions review it is responding to.
> Passing an explicit `…-review.md` path keeps the two apart.
>
> Reviewer R judges the **root cause**. The `Decide.5` red-pen judges the
> **solutions**. Different targets — both fire, and both are required.

As each reviewer returns, verify its file exists and mark its row `completed`.
Handle failures by looping back (offending row → `in-progress`, artifact
rewritten); do not argue with the reviewer (Gotcha #13):

- Reviewer L fail → `Diagnose.15` (re-edit doc + relink).
- Reviewer T fail → `Diagnose.13`/`Diagnose.14` (fix/re-run the test) or
  `Diagnose.12` (correct the verdict).
- Reviewer R `revise` → `Diagnose.15`. `redesign` → escalate to the user.
  `reject` / `needs-more-info` → back to Wave 2 (gather more evidence).

**Record the response, not just the verdict.** Reviewer L reports "pass/fail **plus
fix-up diffs**" — a *pass with fix-ups* is easy to drop on the floor, because the
loop-back rules only fire on fail. Before the gate, fill the analysis doc's
`## Review #1 Response` section: the three verdicts, and for each concern whether it
was accepted (and what changed) or rejected (and why). Gotcha #13 allows fixing,
escalating, or looping back — but not ignoring, and the record is what makes the
difference visible at Consolidate.

Only when all three reviewers pass (or their concerns are resolved and recorded)
proceed to the gate.

---

## Gate: Root cause agreed

Mark plan.md row 21 `blocked-on-user`. Present a summary of the diagnosis to the
user:
- Root cause (1-2 sentences)
- The broken invariant (1 sentence)
- Key evidence (code path trace highlights)
- Test results
- Reviewer verdicts
- Path to the analysis doc

Ask: **"Does this root cause analysis look correct? Say 'yes' to move on to
solution design, or tell me what needs more investigation."**

**This is a hard gate:**
- If user disagrees → loop back to the relevant Diagnose step, update the analysis doc
- If user wants changes → make the changes, re-present
- Do NOT proceed to Reframe without explicit user agreement

On agreement, mark row 21 `completed`.

---

## Phase: Reframe

Read `references/first-principles.md` before starting — it defines the five
questions, the invariant discipline, and the widening discipline this phase runs on.

**This phase does not produce patches.** It produces what must be *true*. If you
find yourself writing a diff, stop and write the invariant the diff would
establish instead. Concrete approaches are the Design phase's job, and keeping
them separate is what stops the run collapsing into the first plausible fix.

**Cost is not an argument here.** Architecture revamps are on the table. Reviewer
pushback, patch size, and landing risk are all Decide-phase concerns. A design
space that has already been pre-filtered by practicality makes the Decide phase
a formality.

### `Reframe.1`: Frame the problem (main agent, not delegated)

Mark plan.md row 22 `in-progress`. Read the analysis doc, `teams/synthesis.md`,
and `teams/team-d-design-archaeology.md`. Answer, in writing:

- **Why is this a problem?** Which guarantee is broken — stated as a proposition,
  not as a description of the failure. For whom: end user, web content, the spec,
  a named internal caller, a security boundary, a future maintainer. What the
  concrete harm is, and its class. And honestly: would anyone notice if it were
  never fixed?
- **Why do we have this problem in the first place?** Which decision, constraint,
  absence, or drift permitted it. Classify the origin (missing contract / contract
  drift / layering violation / representable illegal state / duplicated path /
  lapsed purpose / defensive accretion) and name the specific commit, bug, or
  absence. "Technical debt" is not an answer.

Team P (next step) supplies the evidence trail; the framing itself is yours.

**Persist the answers before marking the row done.** Create
`<run-dir>/bug-<id>-principles.md` from `references/principles-template.md` now,
with the header and the Q1/Q2 sections filled and the rest left as template
placeholders. `Reframe.3` then *edits* this file rather than creating it.

Without this the answers live only in the transcript while Wave 3 runs — four
concurrent long-running agents, and a likely place to be interrupted. Resume trusts
`completed` rows and would read an artifact that does not exist, silently losing the
harm class that `Decide.1` derives its weights from. Mark row 22 `completed` once
the file is on disk.

### `Reframe.2`: Wave 3 teams (P, E, I, W)

Launch all four **in one message** (rows 23–26 `in-progress` before launching).
Full contracts in `references/agent-teams.md`. All are read-only and none may
propose a patch.

- **Team P — problem framing** (row 23) → `teams/team-p-problem-framing.md`.
  Evidence for `Reframe.1`: the broken guarantee as a proposition, who depends on
  it, the origin decision, what changed since.
- **Team E — elimination scan** (row 24) → `teams/team-e-elimination.md`.
  Answers "does this code still deserve to exist?" — reachability, supersession,
  whether the premise still holds, whether it is a workaround for an
  already-fixed upstream bug. Also produces the **call-site census**, which the
  Design and Decide phases both reuse. Every "no callers" claim cites its search.
- **Team I — invariant discovery** (row 25) → `teams/team-i-invariants.md`.
  Per symbol on the failing path, the invariants that would make the bug
  impossible rather than handled. Each needs subject, statement, enforcement
  point, and verification method — anything missing one goes on a "Demoted" list.
- **Team W — widening & unification** (row 26) → `teams/team-w-widening.md`.
  Where a narrow guard could be *extended* rather than reject, given a reliable
  result and predictable downstream handling; which guards collapse, which paths
  unify, and where widening would wrongly move validation off a security boundary.

Mark each row `completed` as its file lands.

### `Reframe.3`: Write the principles doc

Mark plan.md row 27 `in-progress`. Read all four team files (the files, not the
transcripts) and complete `<run-dir>/bug-<id>-principles.md` — the file
`Reframe.1` already created, with Q1/Q2 filled. **Edit it; do not Write over it**,
or the framing answers are lost. Fill the remaining sections:

1. The `Reframe.1` answers, now backed by Team P's evidence.
2. Elimination candidates with evidence, confidence, and blast radius, plus the
   call-site census table.
3. The **invariant table** — IDs I1, I2, … with subject, statement, enforcement
   point, verification method, current violation site, fixes/prevents/avoids, and
   strength. Demoted candidates listed separately with what they lack.
4. Widening opportunities, each with its (a) reliable-result and (b)
   downstream-handling justification, or dropped.
5. A **"designed today"** sketch — architecture-level, migration cost ignored,
   explicitly labelled a sketch. Its job is to establish direction so the eventual
   fix is a step toward the right model rather than away from it.
6. **2–5 named design principles.** Each gets a name, statement, what it buys
   (which failure classes it closes beyond this bug), what it costs (honestly —
   an unstated cost reads as a hidden one), and which invariant IDs and
   elimination candidates it implies.

Naming the principles is main-agent work. The teams supply candidates and
evidence; the synthesis into named strategies is yours.

Mark row 27 `completed`.

### Gate: Principles agreed

Mark plan.md row 28 `blocked-on-user`. Present, concisely:
- The two framing answers (why it's a problem; why it exists)
- The elimination candidates, if any, with confidence
- The invariant table, condensed to ID + statement + strength
- The named principles with what each buys and costs

Ask the user to mark each principle **adopted / rejected / deferred**, and record
the decision in the principle's Status field. **Multiple principles may be adopted
at once** — they are not competing options; they are the criteria the Design phase
will build against.

**If the user adopts nothing**, that is a legitimate outcome, not a stall: record
why in Notes, mark row 29 `skipped`, and run Design on Fleet F alone plus one Fleet G
agent seeded with whichever *deferred* principle sits closest to the user's stated
objection. If the objection is to the framing itself rather than to the principles,
set row 27 `in-progress` and re-derive instead.

Follow the gate contract for disagreement. On agreement, mark row 28 `completed`.

---

## Phase: Design

### `Design.1`: Two independent fleets

Launch both fleets **in one message** (rows 29 and 30 `in-progress`). Append one
row 29.x per adopted principle first — see `references/plan-template.md`
"Dynamic rows".

- **Fleet G (guided)** — **one agent per adopted principle**, not N identical
  agents. Diversity comes from the assigned lens, not from repetition. Each gets
  the analysis doc, the principles doc, the call-site census, and its assigned
  principle ID, and returns 1–3 concrete approaches realising *that* principle.
  → `teams/design-g-<principle-slug>.md`
- **Fleet F (free-mind)** — 2–3 agents given **only** a stripped copy of the
  analysis doc (see below). Diversify by lens: *smallest change that could possibly
  work*, *how would you build this today*, *what would another engine or the
  upstream project do*. → `teams/design-f<N>-freemind.md`

**Fleet F's isolation is a hard rule (Gotcha #14)**, and honour-system isolation is
not enough. The analysis doc contains a **Solution Track** table that links to
`bug-<id>-principles.md` *and* one-line-summarises its contents — enough to anchor
an agent that never opens the file. So before launching Fleet F, write a stripped
copy with the Solution Track and Agreed Approach sections removed:

```bash
# teams/analysis-for-fleet-f.md = the analysis doc up to (not including)
# the "## Solution Track" heading
```

Point Fleet F at that copy, and *also* name the forbidden paths in its prompt —
`bug-<id>-principles.md`, `teams/team-{p,e,i,w}-*.md`, `teams/design-g-*.md` —
belt and braces. Never paste Reframe content into a Fleet F prompt.

Fleet F exists to catch approaches the principles framing quietly excluded; an
anchored Fleet F is worse than no Fleet F, because it looks like independent
corroboration and is not.

Mark rows `completed` as files land.

### `Design.2`: Categorise, merge, sequence (main agent, not delegated)

Mark plan.md row 31 `in-progress`. This is the phase's real thinking, and it is
not delegable — it requires judging proposals against each other.

1. **Normalise.** Give every proposal an ID, a one-line summary, and the strategy
   it follows. Record its provenance (which fleet, which principle or lens).
2. **Cluster by philosophy.** Group proposals that share a principle, strategy, or
   underlying bet. The clue is: would the same reasoning produce both?
3. **Merge.** Where two proposals are complementary rather than competing —
   different layers, different invariants, different failure modes — fuse them
   into one composite option. Record what it was merged from.
4. **Sequence.** Where one proposal is the natural next step of another, put both
   on a **roadmap** `M1 … MN`. Mark the milestone **K** that fixes *this* bug;
   milestones `[K+1..N]` become follow-up bug candidates and are carried into
   `bug-<id>-followups.md`.
5. **Record the relation graph.** Categorisation is **not mutually exclusive**: A
   may merge with B, and the merged AB may sit at milestone 2 of a roadmap that
   also holds C and D. Two options may also outright conflict. Write the relations
   down rather than flattening them into a list.
6. **Note the convergence.** Where Fleet G and Fleet F independently arrived at
   the same approach, say so — that is strong evidence. Where they diverge is
   usually where the interesting options are.

**Write the result to disk before moving on.** Create
`<run-dir>/bug-<id>-solutions.md` from `references/solution-template.md` now, with
everything above filled in — every option (Summary, Core ideas, **Design principle**
and why that philosophy fits, Invariants established with mechanism, Implementation
overview, Roadmap position, Merged-from, Provenance), the Roadmaps, the Relation
graph, the Convergence note, and Change log entry `r1`. Leave **only** the
Comparison section empty; `Design.3` fills it.

Writing here rather than at `Design.4` matters for two reasons: the merge and
roadmap decisions are the most expensive thinking in the phase and would otherwise
exist only in the transcript, and Team M needs this file as its input. Mark row 31
`completed`.

### `Design.3`: Comparison matrix (Team M)

Mark plan.md row 32 `in-progress`. Launch **Team M** over the solutions doc
`Design.2` just wrote. It builds the matrix; it does not invent options and does not
rank them — ranking is the Decide phase's job and must be reached independently.

Blast radius comes from the census, not from estimation. "Invariants covered"
cites invariant IDs; an option covering none gets an explicit "none" rather than a
blank. For a third-party bug the matrix also carries a **layer** column (upstream /
local Firefox patch / both), since A4 and C4 make that a real axis of choice.
→ `teams/team-m-comparison.md`. Mark row 32 `completed`.

### `Design.4`: Finalise the solutions doc

Mark plan.md row 33 `in-progress`. Splice Team M's matrix into the solutions doc's
Comparison section at the top, and re-read the whole document for coherence now
that the options sit side by side — merges that looked clean in isolation often
read as duplicates in a table.

Also create `<run-dir>/bug-<id>-followups.md` here from
`references/followups-template.md`, seeded with every roadmap milestone after the
fix milestone **K**, each marked "candidate — not yet filed".
Creating it now rather than in Implement means a run that stops at the Decide gate
(the user takes the docs and implements it themselves — a normal outcome) still
hands over the follow-up list.

Mark row 33 `completed`.

### Gate: Option set agreed

Mark plan.md row 34 `blocked-on-user`. Present the comparison matrix, the roadmaps,
and a one-line summary per option, with the path to the doc. Note explicitly where
the two fleets converged.

Ask whether the option set is complete and correctly categorised, or whether
something is missing. Do **not** present a recommendation here — that is the next
phase, and mixing them undoes the generate/judge separation.

On agreement, mark row 34 `completed`.

---

## Phase: Decide

Persona shift: first-principles thinker → **practical evaluator**. Everything
Reframe and Design deliberately ignored — patch size, landing risk, schedule,
reviewer burden, uplift constraints — enters here, and only here.

### `Decide.1`: Fix the criteria before reading the options

Mark plan.md row 35 `in-progress`. Write the weighted criteria into
`<run-dir>/bug-<id>-evaluation.md` (from `references/evaluation-template.md`)
**before** re-reading the option set. Fixing the weights up front is what stops
the evaluation quietly rationalising a favourite.

Derive the weights from the bug's own facts:
- **Uplift pressure** — the sec rating and the per-branch status flags Team B
  captured. Record which branches are affected and whether an uplift is likely.
- **Blast radius / regression risk** — from the call-site census.
- **Invariant coverage** — does the option make the bug unrepresentable, or patch
  this one instance?
- **Test verifiability** — would the existing proof test flip FAIL→PASS?
- **Effort / schedule.**
- **Architectural debt paid down.**

If a criterion is added or reweighted later, log it in the evaluation doc's
Decision log with the reason. Mark row 35 `completed`.

### `Decide.2`: Re-evaluate the problem

Mark plan.md row 36 `in-progress`. Re-read the analysis, principles, and solutions
docs. Confirm nothing surfaced in Reframe or Design invalidated the root cause —
Team E's census and Team W's widening analysis both routinely turn up facts that
were not visible during Diagnose. If the root cause has moved, say so and loop
back rather than ranking options against a stale diagnosis.

### `Decide.3`: Score and recommend

Score each option against the fixed criteria and write the evaluation doc's
scoring table, then a **prioritised preference order**: first choice, second
choice, and the fallback with the conditions that would trigger it.

Scores are a thinking aid, not an oracle. Where the recommendation departs from
the highest weighted total, say so and explain why — that disagreement is usually
the most informative line in the document.

**Uplift rule.** When a security bug is likely to be uplifted to shipped or ESR
branches, **the simplest sufficient fix wins**, and the optimisation or cleanup
becomes a named follow-up on the roadmap. A minimal, obviously-correct,
low-blast-radius patch is what a branch reviewer can actually approve; the elegant
version lands on trunk afterwards. Write this reasoning out in the doc rather than
treating it as self-evident — and say so explicitly when it does *not* apply.

Also fill: deferred-to-follow-up (with roadmap milestone references), risks
accepted, and open questions for the user. Mark row 36 `completed`.

### `Decide.4`: User check, before red-pen

Mark plan.md row 37 `blocked-on-user`. Present the criteria, the scoring, and the
prioritised recommendation. Discuss. The user may reweight, disagree with a score,
or redirect entirely — all of which are cheaper to handle now than after a review
run. On agreement, mark row 37 `completed`.

### `Decide.5`: Red-pen on the solutions (REVIEW #2)

Mark plan.md row 38 `in-progress`. Sherlock does not present its own judgement as
the final word. Invoke:

```
Skill(
  skill: "red-pen",
  args: "<abs path to bug-<id>-analysis.md> <abs path to bug-<id>-solutions.md>"
)
```

The skill spawns an isolated `red-pen-critic` with no shared memory, verifies
citations against source, and writes a structured review to
`<run-dir>/bug-<id>-review.md`, returning a 4-line summary (verdict, headline,
path, iteration).

> **The evaluation doc is deliberately NOT passed to the reviewer.** red-pen's
> hard rule is that no conclusions reach the critic, and withholding our ranking
> means the reviewer reaches its own ordering independently — which is the entire
> value of a second opinion. Where the two orderings agree, that is corroboration;
> where they differ, that is the discussion. (It is also a mechanical constraint:
> red-pen accepts at most one analysis source and one solutions source.)

Do **not** invoke the reviewer multiple times in parallel; one review per draft
set. Mark row 38 `completed`.

### `Decide.6`: Consider the review and discuss

Mark plan.md row 39 `in-progress`. Read `<run-dir>/bug-<id>-review.md` and record a
**Review Response** section in the evaluation doc: the verdict, the iteration
recommendation, and each concern with accepted/rejected and reasoning. Note
explicitly whether the reviewer's ordering matched ours.

Handle by verdict:

| Verdict | Action |
|---------|--------|
| `approve` | Proceed to the gate. |
| `approve-with-concerns` | Apply the cited concerns. If changes are non-trivial, re-invoke red-pen. Otherwise proceed. |
| `revise <option>` | Apply the cited changes to that option. If the diff is non-trivial, re-invoke red-pen. |
| `redesign` | **Stop. Do not silently expand scope.** The reviewer has proposed a structurally different fix. Surface it explicitly with its latent-issue list and scope estimate, and ask whether to (a) loop back to Reframe and add a principle, (b) loop back to Design and append the redesign as a new option, (c) take a smaller fix now and put the redesign on the roadmap as a follow-up. Do not proceed until the user picks. |
| `reject` | Loop back to `Diagnose.7` (row 8.5) with the reviewer's open questions. The root cause likely needs more work. |
| `needs-more-info` | Answer the open questions (may need more Diagnose work or a user clarification), then re-invoke. |

Also use red-pen's **Iteration** line (`accept` / `revise N` /
`adopt-alternative` / `pursue-redesign` / `escalate`) — it maps directly onto this
loop and is often more specific than the verdict alone.

**Loop protocol — append, never rewrite (Gotcha #17):**
- Back to **Design** → append a new option to the solutions doc, bump its revision
  counter, log the reason in its Change log and in plan.md Notes. Rows 31–33 go
  `in-progress`, gate row 34 returns to `pending`.
- Back to **Reframe** → append a new principle; row 27 `in-progress`, gate row 28
  `pending`.
- Each red-pen re-run is a separate run: the review doc gets a `-N` suffix, both
  stay on disk, and a row 38.x is appended.

Expect back-and-forth here — push-back, re-investigation, redirection. That is the
phase working, not the phase failing. Present the review and your response
together, comprehensively, and let the user drive. Mark row 39 `completed` when
the discussion concludes.

### Gate: Implementation approved

Mark plan.md row 40 `blocked-on-user`. Present the final choice, the reasoning,
what is being deferred to follow-ups, and the reviewer's verdict verbatim. Get
explicit approval for the implementation choice before writing any code.

On approval, mark row 40 `completed`.

---

## Phase: Implement

### `Implement.1`: Discover implementation skills

Mark plan.md row 41 `in-progress`. **Before writing any code**, discover what
implementation tooling the destination repo offers and let the user pick. Follow
`references/impl-skill-discovery.md` — it has the enumeration commands, the
capability rubric, the degradation rules, and the worktree reconciliation.

In short: enumerate `<repo-root>/.claude/skills/*/SKILL.md` with `find -L` (a
plain glob silently misses symlinked skills), read each frontmatter, bucket by
capability (`implements` / `shapes` / `checks` / `files` / `routes`), and present
the candidates via `AskUserQuestion` with "implement directly" always offered.

**Never hard-code a list of skill names.** The destination tree's skill set
changes; the classifier must work on descriptions it has never seen.

Record the detected set, the timestamp, and the user's pick per bucket in plan.md
Notes, then mark row 41 `completed`.

### `Implement.2`: Implement

Mark plan.md row 42 `in-progress`. Implement the approved option on
`sherlock/bug-<id>` — or, if the chosen skill requires its own worktree, on a
worktree branched **from `sherlock/bug-<id>`** so the proof-test commits carry
over (see `references/impl-skill-discovery.md`).

If a skill was selected, `Skill(<name>)` first and implement under its guidance,
passing the absolute paths of the analysis and solutions docs in the prompt text.
Most in-tree skills are behavioural overlays rather than executors — read what
comes back before assuming otherwise.

### `Implement.2b`: Library-side work (Branch A or C only)

Skip this step unless `Diagnose.9` recorded **Branch A** or **Branch C** in plan.md
Notes. `Diagnose.9` deferred three things to this phase — A4, C4, and the upstream
submission — and they are easy to lose, because everything else in Implement is
Firefox-only.

Read the scope verdict, the library name, the **local library repo path**, and the
vendored revision from plan.md Notes (recorded at T1). Then, in the library repo:

1. Copy the T3 test patch into `fix/` if it needs no code injection (A4/C4).
2. Create the fix branch on the test branch and implement:
   ```bash
   git checkout sherlock/bug-<id>/test
   git checkout -b sherlock/bug-<id>/fix
   # ... implement ...
   git commit --author="$SHERLOCK_AUTHOR" -m "Fix <desc>"
   git format-patch -1 --stdout > <run-dir>/<library>/fix/02-fix-<desc>.patch
   ```
3. Build and run the T3 test on the fix branch — confirm it now passes.
4. Apply the fix to the vendored copy (`media/{lib}/` or `third_party/{lib}/`),
   `./mach build`, and confirm the A2/C2 Firefox test now passes. This is the step
   that proves the vendored fix actually resolves the Firefox-side bug.
5. Update the upstream report's suggested-fix section with the verified fix.
6. Mark the appended `Implement`-phase branch rows (A4 / B2 / C4) `completed`.

**Landing order** (from C4): the Firefox-side fix can land immediately; the library
fix goes upstream first and gets vendored later. Record which is *necessary* and
which is *defensive* in the analysis doc.

**Upstream submission is a mandatory follow-up**, not part of this run — add it to
`bug-<id>-followups.md` in `Implement.6`. For a security bug, see the reproducer
rule in A3 before filing anything upstream.

### `Implement.3`: Commit shape

The final patch series has one of two shapes, and which one is not a style choice:

**Non-security → `[tests] → [fixes]`.** The proof tests are already the first
commits on the branch, so fix commits go on top. Nothing to reorder. A reviewer
can check out the test commit, watch it fail, apply the fix commit, and watch it
pass.

```bash
git checkout sherlock/bug-<id>
git add <fix files>
git commit --author="$SHERLOCK_AUTHOR" -m "<what the fix does>"
git format-patch -1 --stdout > <run-dir>/firefox/fix/02-fix-<desc>.patch
```

**Security → `[fixes] → [tests]`.** The test lands separately and *later* than the
fix, so the fix must come first in the series — a test that demonstrates the
vulnerability must not be public before the fix ships. Because Diagnose committed
the proof tests first, this **requires reordering the branch**.

Prefer a `shapes`-bucket skill if one was discovered — mozilla-central currently
ships a jj-based patch-reorganisation skill, which is the right tool. Otherwise
reorder manually.

**First, consolidate onto the working branch.** If `Implement.2` used a worktree,
the fix commits are on *its* branch, not on `sherlock/bug-<id>`, and every command
below would operate on a branch with no fixes. Cherry-pick them over and drop the
worktree before reordering:

```bash
git worktree list                                  # find it
git checkout sherlock/bug-<id>                     # fails if the worktree holds this branch
git cherry-pick "$SHERLOCK_BASE..<worktree-branch>"
git worktree remove <worktree-path>
```

**Then reorder.** This sequence never loses a commit, needs no interactive rebase,
and avoids zsh word-splitting (which silently breaks a bare `$HASHES` list — see
the repo's own shell notes):

```bash
SHERLOCK_BASE=<base sha recorded in plan.md at Diagnose.6>

# 0. Snapshot first. Everything below rewrites history.
git branch sherlock/bug-<id>-preorder sherlock/bug-<id>

# 1. Find the boundary on the snapshot, not on the branch you are about to rewrite.
git log --oneline "$SHERLOCK_BASE..sherlock/bug-<id>-preorder"
LAST_TEST=<sha of the last test commit>

# 2. Rebuild in [fixes..., tests...] order. Range form — no hash lists.
git checkout -B sherlock/bug-<id> "$SHERLOCK_BASE"
git cherry-pick "$LAST_TEST..sherlock/bug-<id>-preorder"   # the fixes, in order
git cherry-pick "$SHERLOCK_BASE..$LAST_TEST"               # then the tests, in order

# 3. Confirm the order.
git log --oneline "$SHERLOCK_BASE..sherlock/bug-<id>"

# 4. Re-export. The stale patches from Diagnose.14 MUST be cleared first —
#    format-patch writes 0001-*.patch and would otherwise sit alongside 01-*.patch
#    with an ambiguous apply order.
rm -f <run-dir>/firefox/fix/*.patch
git format-patch "$SHERLOCK_BASE..sherlock/bug-<id>" -o <run-dir>/firefox/fix/
```

On conflict — likely, since tests and fixes often touch the same manifest — resolve
and `git cherry-pick --continue`. To abandon:
`git cherry-pick --abort && git checkout -B sherlock/bug-<id> sherlock/bug-<id>-preorder`.

Rename the exported patches to the landing order: `01-fix-<desc>.patch`,
`02-test-<desc>.patch`. Keep the `-preorder` snapshot until Consolidate.

After any reorder, **rebuild** — a replay can produce a series that does not compile
at an intermediate commit, and each commit is supposed to stand on its own. Note the
fix-only commit cannot be *test*-verified (the test does not exist yet at that
point), so intermediate verification there is compile-only; the full FAIL→PASS check
happens at `Implement.4` on the branch tip.

Note that a chosen implementation skill may have its own patch-split rules. Those
typically agree with this one on *separation* (tests separate from the fix for
security bugs) while saying nothing about *ordering*. The ordering requirement
above still applies.

Mark row 42 `completed` once the patches are exported.

### `Implement.4`: Verify

Mark plan.md row 43 `in-progress`. The proof test must go **FAIL → PASS**:

```bash
./mach build
./mach test <path> --headless 2>&1 | tee <run-dir>/firefox/fix/bug-<id>-verify-run.log
```

If it does not flip, the root cause or the fix is wrong. Loop back — to
`Decide.6` if the option was unsuitable, to `Diagnose.7` (row 8.5) if the diagnosis was.
Do not adjust the test until it passes; that destroys the only evidence the run
has.

Run any `checks`-bucket skill the user selected (lint, format, build gates) before
declaring this done. Mark row 43 `completed`.

### `Implement.5`: Improve or revert

Implementation surfaces things the documents did not anticipate, and the user may
change their mind. Both are normal; both must leave a record.

- **Improve** — amend the implementation and add a Change log entry to the
  solutions doc saying what changed and why.
- **Revert** — revert the commits, then record in the solutions-doc Change log
  **what was wrong, what was missing, and what changed**. That entry is the reason
  the doc exists; a bare "reverted" is useless to the next reader. Then reopen the
  evaluation doc, take the next-preferred option from the recommendation order,
  discuss it with the user, seek agreement, re-run red-pen, and re-implement.
  Set rows 39/40/42/43 back to `pending`.

Never delete the record of a rejected or reverted approach. The run's history is
part of its output.

### `Implement.6`: Blocking and follow-up triage

Mark plan.md row 44 `in-progress`. Problems found during implementation fall into
two kinds, and conflating them is how a bug fix quietly becomes a three-week
project:

- **Blocking** — must be fixed *before* this bug can land. Record it in plan.md
  Notes **and** in the analysis doc's *Related Context*, append a row 44.x, and
  tell the user the current work may need to be postponed. This is a scheduling
  decision, so surface it immediately rather than at the end.
- **Follow-up** — can land after this fix. Append it to
  `<run-dir>/bug-<id>-followups.md` with what it is, why it was deferred, and its
  roadmap milestone if it came from one. Do not interrupt the user for these;
  they are reported together in Consolidate.

Also seed the follow-up file from the Design phase: every roadmap milestone after
the fix milestone **K** is a follow-up candidate. Mark row 44 `completed`.

---

## Phase: Consolidate

The run has accumulated knowledge that none of the documents individually
reflect — the discussion, the review, the implementation surprises. This phase
reconciles them so the run is useful to someone reading it in six months.

1. **Re-read every document**: `plan.md`, the analysis, principles, solutions,
   evaluation, and followups docs, every review file, and — for a Branch A or C
   run — the upstream report `<library>/bug-<id>-upstream-<library>.md`.
2. **Fold in what was learned after each was written.** Specifically:
   - Does the analysis doc's root cause statement still hold post-implementation?
     If implementation revealed it was incomplete, correct it and say so.
   - Is the solutions-doc Change log complete — every revision, every reversal,
     every redirection?
   - Does the evaluation doc's final choice match what was actually implemented?
     If not, the Decision log must explain the divergence.
   - Does the analysis doc's *Agreed Approach* name what shipped?
   - Does the analysis doc's *Test Evidence* table carry the final **PASS** result
     and a link to `firefox/fix/bug-<id>-verify-run.log`? It still says FAIL from
     Diagnose otherwise.
3. **Confirm the reviewers were actually answered.** For every file in `review/`,
   each fail *and each fix-up* must map to a change in the target artifact or to an
   explicitly recorded rejection in the analysis doc's Review #1 Response. Same for
   the Decide red-pen against the evaluation doc's Review Response. An unanswered
   reviewer concern is the most expensive thing to discover later.
4. **Check formatting and consistency.** No placeholders left. Every link
   revision-pinned — no trunk URLs. Nothing security-sensitive outside the run dir.
   Relative links between the docs all resolve. For a Branch A or C run, **re-run
   the A3 sanitisation check** on the upstream report — no Firefox or Gecko
   references, no Bugzilla links, no sec ratings, and for a security bug no
   reproducer. That check currently only happens at authoring time, and the report
   has usually been edited since.
5. **Verify every follow-up is closed out.** Each entry in
   `bug-<id>-followups.md` must either have a real bug id or be explicitly handed
   to the user. Nothing stays "TODO". For a Branch A or C run, the **upstream
   submission is one of those entries**. Offer a `files`-bucket skill from
   `Implement.1` if one was discovered. `sherlock-config` cannot create bugs, so
   Sherlock must never claim it filed one (Gotcha #18).
6. **Report the refs left behind; delete only what is safely disposable.** The
   branches and worktrees are this run's evidence, so they are kept — but the user
   should not have to discover them months later:
   ```bash
   git branch --list 'sherlock/bug-<id>*'      # Firefox tree
   git worktree list
   # for a third-party run, the same in the local library repo
   ```
   Print what exists plus the one-line command to remove it, and let the user decide.
   The only ref deleted automatically is the `sherlock/bug-<id>-preorder` snapshot
   from `Implement.3`, once the reordered series has been verified.
7. **Close the run out.** Set the `Run status` line in `plan.md`:
   - **FINISHED** when every row is `completed` or `skipped`.
   - **POSTPONED** when a `blocked-external` row remains. A run waiting on a blocking
     bug is not finished, and marking that blocker `skipped` to force a FINISHED
     would put a falsehood in the one document the next session trusts.

   Either way, do not close out over a row still `pending` or `in-progress`: resolve
   it, or mark it `skipped` with a reason in Notes.
8. **Final report** to the user, in ≤8 lines: what shipped, the commit shape, the
   follow-up list with filing status, any blocking issues still outstanding, the refs
   left behind, and the path to the run dir.

Mark rows 45 and 46 `completed`.

---

## Tips

- For security bugs, include a **## Security Rating** section in the analysis doc
- Private bugs: log ONLY `bug_id` to history — no titles, components, or details
- Suggested fixes in bug comments are **REFERENCES**, not solutions — analyze
  independently, and let them enter as one proposal among many in Design
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
- **Agent teams run in waves**: launch all Wave 1 teams (B, H) in one message,
  then all applicable Wave 2 teams (C, L, D, X, T) in one message, then the
  Diagnosis Review reviewers (L, T, R) in one message, then Wave 3 (P, E, I, W),
  then Wave 4 (Fleet G + Fleet F). Each team owns a file under `teams/` or
  `review/`; the main agent reads files, never transcripts. See
  `references/agent-teams.md`.
- **Read the review doc, don't restate it**: when surfacing a `red-pen` result to
  the user, link the review doc instead of paraphrasing — paraphrasing dilutes the
  reviewer's exact wording and defeats the point of the independent second opinion.
- **The docs are the deliverable as much as the patch.** A run that lands a fix
  but leaves the solutions doc's Change log empty has lost the reasoning that
  justified the fix.
