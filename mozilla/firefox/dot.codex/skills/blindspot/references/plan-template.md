# Blindspot run: {slug}

- **Started:** {start_timestamp}
- **Claim:** [`claim.md`](./claim.md)
- **Output directory:** `{abs_output_dir}`
- **Searchfox revision:** `{rev_short}` (full: `{rev_full}`)
- **Working branch:** `blindspot/{slug}` (created on demand in Phase 3)

## How to resume

If this run was interrupted (server unavailable, context exhausted, kill, etc.),
re-invoke blindspot with:

```bash
/blindspot --resume {abs_output_dir}
```

Blindspot reads this file, finds the first `pending` or `in-progress` row, and
continues from there. Completed rows are trusted — the artifacts on disk are the
source of truth. `in-progress` rows are treated as un-finished and re-run; their
output file is overwritten.

## Progress

Statuses: `pending` / `in-progress` / `completed` / `skipped` / `blocked-on-user`.

| #   | Phase | Task                              | Status   | Artifact                                              |
|-----|-------|-----------------------------------|----------|-------------------------------------------------------|
| 1   | 0     | Input intake + plan setup         | pending  | `claim.md`, `plan.md`                                 |
| 2   | 1     | Validity gate                     | pending  | `report.md` (Validity assessment section)             |
| 3   | 1.5   | Investigation plan (plan-mode)    | pending  | harness plan file + Notes section below               |
| 4   | 2     | Team C — Code trace               | pending  | `team-c-code-trace.md`                                |
| 5   | 2     | Team H — Hypothesis brainstorm    | pending  | `team-h-hypotheses.md`                                |
| 6   | 2     | Team D — Design archaeology       | pending  | `team-d-design-archaeology.md`                        |
| 7   | 2     | Team X — Cross-browser & spec     | pending  | `team-x-cross-browser.md`                             |
| 8   | 2     | Team T — Test framework scout     | pending  | `team-t-frameworks.md`                                |
| 9   | 2     | Synthesis (main agent)            | pending  | `synthesis.md`                                        |
| 10  | 3     | Experimental validation           | pending  | rows 10.1, 10.2, … appended per `to-test` hypothesis  |
| 11  | 4     | Draft report                      | pending  | `report.md`                                           |
| 12  | 5     | Reviewer L — Links                | pending  | `review/L.md`                                         |
| 13  | 5     | Reviewer T — Tests                | pending  | `review/T.md`                                         |
| 14  | 5     | Reviewer R — Red-pen              | pending  | `review/R.md`                                         |
| 15  | 6     | Hand off                          | pending  | terminal output                                       |

For Phase 3, Synthesis appends one row per `to-test` hypothesis once the
hypotheses are classified, e.g.:

| 10.1 | 3 | Validate H1: GetImageSize overflows on UINT32_MAX-class crop | pending | `firefox/fix/01-test-h1-*.patch`, `logs/test-h1-*.log` |

## Notes

(Append-only log of decisions, skipped-team rationales, user clarifications.)

- {start_timestamp}: created run dir, claim ingested.
