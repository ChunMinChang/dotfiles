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
argument-hint: "<claim-text-or-file-path> [--output-dir <path>]"
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
- The argument is treated as **claim text** unless it resolves to a readable file, in
  which case the file contents become the claim.
- `--output-dir <path>` is the only flag; if present, it overrides the configured
  output directory for this run only and is not persisted.

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

## Phase 0 — Input intake

1. Run `./.claude/skills/blindspot/blindspot-config --check-setup`. Required
   prerequisites: `searchfox-cli` on PATH, an output directory configured (or supplied
   via `--output-dir`), git user name+email set.
2. Strip `--output-dir <path>` from the arguments. Resolve the output directory in
   this order:
   a. `--output-dir` from the flag.
   b. `blindspot-config --get-output-dir` (reads `~/.config/firefox-blindspot/config.toml`).
   c. If both empty, use `AskUserQuestion` to ask the user for a directory, then run
      `blindspot-config --set-output-dir <path>` to persist it.
3. Treat the remaining argument as the claim:
   - If it resolves to a readable file via `Read`, use the file contents.
   - Otherwise treat the entire argument verbatim as inline claim text.
4. Generate a slug from the first ~5 tokens of the claim via
   `blindspot-config --slug "<claim>"`.
5. Create the per-run subdirectory:
   `<output_dir>/<slug>-<YYYYMMDD-HHMMSS>/`. Within it, create `firefox/fix/`,
   `firefox/debug/`, `logs/`, `review/`.
6. Write the verbatim claim into `<run_dir>/claim.md`.
7. Resolve the searchfox revision pin into `$BLINDSPOT_REV` for the session:
   `blindspot-config --resolve-rev`.
8. Confirm to the user in ≤2 lines: slug, resolved output directory,
   `$BLINDSPOT_REV` short hash.

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

---

## Phase 2 — Parallel investigation (agent teams)

Launch all applicable teams **in a single message containing multiple `Agent` calls**
so they run concurrently. This is the agent-teams primitive — no harness toggle.

Read `references/agent-teams.md` for the full I/O contract per team. Summary:

- **Team C — Code trace.** Trace the suspect function with `searchfox-cli`: every
  caller, every consumer of the return, every gating check. Output: numbered trace
  with revision-pinned `[Sym](permalink#L…)` lines + a "notable observations" block.
  No root-cause claims.
- **Team H — Hypothesis brainstorm.** Generate **≥5** concrete failure scenarios
  (precondition, mechanism, predicted observable signal, probe cost) and rank them
  by `confirm_value / probe_cost`. No verdict.
- **Team D — Design archaeology.** Walk `git log -S`, `git blame`, and the Bugzilla
  bugs of introducing commits. Output: dated commit citations + a "what the author
  meant" paragraph. No verdict.
- **Team X — Cross-browser & spec check.** Look up the relevant spec section
  (use `Skill(webspec-index, …)` when applicable), grep `testing/web-platform/tests/`
  for existing coverage, optionally invoke `Skill(playwright, …)` to observe live
  Chrome/Safari behaviour. Output: behaviour table + spec citation.
- **Team T — Test framework scout.** For each hypothesis from Team H, pick the right
  framework using `references/test-frameworks.md` and find a representative neighbour
  test in the tree whose conventions the new test should mirror. Output: framework
  choice + neighbour-test path per hypothesis.

Skip a team only when the claim is **provably** orthogonal (e.g., skip Team X for a
purely internal codec parser with no web surface). Document the skip reason in
`report.md`.

After all teams return, the main agent **synthesises**:
1. Merge Team C's trace with Team D's design intention. Note any drift.
2. Walk Team H's ranked list. For each hypothesis, mark
   `to-test` / `lucky-prevented` / `design-smell-only` / `refuted` using Team C/D/X
   evidence.
3. Pick the `to-test` hypotheses for Phase 3. Hypotheses already proven `refuted` or
   `lucky-prevented` skip Phase 3.

---

## Phase 3 — Experimental validation

Only `to-test` hypotheses come here. For each:

1. Pick the framework per Team T's recommendation.
2. Create branch: `git checkout -b blindspot/<slug>` from current HEAD if not already.
3. Write the **end-to-end** test in the chosen framework. The test must reproduce the
   user-facing consequence without modifying the suspect function. No mocking, no
   forcing private state, no `#ifdef`-injected return values. If you cannot satisfy
   this constraint, see the fault-injection escape hatch below.
4. Build:
   - C++/Rust-touching change → `./mach build` (full).
   - FE-only change → `./mach build faster`.
   - Redirect to `<run_dir>/logs/build-<hypothesis>.log` per AGENTS.md (never pipe
     through `tail`/`head`).
5. Run the test, capturing to `<run_dir>/logs/test-<hypothesis>.log`. Expectation:
   - Test **fails** → hypothesis confirmed → keep status `to-test → confirmed`.
   - Test **passes** → reclassify as `lucky-prevented`. In `report.md`, identify
     *which* check saved the day with a revision-pinned link and write the
     "would-become-real-if-…" trigger.
6. Commit on `blindspot/<slug>`:
   `git commit --author="$(./.claude/skills/blindspot/blindspot-config --get-patch-author)"
   -m "Blindspot proof: <one-line>"`.
7. Emit the patch:
   `git format-patch -1 --stdout > <run_dir>/firefox/fix/01-test-<desc>.patch`.

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

Fill `references/analysis-template.md` into `<run_dir>/report.md`. Every claim is
labelled Verified or `[Assumption]`. Every link uses `$BLINDSPOT_REV` pinning. Reuse
`Skill(source-links, …)` for any external resource.

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

Launch in parallel (single message, multiple `Agent` + `Skill` calls):

- **Reviewer L (Link & citation audit).** Open every code link in `report.md` via
  `Read`. Confirm the cited file/line still says what the report claims. Replace any
  unpinned URL. Output: pass/fail + fix-up diffs into `<run_dir>/review/L.md`.
- **Reviewer T (Test re-runner).** Reset to a clean tree, re-apply each
  `firefox/fix/*.patch`, rebuild (or `./mach build faster` if applicable), rerun the
  test. Confirm pass/fail matches the report. Reject any committed
  `#ifdef BLINDSPOT_INJECT_*` patch lacking the "Proof method: fault injection"
  section. Output to `<run_dir>/review/T.md`.
- **Reviewer R (Independent adversarial).** Invoke `Skill(red-pen, …)` passing the
  draft report path. Verdict goes into `<run_dir>/review/R.md`.

If any reviewer reports problems, loop back:
- Reviewer L failures → Phase 4 (rewrite + relink).
- Reviewer T failures → Phase 3 (fix tests) or Phase 4 (correct verdict).
- Reviewer R `revise` → Phase 4. `redesign` → escalate to user. `reject` or
  `needs-more-info` → Phase 2 (gather more evidence).

Do not argue with the reviewer; mirror sherlock rule #11.

---

## Phase 6 — Hand off

Summarise to the user in ≤6 lines:
- Verdict.
- One-sentence reason.
- Path to `<run_dir>/report.md`.
- Red-pen verdict verbatim.
- Path to `<run_dir>/firefox/fix/` if any proof tests landed.
- Suggested next skill (e.g., "file with `/triage`" or "if you want a fix:
  `/sherlock <bug-id>` once filed").

Stop. Blindspot never files the report and never opens a Bugzilla entry. That's the
user's call.
