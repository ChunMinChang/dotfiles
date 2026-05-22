---
name: blindspot
description: >
  Hypothesis-driven Firefox investigation: given a freeform suspicion that some code
  is buggy, unsafe, mis-behaving, or non-spec, blindspot validates the claim, finds
  real user-facing or security consequences (or proves there are none), and writes a
  bug-style report with revision-pinned code traces, original design intention from
  git history, and end-to-end proof tests. Triggers on: "/blindspot", "investigate
  this claim", "is this a real bug", "prove this is a bug", "find issues in <code>",
  "is this code safe", "what could go wrong with <code>".
argument-hint: "<claim-text-or-file-path> [--output-dir <path>] | --resume <run-dir>"
allowed-tools:
  - Bash(git:*)
  - Bash(jj:*)
  - Bash(searchfox-cli:*)
  - Bash(./mach:*)
  - Bash(.claude/skills/blindspot/blindspot-config:*)
  - Bash(mkdir:*)
  - Bash(cp:*)
  - Bash(ls:*)
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

# Blindspot: hypothesis-driven bug investigation

Follow `../sherlock/references/source-permalinks.md` for ALL source and documentation references.
Follow `../sherlock/references/spec-check.md` when verifying web specification compliance.
Follow `../sherlock/references/gecko-architecture.md` for Gecko architecture lookups.
Follow `references/test-frameworks.md` for test framework selection.

Blindspot is the inverse of `/sherlock`. Sherlock starts from a confirmed bug ID and asks
"why does this fail?". Blindspot starts from a suspicion ("this code looks wrong") and
asks "is this a real bug, and what is the user-facing consequence?".

**Arguments:** $0

Parsing:
- `--resume <run-dir>` mode: skip claim parsing; read `claim.md` and `plan.md` from the
  named directory and continue from the first `pending`/`in-progress` row.
- Otherwise: the argument is treated as **claim text** unless it resolves to a
  readable file, in which case the file contents become the claim.
- `--output-dir <path>` overrides the configured output directory for this run only
  and is not persisted. Ignored when `--resume` is set.

---

## Gotchas

1. **Every claim needs evidence or `[Assumption]` label** — never state hypotheses as
   facts. Read the actual code before asserting anything about its behaviour.
2. **ALWAYS use revision-pinned links** — read `../sherlock/references/source-permalinks.md`.
   Never use trunk/tip URLs (`firefox-main/source/...`) in the report.
3. **Tests are PROOFS** — they must reproduce the user-facing consequence end-to-end,
   without monkey-patching the suspect function. Simulated tests (mocked returns, forced
   branches) are investigation-only and MUST NOT appear in committed `firefox/fix/`
   patches.
4. **Fault-injection is a last resort** — see `references/injection-patterns.md`. Any
   `#ifdef BLINDSPOT_INJECT_*` or allocator-hook patch must be accompanied by a
   "Proof method: fault injection" subsection in the report justifying why a benign
   reproducer is impossible. Phase 5 reviewer rejects un-justified injections.
5. **A valid claim can have no exploitable consequence** — when a sibling check or
   clamp accidentally saves the day, report it as **Lucky-prevented** with the saving
   check linked, plus a "would-become-real-if-…" trigger.
6. **A nonsense claim short-circuits** — Phase 1 writes a rebuttal and STOPS.
7. **Delegate research, not synthesis** — Phase 2 teams gather evidence; the main agent
   classifies hypotheses. A team never declares the verdict.
8. **Five hypotheses minimum in Team H** — blindspot runs on speculative input, so the
   anti-anchoring threshold is higher than sherlock's three.
9. **The reviewer is independent** — when red-pen returns `revise`/`redesign`, loop
   back; do not argue.
10. **Private and security-sensitive material** — if the claim mentions a sec-* class
    (UAF, OOB, RCE, sandbox escape, info-leak), treat the per-run subdir as private.
    Do not echo the report contents in conversation summaries beyond the verdict.
11. **Persist every team output to disk** — Phase 2 teams and Phase 5 reviewers each
    own a named output file in the run dir. Their findings live there, not just in
    the main-agent transcript. A halted session resumes by reading those files.
