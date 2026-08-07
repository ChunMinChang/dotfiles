# Sherlock run: bug {bug_id}

- **Run status:** in-progress
- **Started:** {start_timestamp}
- **Bug:** {bug_id} ({public_or_private})
- **Run directory:** `{abs_run_dir}`
- **Searchfox revision:** `{rev_short}` (full: `{rev_full}`)
- **Working branch:** `sherlock/bug-{bug_id}`
- **Branch base (`SHERLOCK_BASE`):** `{base_sha}` — local HEAD when the branch was
  cut at `Diagnose.6`. **Not** the same as the Searchfox revision above, which may
  be an older indexed commit. The `Implement.3` reorder and branch recovery need this.
- **Branch tip:** `{tip_sha}` — updated after every commit-producing row, so a lost
  branch can be recovered by SHA rather than recreated empty.

## Third-party fields
> Filled at `Diagnose.9`/T1 when vendored code is involved; otherwise "n/a".

- **Library:** {name} · **Upstream:** {url} · **Vendored revision:** `{hash}`
- **Local library repo:** `{absolute path}`
- **Library branches:** `sherlock/bug-{bug_id}/test`, `/debug`, `/fix`
- **Scope verdict:** {Branch A / B / C, from T3}

> `Run status` becomes **FINISHED** only in the Consolidate phase, once every row
> is `completed` or `skipped` and every follow-up is filed or explicitly handed
> to the user. A run blocked on an external dependency ends as **POSTPONED**
> instead — see the `blocked-external` status below.

## How to resume

If this run was interrupted (server unavailable, context exhausted, power
outage, kill, etc.), re-invoke sherlock with either:

```bash
/sherlock --resume {abs_run_dir}
# or, since the bug id locates the run dir:
/sherlock {bug_id}
```

Sherlock reads this file, finds the first `pending` or `in-progress` row, and
continues from there. Completed rows are trusted — the artifacts on disk are the
source of truth. `in-progress` rows are treated as un-finished and re-run; their
output file is overwritten. `blocked-on-user` rows (the gates) are re-presented
to the user.

**Do NOT re-resolve the Searchfox revision on resume** — it is pinned above and
every link already on disk depends on it. Read it back from this file. Only
`$SHERLOCK_AUTHOR` is re-resolved (it is deterministic).

## Progress

Statuses: `pending` / `in-progress` / `completed` / `skipped` / `blocked-on-user` /
`blocked-external`.

`blocked-external` is for work that cannot proceed until something outside this run
lands (a blocking bug, an upstream release). It is a terminal status for the run:
Consolidate ends such a run as **POSTPONED**, not FINISHED. Do not mark a genuine
blocker `skipped` just to close the table out.

