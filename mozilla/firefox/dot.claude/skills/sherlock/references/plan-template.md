# Sherlock run: bug {bug_id}

- **Started:** {start_timestamp}
- **Bug:** {bug_id} ({public_or_private})
- **Run directory:** `{abs_run_dir}`
- **Searchfox revision:** `{rev_short}` (full: `{rev_full}`)
- **Working branch:** `sherlock/bug-{bug_id}`

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
output file is overwritten. `blocked-on-user` rows (e.g. the Phase Gate) are
re-presented to the user.

**Do NOT re-resolve the Searchfox revision on resume** — it is pinned above and
every link already on disk depends on it. Read it back from this file. Only
`$SHERLOCK_AUTHOR` is re-resolved (it is deterministic).

## Progress

Statuses: `pending` / `in-progress` / `completed` / `skipped` / `blocked-on-user`.

| #   | Phase  | Task                                            | Status   | Artifact                                              |
|-----|--------|-------------------------------------------------|----------|-------------------------------------------------------|
| 1   | Pre    | Setup + intake (config, output dir, rev, fetch) | pending  | `plan.md`, `bug-{bug_id}-report/`                     |
| 2   | 1      | Team B — bug-context digest                     | pending  | `teams/team-b-bug-context.md`                         |
| 3   | 1      | Team H — hypothesis brainstorm (advisory)       | pending  | `teams/team-h-hypotheses.md`                          |
| 4   | 1.2    | Duplicate / related analysis (main agent)       | pending  | analysis-doc Related Context                          |
| 5   | 1.3    | Failure-pattern classification (main agent)     | pending  | analysis-doc Failure Pattern                          |
| 6   | 1.3b   | Investigation plan (EnterPlanMode)              | pending  | harness plan + Notes                                  |
| 7   | 1.3b.5 | Hypothesis tree ≥3 (main agent)                 | pending  | analysis-doc Hypothesis Tree                          |
| 8   | 1.3c   | Firefox working branch                          | pending  | branch `sherlock/bug-{bug_id}`                        |
| 9   | 2      | Team C — Firefox code-trace                     | pending  | `teams/team-c-code-trace-firefox.md`                  |
| 10  | 2      | Team L — library code-trace (if 1.5b)           | pending  | `teams/team-l-code-trace-library.md`                  |
| 11  | 2      | Team D — design archaeology (skip if 1.5b)      | pending  | `teams/team-d-design-archaeology.md`                  |
| 12  | 2      | Team X — cross-browser / spec (skip if internal)| pending  | `teams/team-x-cross-browser.md`                       |
| 13  | 2      | Team T — test-framework scout + draft           | pending  | `teams/team-t-frameworks.md`                          |
| 14  | 1.5b   | Third-party gate (T1/T2/T3 diagnostic)          | pending  | `<library>/debug/` logs + scope verdict in Notes      |
| 15  | Synth  | Synthesis + verdict + root cause (main agent)   | pending  | `teams/synthesis.md`                                  |
| 16  | 1.8/1.9| Proof tests (serialized build + run)            | pending  | rows 16.1, 16.2, … appended per hypothesis (`firefox/fix/`, `firefox/debug/`) |
| 17  | 1.10   | Analysis doc generated                          | pending  | `bug-{bug_id}-analysis.md`                            |
| 18  | 5      | Reviewer L — links / citations                  | pending  | `review/L.md`                                         |
| 19  | 5      | Reviewer T — test re-runner                     | pending  | `review/T.md`                                         |
| 20  | 5      | Reviewer R — red-pen on root cause              | pending  | `review/R.md`                                         |
| 21  | Gate   | Phase Gate (user review)                        | pending  | terminal output                                       |
| 22  | 2      | Solution discussion + red-pen on solutions      | pending  | plan-mode draft + `bug-{bug_id}-review.md`            |
| 23  | 2      | Solutions written to analysis doc               | pending  | analysis-doc Proposed Solutions                       |

### Dynamic rows

**Per-hypothesis proof-test rows.** Synthesis (row 15) classifies the hypothesis
tree and appends one row per `to-test` hypothesis under row 16, naming the target
patch, e.g.:

| 16.1 | 1.8 | Validate H1: OOB read in vorbis window function | pending | `firefox/fix/01-test-h1-*.patch`, `firefox/debug/bug-{bug_id}-test-run.log` |

**Third-party Branch rows.** Row 14 (T1/T2/T3) is a *gate*. When T3 resolves
scope, write the scope verdict (`Branch A` / `Branch B` / `Branch C`) into the
Notes section, then append the branch sub-rows under row 14:

- **Branch A (library bug):**
  - `14.1 | 1.5b | A1 library investigation | pending | <library>/...`
  - `14.2 | 1.5b | A2 Firefox regression test | pending | firefox/fix/...`
  - `14.3 | 1.5b | A3 upstream report | pending | <library>/bug-{bug_id}-upstream-<lib>.md`
  - `14.4 | 1.5b | A4 fix verify (Phase 2) | pending | <library>/fix/...`
- **Branch B (Firefox integration):**
  - `14.1 | 1.5b | B1 pivot trace + proof test | pending | firefox/fix/...`
  - `14.2 | 1.5b | B2 integration fix (Phase 2) | pending | firefox/fix/...`
- **Branch C (split scope):** the two-layer rows (library + Firefox traces,
  tests, and upstream report) following A and B patterns.

Recording the scope verdict in Notes lets a resume that halts *after* T3 but
*before* the branch rows are written reconstruct the correct sub-rows.

## Notes

(Append-only log of decisions, scope verdicts, skipped-team rationales, user
clarifications, reviewer loop-backs.)

- {start_timestamp}: created run dir, fetched bug {bug_id}.