12. **Update `plan.md` at every transition** — set a row to `in-progress` *before*
    starting work, `completed` after the artifact is on disk. Never leave a row
    silently behind; the progress table is the hand-over document.

---

## Subagent delegation policy

Main-agent context is reserved for synthesis: validity gate, hypothesis pruning,
verdict classification, report wording, review-loop decisions. Bounded research goes
to subagents per `references/agent-teams.md`.

**Delegate** when the task is bounded (clear input + output shape), voluminous
(searchfox dumps, git log archaeology, multi-file traces), or parallelisable.

**Do NOT delegate** validity-gate decisions, the verdict, the hypothesis classifier,
or the final report wording.

---

## Persistence and resume

Every run writes a `plan.md` (workplan + progress table) to its run directory. Each
Phase 2 team and Phase 5 reviewer writes its findings to a dedicated file. The main
agent never relies on subagent transcripts to retain results — it reads the files.

**If a session halts** (server unavailable, context exhausted, user kill, etc.),
re-invoke blindspot with `--resume <run-dir>`. The skill reads `plan.md`, jumps to
the first `pending` or `in-progress` row, and continues. Completed rows are
trusted; their artifacts on disk are the source of truth.

**Team output files** (relative to `<run_dir>`):

| Task | File |
|---|---|
| Team C — Code trace | `team-c-code-trace.md` |
| Team H — Hypothesis brainstorm | `team-h-hypotheses.md` |
| Team D — Design archaeology | `team-d-design-archaeology.md` |
| Team X — Cross-browser & spec | `team-x-cross-browser.md` |
| Team T — Test framework scout | `team-t-frameworks.md` |
| Main-agent synthesis | `synthesis.md` |
| Reviewer L — Links | `review/L.md` |
| Reviewer T — Tests | `review/T.md` |
| Reviewer R — Red-pen | `review/R.md` |

Per-hypothesis Phase 3 artifacts go under `firefox/fix/`, `firefox/debug/`, and
`logs/`, named with the hypothesis index (e.g. `01-test-h1-getimagesize-overflow.patch`).

---

## Phase 0 — Input intake

### Resume branch

If the invocation contains `--resume <run-dir>`:

1. `Read` `<run-dir>/claim.md` to recover the claim.
2. `Read` `<run-dir>/plan.md` to recover the progress table and the
   `Searchfox revision` line; restore `$BLINDSPOT_REV` for the session.
3. Announce in ≤2 lines: "Resuming blindspot run `<slug>` at `<run-dir>`; next
   pending task: `<task name>`."
4. Jump to the phase containing the first `pending`/`in-progress` row. Treat
   `in-progress` rows as un-finished — re-run them; their output file overwrites.
5. Skip the rest of Phase 0.

### Fresh-run branch

1. Run `./.claude/skills/blindspot/blindspot-config --check-setup`. Required:
   `searchfox-cli` on PATH, output directory configured (or supplied via
   `--output-dir`), git user name+email set.
2. Strip `--output-dir <path>` from the arguments. Resolve the output directory:
   a. `--output-dir` from the flag.
   b. `blindspot-config --get-output-dir` (reads
      `~/.config/firefox-blindspot/config.toml`).
   c. If both empty, use `AskUserQuestion` to ask for a directory, then run
      `blindspot-config --set-output-dir <path>` to persist it.
3. Treat the remaining argument as the claim:
   - If it resolves to a readable file via `Read`, use the file contents.
   - Otherwise treat the entire argument verbatim as inline claim text.
4. **Choose a semantic slug** (do not delegate). Read the claim and pick a 3–6
   token kebab-case phrase that captures the gist — the suspect symbol, the
   alleged class of bug, and (when relevant) the module. Good examples:
   `h265sps-getimagesize-overflow`, `ipdl-deserializer-oom`, `media-track-uaf`.
   Bad examples: anything that just echoes the first sentence verbatim
   (`h265sps-returns-int32-from-pair`) or stops mid-word.
   Then sanitize: `blindspot-config --slug "<your-choice>"`. The helper
   lowercases, drops non-alphanumeric chars, and caps the length at 60 chars
   on a hyphen boundary.