| #   | Phase       | Task                                                        | Status   | Artifact                                                     |
|-----|-------------|-------------------------------------------------------------|----------|--------------------------------------------------------------|
| 1   | Intake      | Setup (config, output dir, revision pin, author)            | pending  | `plan.md`                                                    |
| 2   | Diagnose    | Team B — bug-context digest (+ branch status flags)         | pending  | `teams/team-b-bug-context.md`, `bug-{bug_id}-report/`        |
| 3   | Diagnose    | Team H — hypothesis brainstorm (advisory)                   | pending  | `teams/team-h-hypotheses.md`                                 |
| 4   | Diagnose    | `Diagnose.2` duplicate / related analysis                   | pending  | analysis-doc Related Context                                 |
| 5   | Diagnose    | `Diagnose.3` failure-pattern classification                 | pending  | analysis-doc Failure Pattern                                 |
| 6   | Diagnose    | `Diagnose.4` investigation plan (EnterPlanMode)             | pending  | harness plan + Notes                                         |
| 7   | Diagnose    | `Diagnose.5` hypothesis tree ≥3                             | pending  | analysis-doc Hypothesis Tree                                 |
| 8   | Diagnose    | `Diagnose.6` Firefox working branch                         | pending  | branch `sherlock/bug-{bug_id}`                               |
| 8.5 | Diagnose    | `Diagnose.7` code-path research + third-party determination | pending  | analysis-doc Code Path Trace + Notes (vendored yes/no)       |
| 9   | Diagnose    | Team C — Firefox code-trace                                 | pending  | `teams/team-c-code-trace-firefox.md`                         |
| 10  | Diagnose    | Team L — library code-trace (if `Diagnose.9`)               | pending  | `teams/team-l-code-trace-library.md`                         |
| 11  | Diagnose    | Team D — design archaeology (skip if `Diagnose.9`)          | pending  | `teams/team-d-design-archaeology.md`                         |
| 12  | Diagnose    | Team X — cross-browser / spec (skip if internal)            | pending  | `teams/team-x-cross-browser.md`                              |
| 13  | Diagnose    | Team T — test-framework scout + draft                       | pending  | `teams/team-t-frameworks.md`                                 |
| 14  | Diagnose    | `Diagnose.9` third-party gate (T1/T2/T3 diagnostic)         | pending  | `<library>/debug/` logs + scope verdict in Notes             |
| 15  | Diagnose    | `Diagnose.12` synthesis + root cause + broken invariant     | pending  | `teams/synthesis.md`                                         |
| 16  | Diagnose    | `Diagnose.13`/`.14` proof tests (serialized build + run)    | pending  | rows 16.x appended per hypothesis (`firefox/fix/`, `firefox/debug/`) |
| 16.5| Diagnose    | `Diagnose.11` two-tier claim verification                   | pending  | analysis-doc Verified Claims / Assumptions                   |
| 17  | Diagnose    | `Diagnose.15` analysis doc generated                        | pending  | `bug-{bug_id}-analysis.md`                                   |
| 17.5| Diagnose    | `Diagnose.16` structural self-check                         | pending  | checklist result in Notes                                    |
| 18  | Diagnosis Review | Reviewer L — links / citations                              | pending  | `review/L.md`                                                |
| 19  | Diagnosis Review | Reviewer T — test re-runner                                 | pending  | `review/T.md`                                                |
| 20  | Diagnosis Review | Reviewer R — red-pen on root cause (REVIEW #1)              | pending  | `review/R.md`, `review/bug-{bug_id}-rootcause-review.md`     |
| 21  | Gate        | **Root cause agreed** (user review)                         | pending  | terminal output                                              |
| 22  | Reframe     | `Reframe.1` problem framing Q1/Q2 (main agent)              | pending  | principles-doc Q1/Q2                                         |
| 23  | Reframe     | Team P — problem-framing evidence                           | pending  | `teams/team-p-problem-framing.md`                            |
| 24  | Reframe     | Team E — elimination scan + call-site census                | pending  | `teams/team-e-elimination.md`                                |
| 25  | Reframe     | Team I — invariant discovery                                | pending  | `teams/team-i-invariants.md`                                 |
| 26  | Reframe     | Team W — widening & unification                             | pending  | `teams/team-w-widening.md`                                   |
| 27  | Reframe     | `Reframe.3` principles doc + named principles               | pending  | `bug-{bug_id}-principles.md`                                 |
| 28  | Gate        | **Principles agreed** (adopted / rejected / deferred)       | pending  | terminal output + principle Status fields                    |
| 29  | Design      | Fleet G — guided brainstorm                                 | pending  | rows 29.x appended per adopted principle (`teams/design-g-*.md`) |
| 30  | Design      | Fleet F — free-mind brainstorm (isolated from Reframe)      | pending  | `teams/design-f*-freemind.md`                                |
| 31  | Design      | `Design.2` categorise / merge / roadmap                     | pending  | solutions-doc Roadmaps + Relation graph                      |
| 32  | Design      | Team M — comparison matrix                                  | pending  | `teams/team-m-comparison.md`                                 |
| 33  | Design      | `Design.4` solutions doc                                    | pending  | `bug-{bug_id}-solutions.md`                                  |
| 34  | Gate        | **Option set agreed**                                       | pending  | terminal output                                              |
| 35  | Decide      | `Decide.1` criteria + weights fixed (before reading options)| pending  | evaluation-doc Criteria                                      |
| 36  | Decide      | `Decide.2`/`.3` problem re-check + scoring + recommendation | pending  | `bug-{bug_id}-evaluation.md`                                 |
| 37  | Gate        | **Evaluation reviewed** (user check, before red-pen)        | pending  | terminal output                                              |
| 38  | Decide      | `Decide.5` red-pen on solutions (REVIEW #2)                 | pending  | `bug-{bug_id}-review.md`                                     |
| 39  | Decide      | `Decide.6` review response + discussion loop                | pending  | evaluation-doc Review Response                               |
| 40  | Gate        | **Implementation approved**                                 | pending  | terminal output                                              |
| 41  | Implement   | `Implement.1` impl-skill discovery + user pick              | pending  | Notes (detected set, timestamp, pick per bucket)             |
| 42  | Implement   | `Implement.2`/`.3` implement + commit shape                 | pending  | `firefox/fix/*.patch`                                        |
| 43  | Implement   | `Implement.4` verify proof test FAIL→PASS                   | pending  | `firefox/fix/bug-{bug_id}-verify-run.log`                    |
| 44  | Implement   | `Implement.6` blocking / follow-up triage                   | pending  | `bug-{bug_id}-followups.md`                                  |
| 45  | Consolidate | Doc reconciliation + follow-up filing check                 | pending  | all docs                                                     |
| 46  | Consolidate | Mark run FINISHED                                           | pending  | `Run status` line above                                      |

### Dynamic rows

**Per-hypothesis proof-test rows.** Synthesis (row 15) classifies the hypothesis
tree and appends one row per `to-test` hypothesis under row 16, naming the target
patch, e.g.:

| 16.1 | Diagnose | Validate H1: OOB read in vorbis window function | pending | `firefox/fix/01-test-h1-*.patch`, `firefox/debug/bug-{bug_id}-test-run.log` |

**Third-party Branch rows.** Row 14 (T1/T2/T3) is a *gate*. When T3 resolves
scope, write the scope verdict (`Branch A` / `Branch B` / `Branch C`) into the
Notes section, then append the branch sub-rows under row 14:

- **Branch A (library bug):**
  - `14.1 | Diagnose | A1 library investigation | pending | <library>/...`
  - `14.2 | Diagnose | A2 Firefox regression test | pending | firefox/fix/...`
  - `14.3 | Diagnose | A3 upstream report | pending | <library>/bug-{bug_id}-upstream-<lib>.md`
- **Branch B (Firefox integration):**
  - `14.1 | Diagnose | B1 pivot trace + proof test | pending | firefox/fix/...`
- **Branch C (split scope):** the two-layer rows (library + Firefox traces,
  tests, and upstream report) following A and B patterns.

**Deferred fix work goes under row 42, not row 14.** A4, B2 and C4 happen in the
Implement phase, so they are appended as `42.x` rows at `Implement.2b` time:

- `42.1 | Implement | A4 library fix + vendor + re-verify | pending | <library>/fix/...`

Putting them under 14 would break resume. The table is scanned for the *first*
non-completed row, so a `pending` row 14.4 sitting through Diagnosis Review, four
gates, Reframe, Design and Decide would make every resume in that stretch jump
straight into Implement — before an option had even been chosen. Keep the row order
monotonic in phase.

Recording the scope verdict in Notes lets a resume that halts *after* T3 but
*before* the branch rows are written reconstruct the correct sub-rows. **T1 must
also record**, as named fields in the header block above: library name, upstream
URL, absolute local repo path, vendored revision, and the three library branch
names. Without them a resumed run cannot find the repo it was working in.

**Per-principle guided-brainstorm rows.** The Principles gate (row 28) fixes
which principles are adopted. Append one row per adopted principle under row 29:

| 29.1 | Design | Fleet G — P1 "Validate at the boundary" | pending | `teams/design-g-validate-at-boundary.md` |

**Red-pen iteration rows.** Each re-invocation of red-pen after revisions is a
separate run; the review doc gets a `-N` suffix and both stay on disk. Append a
row per re-run under row 38:

| 38.2 | Decide | red-pen run 2 (after option E appended) | pending | `bug-{bug_id}-review-2.md` |

**Follow-up and blocking rows.** `Implement.6` appends one row per issue found
during implementation:

| 44.1 | Implement | Blocking: {issue} — must land before this bug | pending | Notes + analysis-doc Related Context |
| 44.2 | Implement | Follow-up: {issue} — file after landing | pending | `bug-{bug_id}-followups.md` |

Blocking rows must be resolved (or the run explicitly postponed) before row 45.
Follow-up rows are `completed` when the bug is filed or explicitly handed to the
user — never on a bare "TODO".

### Loop-backs

The Design↔Decide loop is expected. When the Decide phase sends work back:

- **Back to Design** — set rows 31/32/33 to `in-progress`, **append** a new
  option to the solutions doc (never rewrite an existing one), bump its revision
  counter, and log the reason in the solutions-doc Change log *and* in Notes
  below. Gate row 34 returns to `pending`.
- **Back to Reframe** — set row 27 `in-progress` and append a new principle;
  gate row 28 returns to `pending`. Then re-run the Design rows.
- **Back to Diagnose** (reviewer `reject`, or the proof test fails to flip) —
  set the offending Diagnose row `in-progress` and re-run forward from there.
- **After a reverted implementation** — set rows 39/40/42/43 back to `pending`,
  record what was wrong / missing / changed in both the solutions-doc Change log
  and the evaluation-doc Decision log, and take the next-preferred option.

Never delete a row to represent a loop-back. The table is the run's history as
well as its state.

## Notes

(Append-only log of decisions, scope verdicts, skipped-team rationales, user
clarifications, gate outcomes, reviewer loop-backs, discovered-skill sets.)

- {start_timestamp}: created run dir, fetched bug {bug_id}.
