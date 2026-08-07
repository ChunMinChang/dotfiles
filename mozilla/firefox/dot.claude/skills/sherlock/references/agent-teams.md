# Agent teams

Sherlock launches research subagents in **one message containing multiple `Agent`
tool calls** so they run concurrently — that is the agent-teams primitive. No
harness flag exists or is needed.

Sherlock's workflow is gated, so teams launch in **four waves**:

- **Wave 1 — intake teams** run *before* any hypothesis exists (`Diagnose.1`).
  Teams: **B** (bug-context), **H** (hypothesis brainstorm).
- **Wave 2 — research teams** run *after* the primary hypothesis is chosen,
  targeting the chosen symbols/files (`Diagnose.8`). Teams: **C** (Firefox
  code-trace), **L** (library code-trace, when `Diagnose.9` applies), **D**
  (design archaeology), **X** (cross-browser/spec), **T** (test-framework
  scout + draft).
- **Wave 3 — Reframe teams** run after the root cause is agreed (`Reframe.2`).
  Teams: **P** (problem framing), **E** (elimination scan), **I** (invariant
  discovery), **W** (widening & unification).
- **Wave 4 — Design fleets** run after the principles are agreed (`Design.1`),
  plus **Team M** (comparison matrix) at `Design.3`. Fleets: **G** (guided, one
  agent per adopted principle), **F** (free-mind, isolated from Reframe).