5. Create the per-run subdirectory `<output_dir>/<slug>-<YYYYMMDD-HHMMSS>/`.
   Inside it create `firefox/fix/`, `firefox/debug/`, `logs/`, `review/`.
6. Resolve the searchfox revision pin: `blindspot-config --resolve-rev`. Store
   as `$BLINDSPOT_REV`.
7. Write the verbatim claim into `<run_dir>/claim.md`.
8. Write `<run_dir>/plan.md` from `references/plan-template.md`. Substitute
   `{slug}`, `{start_timestamp}`, `{abs_output_dir}`, `{rev_short}`,
   `{rev_full}`. Initial progress: row 1 (Input intake) is `in-progress`; all
   others `pending`.
9. Mark row 1 `completed` in `plan.md`. Append a one-line note in the Notes
   section: "Created run dir, claim ingested ({char_count} chars)."
10. Confirm to the user in ≤3 lines: slug, run-dir path, `$BLINDSPOT_REV` short
    hash, "resume with `/blindspot --resume <run-dir>` if I stop".

---

## Phase 1 — Validity gate (NOT DELEGATABLE)

Apply `references/validity-gate.md`. Run these cheap checks in the main agent:

1. **Symbol existence.** Every concrete symbol/file named in the claim must resolve
   via `searchfox-cli --define '<sym>'` or `searchfox-cli --path '<glob>'`. Record
   misses.
2. **Type/signature plausibility.** If the claim alleges a specific mechanism
   (overflow on `uint32_t→int32_t`, UAF after `Release`, race between threads X and Y,
   missing nullcheck on Z), confirm the relevant types/threading model match. Quote
   the line.
3. **Coherence.** Does the claim describe a *specific* failure mode? Vague claims
   ("this looks fishy") need clarification via `AskUserQuestion`.

**Outcome classification:**

- **Nonsense** — at least one of: cited symbols do not exist; mechanism is type-
  impossible (e.g., "buffer overflow in a value-type `nsString`"); claim is
  self-contradictory.
  Action: write a `report.md` with only the **Verdict** (Nonsense), **Claim**,
  **Validity assessment** (citing what failed), and **What would make it real**
  sections. STOP. Surface the report path to the user.
- **Ambiguous** — claim is coherent but admits multiple interpretations. Use
  `AskUserQuestion` to pin down which interpretation to pursue. Re-run gate.
- **Plausible** — symbols exist, mechanism is type-possible, claim is concrete.
  Proceed to Phase 2.

