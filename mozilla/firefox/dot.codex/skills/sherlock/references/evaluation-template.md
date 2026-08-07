# Bug {bug_id} — Evaluation

> Produced by the **Decide** phase. The Reframe and Design phases deliberately
> ignored cost; this document is where practicality enters. It ranks the options
> in `bug-{bug_id}-solutions.md` and records the reasoning, so a future reader
> can tell what was chosen, what was passed over, and why.

- **Bug**: [Bug {bug_id}](https://bugzilla.mozilla.org/show_bug.cgi?id={bug_id})
- **Analysis**: [`bug-{bug_id}-analysis.md`](./bug-{bug_id}-analysis.md)
- **Principles**: [`bug-{bug_id}-principles.md`](./bug-{bug_id}-principles.md)
- **Solutions**: [`bug-{bug_id}-solutions.md`](./bug-{bug_id}-solutions.md) (r{n})
- **Evaluation date**: {YYYY-MM-DD}

## Criteria

> **Written before reading the options.** Fixing the weights up front is what
> stops the evaluation rationalising a favourite. If a criterion is added or
> reweighted later, log it in the Decision log below with the reason.

| Criterion | Weight | Why this weight, for *this* bug |
|---|---|---|
| Uplift pressure | {1–5} | {sec rating + which branches are affected} |
| Blast radius / regression risk | {1–5} | {from the call-site census} |
| Invariant coverage | {1–5} | {does it make the bug unrepresentable, or patch this instance?} |
| Test verifiability | {1–5} | {can the Diagnose proof test flip FAIL→PASS?} |
| Effort / schedule | {1–5} | {…} |
| Architectural debt paid down | {1–5} | {…} |

### Uplift context

- **Security rating**: {sec-critical / sec-high / sec-moderate / sec-low / not a security bug}
- **Affected branches**: {from Team B's status flags — release, beta, ESR-N, …}
- **Uplift likely?**: {yes / no} — {reasoning}

> When a security bug is likely to be uplifted to shipped or ESR branches, **the
> simplest sufficient fix wins**, and optimisation or cleanup becomes a named
> follow-up on the roadmap. A minimal, obviously-correct, low-blast-radius patch
> is what a branch reviewer can actually approve; the elegant version can land on
> trunk afterwards. Write the reasoning out rather than treating it as obvious —
> and say so explicitly when it does *not* apply.

## Problem re-check

> Confirm nothing in Reframe or Design invalidated the root cause before ranking
> anything against it.

- **Root cause still holds?**: {yes / no — what changed}
- **New evidence since Diagnose**: {…}
- **Consequences for the option set**: {…}

## Scoring

| Option | Uplift | Blast | Invariants | Testable | Effort | Debt | Weighted | Notes |
|---|---|---|---|---|---|---|---|---|
| A | {n} | {n} | {n} | {n} | {n} | {n} | **{total}** | {the one thing that decided it} |
| B | … | … | … | … | … | … | … | … |

Scores are a thinking aid, not an oracle. Where the recommendation departs from
the highest total, say so and explain why — that disagreement is usually the most
informative line in the document.

## Recommendation

1. **First choice — Option {X}**: {why, in two or three sentences}
2. **Second choice — Option {Y}**: {what would make this the pick instead}
3. **Fallback — Option {Z}**: {the conditions under which we drop to this}

### Deferred to follow-up
| Deferred work | From | Roadmap milestone | Follow-up filed |
|---|---|---|---|
| {…} | Option C | R1 / M2 | {bug id or "pending"} |

### Risks accepted
- {risk} — {why it is acceptable, and what would change that}

### Open questions for the user
- {…}

## Review Response

> Filled in after the red-pen review (`bug-{bug_id}-review.md`). The reviewer is
> given the analysis and the solutions doc but **not** this evaluation, so its
> ordering is reached independently of ours. Where the two agree, that is
> corroboration; where they differ, that is the discussion.

- **Verdict**: {approve | approve-with-concerns | revise | reject | redesign | needs-more-info}
- **Headline**: {reviewer's one-sentence finding}
- **Iteration recommendation**: `{accept | revise <option-id> | adopt-alternative | pursue-redesign | escalate}`
- **Review doc**: [`{exact_latest_review_filename}`](./{exact_latest_review_filename})
- **Reviewer's ranking vs ours**: {agreed | differed — how}

| # | Concern | Severity | Accepted? | Response |
|---|---|---|---|---|
| 1 | {…} | critical/important/minor | yes/no | {what changed, or why we disagree} |

**Post-review recommendation**: {unchanged, or the new first choice and why}

> Do not argue with the reviewer in this document. Either apply the concern,
> escalate it to the user, or record an explicit user override with its reasoning.

## Decision log

> Append-only. Covers the Design↔Decide loop and everything after implementation.

| Date | Event | Outcome |
|---|---|---|
| {YYYY-MM-DD} | Criteria fixed | {…} |
| {YYYY-MM-DD} | red-pen run 1 | {verdict} → {action} |
| {YYYY-MM-DD} | Sent back to Design | {why} → solutions r{n+1}, option {new} appended |
| {YYYY-MM-DD} | User approved | Option {X} for implementation |
| {YYYY-MM-DD} | Implementation reverted | {what was wrong / missing / changed} → moved to Option {Y} |
