# Agent teams

Sherlock launches research subagents in **one message containing multiple `Agent`
tool calls** so they run concurrently — that is the agent-teams primitive. No
harness flag exists or is needed.

Sherlock's investigation is gated, so teams launch in **two waves**:

- **Stage 2a — intake teams** run *before* any hypothesis exists (formalises the
  old Step 1.1). Teams: **B** (bug-context), **H** (hypothesis brainstorm).
- **Stage 2b — research teams** run *after* the primary hypothesis is chosen,
  targeting the chosen symbols/files (formalises the old Steps 1.5/1.6). Teams:
  **C** (Firefox code-trace), **L** (library code-trace, when 1.5b applies),
  **D** (design archaeology), **X** (cross-browser/spec), **T** (test-framework
  scout + draft).

Between the waves the main agent does the un-delegatable work (see "Main-agent
only" below). After Stage 2b the main agent runs **Synthesis**.

Each team has a tight I/O contract. Subagents never declare the root cause, the
verdict, or the hypothesis ranking; the main agent synthesises after all teams
return.

## Output persistence

**Every team writes its full findings to a dedicated file** under
`<run_dir>/teams/` and returns only a short summary (≤10 lines) for synthesis.
The main agent reads the file when it needs the full results — never relies on the
subagent transcript. This makes the work survivable: if the session halts, the
next session resumes from the on-disk files.

| Team | Output file (under `<run_dir>/teams/`) |
|---|---|
| Team B | `team-b-bug-context.md` |
| Team H | `team-h-hypotheses.md` |
| Team C | `team-c-code-trace-firefox.md` |
| Team L | `team-l-code-trace-library.md` |
| Team D | `team-d-design-archaeology.md` |
| Team X | `team-x-cross-browser.md` |
| Team T | `team-t-frameworks.md` |
| Synthesis (main agent) | `synthesis.md` |

Each prompt template below ends with an instruction to write to that file. Every
invocation passes inputs as **file paths and explicit values** (not "the bug we're
investigating") and includes the framing *"return the requested artifact only; do
not draw conclusions about the root cause."*

---

## Stage 2a — intake teams

Launch Team B and Team H in the **same message**. They are independent: B fetches
and digests bug data; H brainstorms candidate hypotheses from the raw bug
description the main agent passes inline.

### Team B — Bug-context digest

**Goal:** gather all bug context (main bug, duplicates, attachments, Treeherder)
into one digest so the main agent's context is not flooded, and so Steps 1.2
(duplicates), 1.3 (failure pattern), and 1.8a (attachments) all read one file
instead of re-fetching.

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
   - **Pointers**: relative paths to the fetched artifact directories.

2. **Return** a short summary (≤10 lines): title, component, public/private,
   sec-* keywords, one-line failure pattern (consistent/intermittent + count),
   duplicate count, attachment count.

Hard rules:
- Do NOT propose a root cause or speculate about which code is responsible.
- Do NOT include the full text of bug comments — distill to key facts.
- NEVER read, parse, or print any API key. All API access goes through the
  config helper. Do NOT use python3 to parse config files.
```

### Team H — Hypothesis brainstorm (advisory)

**Goal:** generate candidate root-cause hypotheses to *feed* the main agent's
hypothesis tree (Step 1.3b.5). **Advisory only** — the main agent independently
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

## Stage 2b — research teams

Launch every applicable team in the **same message**. Team L only when the bug
involves vendored third-party code (Step 1.5b active). Team D is **skipped** when
1.5b is active (design intention is covered inside the branch workflow A1/B1/C1) —
set its plan.md row `skipped`. Team X is skipped for internal-only bugs with no
web surface.

All Stage 2b teams are **read-only** (searchfox / upstream tracing / git history /
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
permalinks. Only launched when Step 1.5b is active.

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
believed they were establishing. Skipped when Step 1.5b is active.

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
   postconditions, invariants, threading, ownership).

Output:

1. **Write to disk:** `<run_dir>/teams/team-d-design-archaeology.md`:
   - Introducing commit (hash, summary, linked bug)
   - Original purpose (1 sentence)
   - Design rationale (cite commit message / bug discussion)
   - Constraints / tradeoffs
   - Function contract (preconditions, postconditions, invariants, threading,
     ownership)
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

## Third-party (Step 1.5b) coexistence with parallel teams

The third-party sub-workflow is inherently **sequential** and is NOT a team:

- **T1** (locate the upstream repo) needs interactive user input — `AskUserQuestion`.
- **T2** (scope hypothesis: library / integration / local-patch) is main-agent
  judgment.
- **T3** is a **mandatory diagnostic build** that reproduces the bug in the
  upstream library — a **GATE** whose result chooses Branch A / B / C.

Ordering when 1.5b is active:

1. Stage 2b launches the read-only traces **Team C + Team L** (and X, T) in
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

---

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

## Phase 5 — review team

After the analysis doc is written (row 17) and the main agent's thin structural
self-check passes, launch the three reviewers in **one message**. Each writes a
dedicated file under `<run_dir>/review/` and returns a short verdict.

| Reviewer | File | Job |
|---|---|---|
| **L (links / citations)** | `review/L.md` | Open every code link in `bug-<id>-analysis.md` via `Read`. Confirm the cited file/line still says what the doc claims. Replace any trunk URL with a `$SHERLOCK_REV` link. Report pass/fail + fix-up diffs. |
| **T (test re-runner)** | `review/T.md` | Re-read `firefox/debug/bug-<id>-test-run.log` (and, if cheap, re-apply each `firefox/fix/*.patch` and rebuild). Confirm the proof test FAILs **on the bug**, not on a test-setup error. Reject any committed `#ifdef`-injected test lacking a documented "no benign reproducer" justification. Report pass/fail. |
| **R (red-pen on root cause)** | `review/R.md` | Invoke `Skill(red-pen, <abs path to bug-<id>-analysis.md>)`. The independent reviewer challenges the root cause, the hypothesis-tree ranking, and the assumption labels. Verdict goes into the file. |

Reviewer R judges the **root cause** (Phase 1). The separate Phase-2 `red-pen`
(SKILL Step 2.3) judges the **solutions**. Different targets — both fire.

Handle reviewer failures by looping back (the offending plan.md row goes back to
`in-progress` and the artifact is rewritten):

- Reviewer L fail → row 17 (re-edit doc + relink).
- Reviewer T fail → row 16 (fix/re-run the test) or row 15 (correct the verdict).
- Reviewer R `revise` → row 17. `redesign` → escalate to the user. `reject` /
  `needs-more-info` → back to Stage 2b (gather more evidence).

Do not argue with the reviewer (Gotcha #11).

---

## Synthesis (main agent, not delegated)

After Stage 2b, set the synthesis row `in-progress`, read **all** team files (not
the subagent transcripts), and write `<run_dir>/teams/synthesis.md`:

1. Merged code-trace + design-intention narrative; note any drift.
2. Re-rank the hypothesis tree against the gathered evidence. Revive any pruned
   hypothesis the evidence warrants — do not silently re-anchor.
3. Classify each hypothesis as `to-test` / `refuted` / `assumption-only`, citing
   the Team C/L/D/X evidence that drove the classification.
4. State the **verified root cause** with two-tier labels (Verified / `[Assumption]`),
   and the sentence on how the root cause relates to (violates / reveals a gap in /
   drifts from) the design intention.
5. Append one row 16.x to `plan.md` per `to-test` hypothesis.

Mark synthesis `completed`.

---

## Main-agent only (never delegate)

- Failure-pattern classification.
- Investigation plan / `EnterPlanMode`.
- Hypothesis-tree construction, selection, pruning, re-ranking (Team H is
  candidates-only).
- T1 (user-interactive), T2 scope hypothesis, reading T3 into a scope verdict.
- Synthesis, the verdict, and the root-cause statement.
- The "how root cause relates to design intention" sentence.
- Two-tier claim verification.
- The Phase Gate and all Phase-2 solution decisions.

A team never declares the root cause, the verdict, or the hypothesis ranking. A
team that steps outside its contract is re-prompted, not promoted.

## Anti-patterns

- **Do not** give the same prompt to two teams hoping one returns better results.
- **Do not** let any team propose a fix or declare the root cause.
- **Do not** sequentialise teams within a wave. If one team needs another's
  output, that's bad partitioning — restructure (or move it to the next wave).
- **Do not** let Team T build. Builds serialize through the main agent.