In `report.md`, the **Validity assessment** section is written *now*, even on the
plausible path, so it records what the gate found (e.g., "function signature confirmed
at L123, return type does narrow from uint32_t to int32_t").

Mark the Validity gate row `completed` in `plan.md` (or `completed` with a
`Nonsense` note if the gate short-circuits).

---

## Phase 1.5 — Investigation plan (EnterPlanMode)

Before launching the Phase 2 teams, **call `EnterPlanMode`**. Draft a short
investigation plan covering:

- The seed hypothesis classes you'll ask Team H to enumerate (e.g. "narrowing
  overflow", "missing nullcheck after Realloc", "race on `mLastUpdated`").
- Which teams to run vs. skip, with a one-line reason per skip.
- Any non-standard build needed (ASan/TSan/debug) and why.
- Open questions for the user.

Present the plan; let the user redirect (refine hypotheses, drop a team, add a
constraint). Once approved, `ExitPlanMode`.

Reflect any plan decisions in `plan.md`:
- Append a note in the Notes section ("Team X skipped: internal codec parser, no
  web surface").
- For any team marked skipped here, set its row to `skipped` directly.

> The harness `EnterPlanMode` writes its own plan file at `~/.claude/plans/…`.
> That is **separate** from `<run_dir>/plan.md` (blindspot's persistent
> progress tracker). Don't conflate them — the harness plan is one-shot user
> approval, blindspot's plan.md is the hand-over document.

---

## Phase 2 — Parallel investigation (agent teams)

Set each non-skipped Phase 2 row in `plan.md` to `in-progress`. Launch all
applicable teams **in a single message containing multiple `Agent` calls** so
they run concurrently. This is the agent-teams primitive — no harness toggle.

Read `references/agent-teams.md` for the full I/O contract per team. Every team
**writes its findings to its dedicated output file** in the run dir and returns
only a short summary (≤10 lines) for synthesis:

- **Team C — Code trace.** Writes `team-c-code-trace.md`. Numbered trace with
  revision-pinned `[Sym](permalink#L…)` lines + "notable observations". No
  root-cause claims.
- **Team H — Hypothesis brainstorm.** Writes `team-h-hypotheses.md`. **≥5**
  scenarios (precondition, mechanism, predicted observable signal, probe cost),
  ranked by `confirm_value / probe_cost`. No verdict.
- **Team D — Design archaeology.** Writes `team-d-design-archaeology.md`.
  Dated commit citations + a "what the author meant" paragraph. No verdict.
- **Team X — Cross-browser & spec check.** Writes `team-x-cross-browser.md`.
  Spec citation + behaviour table.
- **Team T — Test framework scout.** Writes `team-t-frameworks.md`. Framework
  choice + neighbour-test path per hypothesis from Team H.

Skip a team only when the claim is **provably** orthogonal (e.g. skip Team X
for a purely internal helper with no web surface) — and do that at Phase 1.5,
not silently here. Document the skip reason in `plan.md`'s Notes section.

As each team returns, verify its output file exists and is non-empty, then
mark its row `completed` in `plan.md`. If a team aborts mid-task, leave the row
`in-progress` — `--resume` will re-run it.

### Synthesis (main agent, not delegated)

Set the Synthesis row to `in-progress`. Read **all** Phase 2 output files (not
the subagent transcripts) and write `<run_dir>/synthesis.md` containing:

1. Merged code trace + design-intention narrative. Note any drift.
2. Team H ranked list, with each hypothesis classified as `to-test` /
   `lucky-prevented` / `design-smell-only` / `refuted`, citing the Team C/D/X
   evidence that drove the classification.
3. For every `to-test` hypothesis, append a row to `plan.md`'s progress table
   under Phase 3 (e.g. `9.1 | 3 | Validate H1: <one-line> | pending | firefox/fix/01-test-h1-*.patch`).

Mark Synthesis `completed`.

---

## Phase 3 — Experimental validation

Only `to-test` hypotheses come here — one `plan.md` row per hypothesis, added by
Synthesis. For each:

1. Mark this hypothesis's row `in-progress` in `plan.md`.
2. Pick the framework per Team T's recommendation.
3. Create branch (once per run): `git checkout -b blindspot/<slug>` from
   current HEAD if not already.
4. Write the **end-to-end** test in the chosen framework. The test must
   reproduce the user-facing consequence without modifying the suspect function.
   No mocking, no forcing private state, no `#ifdef`-injected return values. If
   you cannot satisfy this constraint, see the fault-injection escape hatch
   below.
5. Build:
   - C++/Rust-touching change → `./mach build` (full).
   - FE-only change → `./mach build faster`.
   - Redirect to `<run_dir>/logs/build-h<N>-<desc>.log` per AGENTS.md (never
     pipe through `tail`/`head`).
6. Run the test, capturing to `<run_dir>/logs/test-h<N>-<desc>.log`. Expectation:
   - Test **fails** → hypothesis confirmed → keep status `to-test → confirmed`.
   - Test **passes** → reclassify as `lucky-prevented`. In `synthesis.md` and
     later in `report.md`, identify *which* check saved the day with a
     revision-pinned link and write the "would-become-real-if-…" trigger.
7. Commit on `blindspot/<slug>`:
   `git commit --author="$(./.claude/skills/blindspot/blindspot-config --get-patch-author)"
   -m "Blindspot proof H<N>: <one-line>"`.
8. Emit the patch:
   `git format-patch -1 --stdout > <run_dir>/firefox/fix/<NN>-test-h<N>-<desc>.patch`
   (NN = the global ordinal across hypotheses).
9. Mark this hypothesis's row `completed` in `plan.md` with the final
   classification noted in the Notes section.

### Fault-injection escape hatch (LAST RESORT)

See `references/injection-patterns.md`. Allowed only when:
- The hypothesis genuinely has no benign reproducer (forced allocator OOM at a
  specific site, compromised IPC peer, sandbox-internal state).
- The injection is gated behind `#ifdef BLINDSPOT_INJECT_<name>` or a build flag, never
  in shipping code paths.
- `report.md` contains a **Proof method: fault injection** subsection naming the
  specific reason a benign reproducer is impossible. Phase 5's Reviewer T rejects any
  committed injection without this section.

### Run `verify` after each proof commit

Invoke `Skill(verify, …)` so formatting/lint regressions don't pollute the review.

---

## Phase 4 — Draft the report

Mark the Draft-report row `in-progress` in `plan.md`. Fill
`references/analysis-template.md` into `<run_dir>/report.md`, sourcing content
from `claim.md`, `synthesis.md`, and each team's output file. Every claim is
labelled Verified or `[Assumption]`. Every link uses `$BLINDSPOT_REV` pinning.
Reuse `Skill(source-links, …)` for any external resource. Mark `completed`
when the report file is written.

The report's **Verdict** is one of:
- **Confirmed** — at least one hypothesis has a passing-on-fix, failing-now proof test.
- **Lucky-prevented** — all `to-test` hypotheses passed (test didn't fail); claim is
  valid but a sibling check prevents user-visible impact.
- **Design-smell-only** — no testable consequence at all, but Team C found a
  maintainability or future-correctness hazard.
- **Refuted** — Team C/D evidence shows the alleged mechanism cannot occur.
- **Nonsense** — Phase 1 short-circuit only.

Do NOT propose fixes. Blindspot produces a *report*. Fixes are a separate workflow
(typically `/sherlock` Phase 2 after the user files the bug, or
`/firefox-implementation` if they jump straight to a patch).

---

## Phase 5 — Review by a second team

Mark each Reviewer row `in-progress` in `plan.md`. Launch in parallel (single
message, multiple `Agent` + `Skill` calls). Every reviewer writes its verdict
to a dedicated file:

- **Reviewer L (Link & citation audit).** Open every code link in `report.md`
  via `Read`. Confirm the cited file/line still says what the report claims.
  Replace any unpinned URL. Writes pass/fail + fix-up diffs to
  `<run_dir>/review/L.md`.
- **Reviewer T (Test re-runner).** Reset to a clean tree, re-apply each
  `firefox/fix/*.patch`, rebuild (or `./mach build faster` if applicable),
  rerun the test. Confirm pass/fail matches the report. Reject any committed
  `#ifdef BLINDSPOT_INJECT_*` patch lacking the "Proof method: fault injection"
  section. Writes to `<run_dir>/review/T.md`.
- **Reviewer R (Independent adversarial).** Invoke `Skill(red-pen, …)` passing
  the draft report path. Verdict goes into `<run_dir>/review/R.md`.

As each reviewer returns, verify its file exists; mark its row `completed`.

If any reviewer reports problems, loop back (the offending phase's row goes
back to `in-progress` and the artifact is rewritten):

- Reviewer L failures → Phase 4 (rewrite + relink).
- Reviewer T failures → Phase 3 (fix tests) or Phase 4 (correct verdict).
- Reviewer R `revise` → Phase 4. `redesign` → escalate to user. `reject` or
  `needs-more-info` → Phase 2 (gather more evidence).

Do not argue with the reviewer; mirror sherlock rule #11.

---

## Phase 6 — Hand off

Mark the Hand-off row `in-progress`. Confirm every other row in `plan.md` is
`completed` or `skipped` (no `pending`/`in-progress` left). If any are not,
loop back to that phase.

Summarise to the user in ≤6 lines:
- Verdict.
- One-sentence reason.
- Path to `<run_dir>/report.md`.
- Red-pen verdict verbatim.
- Path to `<run_dir>/firefox/fix/` if any proof tests landed.
- Suggested next skill (e.g., "file with `/triage`" or "if you want a fix:
  `/sherlock <bug-id>` once filed").

Mark the Hand-off row `completed`. Stop. Blindspot never files the report and
never opens a Bugzilla entry — that's the user's call.

If a session halts before reaching Phase 6, the user can re-invoke with
`/blindspot --resume <run-dir>` and pick up at the first non-completed row.