Between the waves the main agent does the un-delegatable work (see "Main-agent
only" below). After Wave 2 the main agent runs **Synthesis**; after Wave 3 it
writes the principles doc; after Wave 4 it does the categorisation.

Each team has a tight I/O contract. Subagents never declare the root cause, the
verdict, the hypothesis ranking, or the chosen solution; the main agent
synthesises after all teams return.

## Output persistence

**Every team writes its full findings to a dedicated file** under
`<run_dir>/teams/` and returns only a short summary (≤10 lines) for synthesis.
The main agent reads the file when it needs the full results — never relies on the
subagent transcript. This makes the work survivable: if the session halts, the
next session resumes from the on-disk files.

| Wave | Team | Output file (under `<run_dir>/teams/`) |
|---|---|---|
| 1 | Team B | `team-b-bug-context.md` |
| 1 | Team H | `team-h-hypotheses.md` |
| 2 | Team C | `team-c-code-trace-firefox.md` |
| 2 | Team L | `team-l-code-trace-library.md` |
| 2 | Team D | `team-d-design-archaeology.md` |
| 2 | Team X | `team-x-cross-browser.md` |
| 2 | Team T | `team-t-frameworks.md` |
| — | Synthesis (main agent) | `synthesis.md` |
| 3 | Team P | `team-p-problem-framing.md` |
| 3 | Team E | `team-e-elimination.md` |
| 3 | Team I | `team-i-invariants.md` |
| 3 | Team W | `team-w-widening.md` |
| 4 | Fleet G | `design-g-<principle-slug>.md` (one per adopted principle) |
| 4 | Fleet F | `design-f<N>-freemind.md` (one per lens) |
| 4 | Team M | `team-m-comparison.md` |

Each prompt template below ends with an instruction to write to that file. Every
invocation passes inputs as **file paths and explicit values** (not "the bug we're
investigating") and includes the framing *"return the requested artifact only; do
not draw conclusions about the root cause."*

---

## Wave 1 — intake teams

Launch Team B and Team H in the **same message**. They are independent: B fetches
and digests bug data; H brainstorms candidate hypotheses from the raw bug
description the main agent passes inline.

### Team B — Bug-context digest

**Goal:** gather all bug context (main bug, duplicates, attachments, Treeherder,
branch status) into one digest so the main agent's context is not flooded, and so
`Diagnose.2` (duplicates), `Diagnose.3` (failure pattern), `Diagnose.13a`
(attachments) and `Decide.1` (uplift pressure) all read one file instead of
re-fetching.

**Prompt template:**
```
You are gathering raw context for a Firefox bug investigation (Team B). Return a
structured digest only — do NOT diagnose or speculate about root cause.

Inputs:
- Bug ID: <bug_id>
- Run directory: <run_dir>
- Repo root: <repo-root>
- Sherlock config helper: <repo-root>/.claude/skills/sherlock/sherlock-config

Tasks:
1. Run `<sherlock-config> --fetch-bug <bug_id> -o <run_dir>/bug-<bug_id>-report`
   for the main bug.
2. Parse duplicates from the bug report; for each, run the same fetch into
   `<run_dir>/bug-<dup_id>-report`.
3. Run `<sherlock-config> --fetch-attachments <bug_id> -o <run_dir>/bug-<bug_id>-attachments`.
4. Fetch the Treeherder failure-distribution endpoint for the last 7 days:
   `https://treeherder.mozilla.org/api/failuresbybug/?startday=YYYY-MM-DD&endday=YYYY-MM-DD&tree=all&bug=<bug_id>`
5. Extract the per-branch status flags from the fetched report: every
   `status-firefox<N>` / `cf_status_firefox<N>` and every
   `cf_status_firefox_esr<N>` field, plus `cf_tracking_firefox*` where present.

Output:

1. **Write to disk:** `<run_dir>/teams/team-b-bug-context.md` with sections:
   - **Identity**: title, component, severity, priority, status, public/private,
     sec-* keywords (if any), depends/blocks list.
   - **STR & expected vs actual**: condensed.
   - **Attachments**: one line each (filename, size, type, brief purpose).
   - **Duplicates**: for each, one paragraph of *new* information not in the
     main bug.
   - **Treeherder**: platforms, suites, build types, failure rate
     (consistent / intermittent + count), trees, date range. If no Treeherder
     hits, say so.
   - **Branch status**: a table of | Branch | Status | Tracking | for every
     status flag found (release, beta, nightly, each ESR). This feeds the later
     uplift judgement — report the flags verbatim, do NOT judge whether an
     uplift is likely.
   - **Pointers**: relative paths to the fetched artifact directories.

2. **Return** a short summary (≤10 lines): title, component, public/private,
   sec-* keywords, one-line failure pattern (consistent/intermittent + count),
   duplicate count, attachment count, affected-branch list.

Hard rules:
- Do NOT propose a root cause or speculate about which code is responsible.
- Do NOT include the full text of bug comments — distill to key facts.
- NEVER read, parse, or print any API key. All API access goes through the
  config helper. Do NOT use python3 to parse config files.
```

### Team H — Hypothesis brainstorm (advisory)

**Goal:** generate candidate root-cause hypotheses to *feed* the main agent's
hypothesis tree (`Diagnose.5`). **Advisory only** — the main agent independently
builds, ranks, and prunes the tree. This guards against the central RCA failure
mode (anchoring): the team supplies raw candidates, never the ranking.

**Prompt template:**
```
You are Team H in sherlock. Brainstorm candidate root-cause hypotheses. You are
ADVISORY: the main agent will independently build and rank the hypothesis tree.
Do NOT pick a primary hypothesis or declare a root cause.

Bug summary (from the reporter):
<paste condensed bug identity + STR + expected/actual + any stack traces>

Component: <component>
Failure pattern: <consistent | intermittent (rate)>

Generate AT LEAST 3 distinct candidate hypotheses. For each:
- Failure mechanism (how the bug would manifest internally if this were the cause)
- Confirming evidence (what we'd see in code/logs/test if true)
- Refuting evidence (what we'd see if false)
- Probe cost (read-only / build + gtest / build + mochitest / sanitizer build)

Output:

1. **Write to disk:** `<run_dir>/teams/team-h-hypotheses.md` as a Markdown table
     | # | Hypothesis | Failure mechanism | Confirming evidence | Refuting evidence | Probe cost |
   followed by one paragraph per hypothesis expanding the mechanism.

2. **Return** a short summary (≤10 lines): hypothesis count, the one-line
   mechanism of each, and any class of failure you considered and dropped (with
   reason).

Do NOT pick a primary hypothesis. Do NOT declare the root cause. Do NOT propose
fixes.
```

---

## Wave 2 — research teams

Launch every applicable team in the **same message**. Team L only when the bug
involves vendored third-party code (`Diagnose.9` active). Team D is **skipped**
when `Diagnose.9` is active (design intention is covered inside the branch
workflow A1/B1/C1) — set its plan.md row `skipped`. Team X is skipped for
internal-only bugs with no web surface.

All Wave 2 teams are **read-only** (searchfox / upstream tracing / git history /
spec reading / test authoring). None of them build. The expensive `./mach build`
cycle is the main agent's job and is serialized (see "Test builds serialize").

### Team C — Firefox code-trace

**Goal:** trace the Firefox call path for the primary hypothesis with
revision-pinned permalinks. Flag suspicious steps; do not diagnose.

**Prompt template:**
```
You are producing a Firefox code path trace (Team C). Return the trace only —
do NOT decide what the root cause is.

Inputs:
- Repo root: <repo-root>
- Searchfox revision: <$SHERLOCK_REV>
- Entry symbol(s) / file(s): <list>
- Hypothesis to trace: <one sentence — the failure mechanism the trace should
  illuminate>

Tasks:
1. Use `searchfox-cli` to find the call path. Follow the `source-permalinks` skill.
2. Read each function in the path (do not skim — read the body).
3. Produce a numbered trace, every step pinned to a revision-permalink, with a
   one-line evidence note per step (what happens, what it returns, what state it
   mutates).

Output:

1. **Write to disk:** `<run_dir>/teams/team-c-code-trace-firefox.md`:
   a numbered Markdown list. Each entry:
     N. [`Class::Method`](https://searchfox.org/firefox-main/rev/<sha>/<path>#L<n>) — one-line description
        - evidence sub-bullet (quote the relevant 1–2 lines)
   End with a "Notable observations" block flagging anything suspicious (swallowed
   error, missing nullcheck, unusual lifetime). Flag only — do not call it the
   root cause.

2. **Return** a short summary (≤10 lines): trace-step count, the 2–3 most
   striking observations, and any blocker.

Hard rules: revision-pinned URLs only, never trunk. Never invent line numbers.
Do NOT propose fixes. Do NOT declare the root cause.
```

### Team L — Library code-trace

**Goal:** same as Team C but for vendored third-party code, using upstream
permalinks. Only launched when `Diagnose.9` is active.

**Prompt template:** identical to Team C, with these substitutions:
```
You are producing a third-party library code path trace (Team L).

- Side: library: <name> @ <upstream_revision>
- To find the vendored revision: `git show HEAD:media/<lib>/moz.yaml | grep revision`
- Use upstream permalink construction (see references/upstream-libs.md), e.g.
  https://gitlab.xiph.org/xiph/vorbis/-/blob/<hash>/lib/sharedbook.c#L355

Write to: <run_dir>/teams/team-l-code-trace-library.md
```

### Team D — Design archaeology

**Goal:** recover the original design intention and the contract the author
believed they were establishing. Skipped when `Diagnose.9` is active.

The **function contract** this team extracts is the single most important input
to the Reframe phase — it is what the Reframe invariant work builds on. Extract
it precisely, even when it has to be inferred from the code rather than stated.

**Prompt template:**
```
You are doing git-history archaeology for a Firefox root-cause analysis (Team D).
Return a structured Design Intention block; do NOT propose root cause or fixes.

Inputs:
- Repo root: <repo-root>
- Files: <list of file paths>
- Key symbols: <list — functions / classes / fields / state values>
- Searchfox revision: <$SHERLOCK_REV>

Tasks:
1. Find the introducing commit for each key symbol:
   - `git log --oneline --follow -S "<symbol>" -- <file>` (head -10)
   - `git blame -L <line>,<line> <file>` for the candidate region
   - jj equivalents: `jj annotate <file>`,
     `jj log -r 'ancestors(trunk())' -T builtin_log_oneline -s -- <file>`
2. Read the introducing commit message in full. Follow the linked Bugzilla bug
   (use <repo-root>/.claude/skills/sherlock/sherlock-config --fetch-bug).
3. Read 2-3 commits before and after for context.
4. Summarise the function's contract from the code (preconditions,
   postconditions, invariants, threading, ownership). Where the contract is
   implicit, state it as inferred and cite the code that implies it.

Output:

1. **Write to disk:** `<run_dir>/teams/team-d-design-archaeology.md`:
   - Introducing commit (hash, summary, linked bug)
   - Original purpose (1 sentence)
   - Design rationale (cite commit message / bug discussion)
   - Constraints / tradeoffs
   - Function contract (preconditions, postconditions, invariants, threading,
     ownership) — mark each clause Stated or Inferred
   - Related code (other places using the same pattern)
   - Drift signals (followup commits, workaround comments, dead branches)

2. **Return** a short summary (≤10 lines): introducing-commit hash + bug,
   one-sentence original purpose, the single most important constraint, and any
   drift signal worth flagging.

Hard rules: cite commit hashes and bug numbers. Do NOT claim how this relates to
the current root cause — that is the main agent's job. Do NOT propose fixes.
```

### Team X — Cross-browser & spec check

**Goal:** establish what other engines do and what the spec says. Skipped for
internal-only bugs with no web surface.

**Prompt template:**
```
You are Team X in sherlock. Compare cross-engine behaviour and check the spec.
Follow references/spec-check.md. Return findings only — do NOT pick the verdict.

Inputs:
- Bug summary: <condensed identity + STR>
- Suspect symbol / web-exposed feature: <symbol/feature>
- Searchfox revision: <$SHERLOCK_REV>

Tasks:
1. Identify the relevant spec section. For a web-exposed feature, find the
   algorithm in the spec (WHATWG/W3C/IETF/ITU-T).
2. grep testing/web-platform/tests/ for existing coverage of the same surface.
3. If a public Chromium/WebKit source link is known, read it; otherwise rely on
   spec wording.

Output:

1. **Write to disk:** `<run_dir>/teams/team-x-cross-browser.md`:
   - Spec citation (URL + section, or "no spec — internal").
   - Behaviour table: | Engine | Behaviour | Source |
   - Existing WPT coverage (paths) or "none".
   - Notable spec/impl divergence (if any).

2. **Return** a short summary (≤10 lines): one-sentence spec status, the
   cross-engine behaviour delta in one line, and existing WPT coverage count.

Do NOT pick the verdict. Do NOT propose fixes.
```

### Team T — Test-framework scout + draft

**Goal:** for each live hypothesis, pick the right framework, find a neighbour
test that already exercises the suspect code path, and **draft the test source**.
Team T does NOT build or run — builds serialize (see below); the main agent builds.

**Prompt template:**
```
You are Team T in sherlock. Pick a test framework and draft a proof test per
hypothesis. Do NOT build or run anything. Do NOT pick the verdict.

Live hypotheses (from the main agent's hypothesis tree):
<paste the surviving hypotheses>

Suspect file(s): <path(s)>
Searchfox revision: <$SHERLOCK_REV>
Reference: references/test-frameworks.md (decision tree + FuzzingFunctions map).

For each hypothesis:
1. Choose ONE framework from:
     gtest | mochitest-plain | mochitest-chrome | browser-chrome | xpcshell
     | reftest | crashtest | wpt
2. Find a representative neighbour test in the tree (same dir or sibling) that
   exercises the suspect code path; the new test should follow its style.
3. Draft the proof-test source (the test must be designed to FAIL on the unfixed
   tree and PASS once fixed). The test must reproduce the failure end-to-end —
   no mocking the suspect function. If only code injection can trigger it, say so
   and explain why a benign reproducer is impossible.

Output:

1. **Write to disk:** `<run_dir>/teams/team-t-frameworks.md` as a table
     | # | Hypothesis | Framework | Neighbour test path | Reason |
   followed, per hypothesis, by a fenced code block with the drafted test source
   and the manifest line needed to register it.

2. **Return** a short summary (≤10 lines): framework distribution (e.g.
   "2 gtest, 1 crashtest"), and any hypothesis where the framework choice or a
   benign reproducer was uncertain.

Do NOT build. Do NOT run. Do NOT write into the Firefox source tree.
Do NOT pick the verdict.
```

---

## Third-party (`Diagnose.9`) coexistence with parallel teams

The third-party sub-workflow is inherently **sequential** and is NOT a team:

- **T1** (locate the upstream repo) needs interactive user input — `AskUserQuestion`.
- **T2** (scope hypothesis: library / integration / local-patch) is main-agent
  judgment.
- **T3** is a **mandatory diagnostic build** that reproduces the bug in the
  upstream library — a **GATE** whose result chooses Branch A / B / C.

Ordering when `Diagnose.9` is active:

1. Wave 2 launches the read-only traces **Team C + Team L** (and X, T) in
   parallel. Both are read-only, so they run before T3's build.
2. Main agent reads both traces → forms the T2 scope hypothesis.
3. **T3 diagnostic build runs serialized** (library build + test). Its result is
   the gate.
4. Main agent writes the scope verdict into `plan.md` Notes and appends the
   Branch A/B/C sub-rows (see plan-template.md "Dynamic rows").
5. Branch downstream work (fix, upstream report, Firefox regression test build)
   is main-agent + serialized builds. Branch C reuses the on-disk C/L trace files
   rather than re-tracing.

No new teams run inside the branches — they consume the trace files already on
disk.

## Test builds serialize

`./mach build` (and the library builds in T3/A4/C4) **cannot** run in multiple
parallel agents in one working tree: concurrent objdir writes corrupt the build,
and a branch can only be checked out at one ref. Therefore:

- **Team T drafts in parallel** (read-only authoring) — this is the parallel part.
- **The main agent serializes** write → `./mach build` → run → capture, one build
  at a time, per proof-test row (16.x).
- **Fast path:** front-end-only proof tests (JS/markup, no C++/Rust change) use
  `./mach build faster` instead of a full build.

Builds in *different* repos/trees (T3's library build vs. the Firefox tree) may in
principle overlap, but T3 is a gate by dependency, so keep it before the
scope-dependent Firefox proof-test build.

---

## Diagnosis Review team

After the analysis doc is written and the main agent's thin structural self-check
passes, launch the three reviewers in **one message**. Each writes a dedicated
file under `<run_dir>/review/` and returns a short verdict.

| Reviewer | File | Job |
|---|---|---|
| **L (links / citations)** | `review/L.md` | Open every code link in `bug-<id>-analysis.md` via `Read`. Confirm the cited file/line still says what the doc claims. Replace any trunk URL with a `$SHERLOCK_REV` link. Report pass/fail + fix-up diffs. |
| **T (test re-runner)** | `review/T.md` | Re-read `firefox/debug/bug-<id>-test-run.log` (and, if cheap, re-apply each `firefox/fix/*.patch` and rebuild). Confirm the proof test FAILs **on the bug**, not on a test-setup error. Reject any committed `#ifdef`-injected test lacking a documented "no benign reproducer" justification. Report pass/fail. |
| **R (red-pen on root cause)** | `review/R.md` + `review/bug-<id>-rootcause-review.md` | Invoke `Skill(red-pen, "<run_dir>/bug-<id>-analysis.md <run_dir>/review/bug-<id>-rootcause-review.md")`. The **explicit output path is required** — without it red-pen resolves to `bug-<id>-review.md`, which is the Decide-phase solutions review. The independent reviewer challenges the root cause, the hypothesis-tree ranking, and the assumption labels; Reviewer R then writes its verdict plus a pointer to the full review into `review/R.md`. |

Reviewer R judges the **root cause**. The separate `Decide.5` red-pen judges the
**solutions**. Different targets — both fire, and both are required.

Handle reviewer failures by looping back (the offending plan.md row goes back to
`in-progress` and the artifact is rewritten):

- Reviewer L fail → `Diagnose.15` (re-edit doc + relink).
- Reviewer T fail → `Diagnose.13`/`Diagnose.14` (fix/re-run the test) or
  `Diagnose.12` (correct the verdict).
- Reviewer R `revise` → `Diagnose.15`. `redesign` → escalate to the user.
  `reject` / `needs-more-info` → back to Wave 2 (gather more evidence).

Do not argue with the reviewer (Gotcha #13).

---

## Synthesis (main agent, not delegated)

After Wave 2, set the synthesis row `in-progress`, read **all** team files (not
the subagent transcripts), and write `<run_dir>/teams/synthesis.md`:

1. Merged code-trace + design-intention narrative; note any drift.
2. Re-rank the hypothesis tree against the gathered evidence. Revive any pruned
   hypothesis the evidence warrants — do not silently re-anchor.
3. Classify each hypothesis as `to-test` / `refuted` / `assumption-only`, citing
   the Team C/L/D/X evidence that drove the classification.
4. State the **verified root cause** with two-tier labels (Verified / `[Assumption]`),
   and the sentence on how the root cause relates to (violates / reveals a gap in /
   drifts from) the design intention.
5. State the **broken invariant** in one sentence: the property that Team D's
   function contract implies should always hold, and that the root cause shows
   does not. This sentence is the hand-off into the Reframe phase — without it,
   Reframe has to re-derive the contract from scratch.
6. Append one row 16.x to `plan.md` per `to-test` hypothesis.

Mark synthesis `completed`.

---

## Wave 3 — Reframe teams

Launch Teams P, E, I and W in the **same message**. All are read-only. Read
`references/first-principles.md` first — it defines the five questions these
teams serve and the discipline each answer must meet.

**None of these teams may propose a patch, a diff, or a concrete fix.** They
produce what must be *true*; concrete approaches are Wave 4's job. A team that
returns a code change has stepped outside its contract and is re-prompted.

### Team P — Problem framing

**Goal:** supply the evidence behind "why is this a problem" (Q1) and "why do we
have it in the first place" (Q2). The main agent writes the answers; Team P
supplies the trail.

**Prompt template:**
```
You are Team P in sherlock (Reframe phase). Gather evidence about why this
problem matters and how it came to exist. Do NOT propose a fix of any kind.

Inputs:
- Analysis doc: <run_dir>/bug-<bug_id>-analysis.md
- Design archaeology: <run_dir>/teams/team-d-design-archaeology.md
- Synthesis: <run_dir>/teams/synthesis.md
- Repo root: <repo-root>
- Searchfox revision: <$SHERLOCK_REV>

Tasks:
1. Identify the GUARANTEE that is broken and state it as a proposition (e.g.
   "a decoded frame's dimensions always match those negotiated at init"), not as
   a description of the failure.
2. Enumerate WHO relies on that guarantee: end users, web content, the spec,
   named internal callers, a security boundary, future maintainers. Cite call
   sites or spec text for each.
3. Establish the ORIGIN. Using git history, the introducing commit, and the
   linked bugs, find the specific decision, constraint, or absence that permitted
   this. Classify it as one of: missing contract | contract drift | layering
   violation | representable illegal state | duplicated path | lapsed purpose |
   defensive accretion. Cite the commit or the absence.
4. Identify WHAT CHANGED since that decision was reasonable.

Output:

1. **Write to disk:** `<run_dir>/teams/team-p-problem-framing.md`:
   - Broken guarantee (as a proposition)
   - Dependents table: | Who | How they rely on it | Evidence |
   - Concrete harm, and harm class (correctness | security | performance |
     maintainability)
   - Origin category + the specific decision (commit hash / bug / the absence)
   - What made it reasonable at the time
   - What changed since
   - "If never fixed, who notices" — answer honestly, including "nobody"

2. **Return** a short summary (≤10 lines): the guarantee in one line, the origin
   category, and the single most load-bearing dependent.

Hard rules: cite commits, bugs, file:line, or spec sections for every claim;
label anything unconfirmed `[Assumption]`. "Technical debt" and "legacy code" are
NOT acceptable origin answers — name the decision. Do NOT propose fixes.
```

### Team E — Elimination scan

**Goal:** answer "does this code still deserve to exist?" (Q3), and produce the
**call-site census** that the Design and Decide phases both reuse.

**Prompt template:**
```
You are Team E in sherlock (Reframe phase). Determine whether the culprit code
can be REMOVED rather than fixed, and produce a call-site census. Do NOT design a
fix.

Inputs:
- Analysis doc: <run_dir>/bug-<bug_id>-analysis.md
- Suspect symbols: <list>
- Suspect files: <list>
- Repo root: <repo-root>
- Searchfox revision: <$SHERLOCK_REV>

Tasks:
1. CENSUS. For each suspect symbol, enumerate every call site using
   `searchfox-cli` and grep. Record file:line, the caller, and whether the caller
   depends on the current narrow contract. This census is reused downstream —
   make it complete and cite everything.
2. REACHABILITY. Determine whether each symbol is reachable from production code,
   only from tests, or only from a dead branch. A "no callers" claim MUST cite
   the search that established it.
3. SUPERSESSION. Look for a newer mechanism that already does this job, with the
   suspect code surviving as a fallback. Check for parallel implementations and
   migration commits.
4. PREMISE. Check whether the code's premise still holds: the platform, pref,
   codec, build configuration, or upstream bug it was written for. Check whether
   any pref gating it still ships, and whether any `#ifdef` guarding it is still
   ever true.
5. WORKAROUND CHECK. If it is a workaround for an external bug, check whether
   that bug has since been fixed upstream.

Output:

1. **Write to disk:** `<run_dir>/teams/team-e-elimination.md`:
   - **Call-site census** table: | Symbol | Call sites | Files (permalinks) |
     Depends on narrow contract? |
   - Per removal candidate: what would be removed, reachability + evidence,
     superseded-by, premise-still-true, what else would be removed with it,
     confidence (high/medium/low) with reasoning
   - "Deleting this deletes the bug: yes / partially / no" per candidate
   - Explicit statement of blast radius per candidate

2. **Return** a short summary (≤10 lines): census size (n symbols, n call sites),
   removal-candidate count, and the highest-confidence candidate in one line.

Hard rules: every "no callers" / "dead code" / "never true" claim cites the
search that established it. Revision-pinned links only. Do NOT propose a
replacement design. Do NOT judge whether removal is practical or uplift-safe —
report the blast radius and let the main agent judge.
```

### Team I — Invariant discovery

**Goal:** answer "what must always be true?" (Q4).

**Prompt template:**
```
You are Team I in sherlock (Reframe phase). Enumerate the invariants that would
make this bug IMPOSSIBLE rather than handled. Do NOT write a patch.

Inputs:
- Analysis doc: <run_dir>/bug-<bug_id>-analysis.md
- Design archaeology (function contract): <run_dir>/teams/team-d-design-archaeology.md
- Broken invariant (from synthesis): <paste the one-sentence statement>
- Code trace: <run_dir>/teams/team-c-code-trace-firefox.md
- Repo root: <repo-root>
- Searchfox revision: <$SHERLOCK_REV>
- Method: references/first-principles.md, section Q4

For EACH function, method, field, or class on the failing path, propose the
invariant(s) that would close the failure. Every invariant MUST have all four of:
  - Subject       — which symbol it binds
  - Statement     — what is always true of it, phrased as a proposition
  - Enforcement point — where it becomes true and stays true (constructor,
    factory, type, setter, single entry point)
  - Verification method — how we would KNOW it holds: type | MOZ_ASSERT |
    MOZ_DIAGNOSTIC_ASSERT | static_assert | release check | test

An invariant missing an enforcement point or a verification method is a wish.
Put those in a separate "Demoted" list with a note on what is missing — do not
pad the main table.

Also record per invariant:
  - Current violation site (file:line, permalink)
  - Whether it FIXES the identified cause, PREVENTS it arising, or AVOIDS it
  - Strength: unrepresentable | enforced-at-one-point | asserted |
    checked-and-handled (see first-principles.md for the ranking)

Output:

1. **Write to disk:** `<run_dir>/teams/team-i-invariants.md`:
   - Invariant table with IDs I1, I2, … and every column above
   - One paragraph per invariant explaining the mechanism
   - "Demoted" list with the reason each was demoted

2. **Return** a short summary (≤10 lines): invariant count, how many reach
   "unrepresentable" or "enforced-at-one-point" strength, and the single
   invariant that would close the most failure surface.

Hard rules: do NOT write code beyond naming an assertion or a type. Do NOT
estimate effort or judge feasibility — that is the Decide phase. Cite the
violation site for every invariant.
```

### Team W — Widening & unification

**Goal:** answer "can we widen instead of narrow?" (Q5).

**Prompt template:**
```
You are Team W in sherlock (Reframe phase). Find places where a contract could be
WIDENED to accept more cases rather than reject them, and where that would
collapse redundant checks or unify duplicated paths. Do NOT write a patch.

Inputs:
- Analysis doc: <run_dir>/bug-<bug_id>-analysis.md
- Code trace: <run_dir>/teams/team-c-code-trace-firefox.md
- Suspect symbols: <list>
- Repo root: <repo-root>
- Searchfox revision: <$SHERLOCK_REV>
- Method: references/first-principles.md, section Q5

Tasks:
1. Enumerate every narrow guard, early return, special case, and rejection on the
   failing path. Cite file:line for each.
2. For each, ask whether the domain could be EXTENDED so the currently-rejected
   input gets a well-defined result. A widening proposal is only valid when BOTH:
     (a) a reliable way to compute the correct result for the new inputs exists —
         not a guess, not a silent default that hides a caller bug; and
     (b) further handling (error report, callback, return path) is predictable,
         controllable, and testable.
   State (a) and (b) explicitly for each proposal, or drop it.
3. Identify the redundant condition checks that would COLLAPSE if the contract
   widened — cite each one.
4. Identify duplicated or near-duplicated code paths that would UNIFY, and say
   what bug family that would close (two paths that must agree but can drift).
5. Identify callers that would SIMPLIFY because they could stop pre-validating.
6. SECURITY COUNTER-CASE: for each proposal, state whether the narrow domain IS
   the security property. If widening would move validation away from a security
   boundary, say so and mark the proposal as rejected on those grounds.

Output:

1. **Write to disk:** `<run_dir>/teams/team-w-widening.md`, per proposal:
   - What currently rejects, and the proposed accepted domain
   - (a) the reliable result for each newly-accepted input
   - (b) the downstream handling and how it would be tested
   - Guards that collapse (permalinks)
   - Paths that unify, and the bug family that closes
   - Callers that simplify
   - Security counter-case verdict

2. **Return** a short summary (≤10 lines): proposal count, how many pass both (a)
   and (b), how many were rejected on security grounds, and the one with the
   largest simplification payoff.

Hard rules: "we could be more permissive" is NOT a proposal — name the defined
result. Do NOT propose a patch. Do NOT estimate effort.
```

---

## Wave 4 — Design fleets

Launch Fleet G and Fleet F in the **same message**. Team M runs afterwards, at
`Design.3`, because it needs the assembled option set.

### Fleet G — Guided brainstorm

**One agent per adopted principle**, not N identical agents. Diversity comes from
the assigned lens, not from repetition — this is what makes the outputs
genuinely different rather than three rewordings of the same idea.

**Prompt template (one per adopted principle):**
```
You are a guided solution designer in sherlock (Design phase). Propose concrete
approaches that realise ONE assigned design principle.

Inputs:
- Analysis doc: <run_dir>/bug-<bug_id>-analysis.md
- Principles doc: <run_dir>/bug-<bug_id>-principles.md
- Call-site census: <run_dir>/teams/team-e-elimination.md
- YOUR ASSIGNED PRINCIPLE: <principle ID and full statement>
- Repo root: <repo-root>
- Searchfox revision: <$SHERLOCK_REV>

Propose 1–3 concrete approaches that realise YOUR assigned principle. Do not
propose approaches that realise a different principle — another agent has that
one. If your principle genuinely cannot be realised, say so and explain why;
that is a useful result.

For each approach:
- Summary (2–3 sentences)
- Core ideas (bullets)
- Which invariant IDs from the principles doc it establishes, and by what
  mechanism (or an explicit "establishes none, because…")
- Implementation overview: files touched (permalinks), order of work, test plan,
  migration/compat concerns
- Which proof test would flip FAIL→PASS
- Pros and cons

Output:

1. **Write to disk:** `<run_dir>/teams/design-g-<principle-slug>.md`
2. **Return** a short summary (≤10 lines): approach count, one line each, and
   whether any invariant in your principle proved unrealisable.

Hard rules: ground every file reference in a revision-pinned permalink. Use the
call-site census for blast-radius claims rather than guessing. Do NOT rank your
approaches against approaches you have not seen. Do NOT declare a winner.
```

### Fleet F — Free-mind brainstorm

**Isolated from the Reframe phase on purpose.** Fleet F is the anti-anchoring
control: if the principles framing has quietly excluded a good approach, only an
agent that never saw the framing will find it.

Launch 2–3 agents, **one per lens**, e.g. *smallest possible change*, *how would
you build this today*, *what would another engine or the upstream project do*.

**Prompt template (one per lens):**
```
You are a free-mind solution designer in sherlock (Design phase). Propose
approaches from first principles, unconstrained by any prior framing.

Input — this is the ONLY sherlock document you may read:
- Analysis doc (stripped copy): <run_dir>/teams/analysis-for-fleet-f.md

DO NOT READ these files. They contain a design framing that would anchor you, and
your independence from it is the entire reason you were launched:
- <run_dir>/bug-<bug_id>-analysis.md  (read the stripped copy above instead)
- <run_dir>/bug-<bug_id>-principles.md
- <run_dir>/teams/team-p-problem-framing.md
- <run_dir>/teams/team-e-elimination.md
- <run_dir>/teams/team-i-invariants.md
- <run_dir>/teams/team-w-widening.md
- <run_dir>/teams/design-g-*.md

Reading the Firefox source, searchfox, git history, specs and the bug report is
expected and encouraged.

YOUR LENS: <one of — "the smallest change that could possibly work" | "how would
you build this subsystem today, ignoring what exists" | "what would another
engine, or the upstream project, do here">

Other inputs:
- Repo root: <repo-root>
- Searchfox revision: <$SHERLOCK_REV>

Propose 2–4 approaches through your lens. For each:
- Summary (2–3 sentences)
- Core ideas (bullets)
- The named strategy or philosophy behind it — give it a short name
- Implementation overview: files touched (permalinks), order of work, test plan
- Pros and cons

Output:

1. **Write to disk:** `<run_dir>/teams/design-f<N>-freemind.md`
2. **Return** a short summary (≤10 lines): approach count and one line each.

Hard rules: revision-pinned links only. Do NOT declare a winner. If you believe
the root cause in the analysis doc is wrong, say so in a clearly-marked section
rather than silently solving a different problem.
```

### Team M — Comparison matrix

Runs at `Design.3`, after the main agent has categorised and merged. It reads the
assembled option set — it does not invent options.

**Prompt template:**
```
You are Team M in sherlock (Design phase). Build a comparison matrix over an
existing option set. Do NOT invent options and do NOT recommend one.

Inputs:
- Draft solutions doc: <run_dir>/bug-<bug_id>-solutions.md
  (written by `Design.2`; its Comparison section is empty — you fill it)
- Principles doc (invariant table): <run_dir>/bug-<bug_id>-principles.md
- Call-site census: <run_dir>/teams/team-e-elimination.md
- Bug context (branch status, sec keywords): <run_dir>/teams/team-b-bug-context.md
- Repo root: <repo-root>

Produce one row per option with these columns:
  Option | Philosophy | Scope (files) | Effort (L/M/H) | Risk (L/M/H) |
  Perf impact | Invariants covered (IDs) | Blast radius (call sites) |
  Uplift-friendly (yes/no) | Test verifiable (yes/no) | Pros | Cons

Rules for specific columns:
- Blast radius comes FROM THE CENSUS, as a count of affected call sites. Do not
  estimate it.
- Invariants covered cites invariant IDs from the principles doc. An option that
  covers none gets an explicit "none".
- Uplift-friendly considers patch size, blast radius, and whether the change is
  mechanical enough for a branch reviewer — using the branch status and sec
  keywords in the bug context file.
- Test verifiable means: would the existing proof test flip FAIL→PASS under this
  option?

Output:

1. **Write to disk:** `<run_dir>/teams/team-m-comparison.md` — the table, plus a
   short "column notes" section explaining any judgement call you made.
2. **Return** a short summary (≤10 lines): the sharpest trade-off in the set, and
   any column you could not fill and why.

Hard rules: do NOT rank, score, or recommend — that is the Decide phase, and it
must reach its ordering independently. Do NOT add options.
```

---

## Main-agent only (never delegate)

- Failure-pattern classification.
- Investigation plan / `EnterPlanMode`.
- Hypothesis-tree construction, selection, pruning, re-ranking (Team H is
  candidates-only).
- T1 (user-interactive), T2 scope hypothesis, reading T3 into a scope verdict.
- Synthesis, the verdict, the root-cause statement, and the broken-invariant
  sentence.
- The "how root cause relates to design intention" sentence.
- Two-tier claim verification.
- **Reframe Q1/Q2 answers** and the naming of the design principles (the teams
  supply evidence and candidates; the framing is the main agent's).
- **Design categorisation** — clustering, merging, roadmap sequencing, the
  relation graph.
- **The entire Decide phase** — criteria, weights, scoring, recommendation.
- All gates and user-facing decisions.

A team never declares the root cause, the verdict, the hypothesis ranking, or the
chosen solution. A team that steps outside its contract is re-prompted, not
promoted.

## Anti-patterns

- **Do not** give the same prompt to two teams hoping one returns better results.
- **Do not** let any Wave 1 or Wave 2 team propose a fix or declare the root cause.
- **Do not** let any Wave 3 team propose a patch — Reframe produces what must be
  true, not what code to write.
- **Do not** leak Reframe artifacts into Fleet F prompts. Naming the forbidden
  paths is not enough on its own — never paste principles content either.
- **Do not** let Team M rank or recommend. Its matrix is input to the Decide
  phase, not a substitute for it.
- **Do not** sequentialise teams within a wave. If one team needs another's
  output, that's bad partitioning — restructure (or move it to the next wave).
- **Do not** let Team T build. Builds serialize through the main agent.
