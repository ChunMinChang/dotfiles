# Bug {bug_id} — Follow-ups and Blocking Issues

> Created at `Design.4` seeded with the roadmap milestones after the fix milestone
> **K**, then appended to during `Implement.6`. Verified at Consolidate: **every row
> must end with a real bug id or an explicit "handed to user"** — a row left as
> "TODO" blocks the run from being marked FINISHED.
>
> Created in Design rather than Implement on purpose: a run that stops at the Decide
> gate (the user takes the docs and implements it themselves) still hands over the
> follow-up list.

- **Bug**: [Bug {bug_id}](https://bugzilla.mozilla.org/show_bug.cgi?id={bug_id})
- **Solutions**: [`bug-{bug_id}-solutions.md`](./bug-{bug_id}-solutions.md)

## Blocking

> Must land **before** this bug. Each one also gets a row `44.x` in `plan.md` and a
> note in the analysis doc's *Related Context*. Surface these to the user as soon as
> they are found — they are a scheduling decision, not an end-of-run detail.

| # | Issue | Why it blocks | Discovered at | Status |
|---|---|---|---|---|
| B1 | {what} | {what breaks if we land without it} | `Implement.2` | {filed as Bug NNN \| handed to user \| resolved in-run} |

If a blocking issue cannot be resolved inside this run, set its plan.md row
`blocked-external` and expect Consolidate to close the run as **POSTPONED**.

## Follow-ups

> Can land **after** this fix. Reported together at the end of the run, not
> interrupting the user mid-implementation.

| # | Item | Why deferred | Source | Status |
|---|---|---|---|---|
| F1 | {what} | {simplest-fix-for-uplift \| out of scope \| needs its own design} | roadmap R1 / M2 | {filed as Bug NNN \| handed to user} |
| F2 | Submit the fix upstream to {library} | Upstream review is out of band | Branch A / A3 | {…} |

**Source** should name where the item came from — a roadmap milestone, a red-pen
concern that was accepted-but-deferred, an evaluation "deferred to follow-up" entry,
or something implementation turned up. That provenance is what lets a reader tell a
deliberate deferral from an oversight.

## Security note

For a `sec-*` bug, follow-ups may not describe the vulnerability. Reference the
parent bug id and describe the work in neutral terms ("harden input validation in
X"), and file the follow-up in the same security group unless it is genuinely
independent of the flaw.
