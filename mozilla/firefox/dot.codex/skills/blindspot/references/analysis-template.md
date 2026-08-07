# Blindspot report: {slug}

- **Searchfox revision:** [`{rev_short}`](https://searchfox.org/firefox-main/rev/{rev})
  — every code link below is pinned to this revision.

## Verdict

Value: `Confirmed` | `Lucky-prevented` | `Unreachable` | `Design-smell-only` |
`Refuted` | `Nonsense`.

{One sentence, phrased as the invariant's state: which property is at stake, whether
the code holds it, and — if not — whether the break is reachable and what follows.
Name the strongest hypothesis or the strongest counter-evidence.}

## Claim (verbatim)

> {Paste claim.md contents here, unedited.}

## Validity assessment

- **Symbols resolved:** {list with permalinks, e.g. `H265SPS::GetImageSize` at
  [`H265.cpp#L<n>`](https://searchfox.org/firefox-main/rev/{rev}/dom/media/...#L<n>)}
- **Signature confirms mechanism:** {Yes / No, with quoted line}
- **Mechanism type-possible:** {Yes / No, with reason}
- **Coherence:** {Concrete failure mode named: ...}
- **Candidate invariant stateable:** {Yes, see Invariant below / No — why}
- **Enforced by construction:** {No / Yes — cite the enforcement, which makes this Nonsense}
- **Gate outcome:** {Plausible / Ambiguous / Nonsense} {if Ambiguous, add: — clarified to: …}

## Invariant

> The property this code owes its callers, and whether it holds. The candidate is
> written at the validity gate from the claim alone; the rest is filled from Team I
> after Phase 2. The verdict above is this section's summary — if the two disagree,
> one of them is wrong.
>
> **On the Nonsense short-circuit** the run stops at the gate, so only the candidate
> line below is filled — state it, or state why no invariant could be phrased at all.
> Delete the table and the two subsections; there is no Team I output to fill them.

**Candidate invariant** (from the gate): {one proposition about a named subject}

| ID | Subject | Statement | Source | Enforced by | Holds? | Violation site |
|----|---------|-----------|--------|-------------|--------|----------------|
| I1 | `{symbol}` | {proposition} | {asserted \| documented \| spec \| commit-intent \| inferred-from-callers} | {type / ctor / assertion / caller check / **nothing**} | {holds \| broken \| holds-only-by-convention} | [`file:line`]({permalink}) |

**Source** matters: an invariant the author wrote down is a stronger basis for calling
something a bug than one inferred from what callers happen to do. Say which you have.

### Reachability
> Only for broken invariants. A violation nothing can reach is a real finding, but a
> different one from a violation web content can drive.

- **Reachable by**: {web content / compromised content process / internal callers only / nothing}
- **Call sites**: [`file:line`]({permalink}), …
- **Evidence**: {the search that established the above}

### Sibling saves
> What restores the property before anything observable happens, if anything.

- **Saved by**: [`check`]({permalink}) — {what it does}, or "nothing found — searched {X}, {Y}, {Z}"
- **Would become real if**: {the change that removes the save}

## What would make it real

> Required on the **Nonsense** path, optional elsewhere. The claim was rejected; say
> what would have to be different for it to hold — a caller that reaches the path, a
> type that stopped being checked, a platform where the guard is compiled out. This is
> the part a reader comes back to when the code changes, so be specific rather than
> writing "if the check were removed".

- **What was missing:** {the symbol that did not exist / the enforcement that makes it unbreakable / the interpretation that could not be pinned down}
- **Would become investigable if:** {the concrete change}

## Suspect code

[`{symbol}`](https://searchfox.org/firefox-main/rev/{rev}/{path}#L{n}) —
{one-line description}.

```cpp
{Optional short excerpt (≤8 lines) showing the narrowing/check/whatever is
under suspicion. Pin to revision.}
```

## Original design intention

> From Team D archaeology. All claims here are evidence-based citations of
> commits or comments, not inferences about current correctness.

- **Introducing commit:** `{hash}` ([Bug {bug-id}]({bz-link})) — {one-line
  message}
- **Original purpose:** {What the author was solving}
- **Design rationale:** {Cite commit message or bug discussion}
- **Function contract:** {Preconditions, postconditions, invariants, threading
  model, ownership}
- **Drift signals:** {followup commits, workaround comments, dead branches}
- **How the claim relates:** {Main-agent synthesis: violates the contract /
  reveals a gap / drifts from intent / orthogonal to original purpose}

## Hypothesis table

> Every Team H hypothesis with its final status.

| # | Hypothesis | Invariant | Predicted signal | Status | Rationale |
|---|---|---|---|---|---|
| 1 | {one line} | I1 | {observable} | Confirmed / Lucky-prevented / Unreachable / Design-smell-only / Refuted | {one line, cite evidence} |
| 2 | ... | ... | ... | ... | ... |

Every hypothesis names the invariant it would violate. One that maps to no invariant
is not a hypothesis — either find the property it implies, or refute it.

## Confirmed consequences

> One subsection per Confirmed hypothesis.

### Confirmed — {Hypothesis N}: {one line}

- **User-visible impact:** {what a user/site sees — wrong video dimensions,
  decode error swallowed, crash signature, etc.}
- **Code path:**
  1. [`{Caller}`]({permalink}#L{n}) — {what it does}
  2. [`{Callee}`]({permalink}#L{n}) — {where the defect manifests}
  3. ...
- **Proof test:** [`firefox/fix/01-test-{desc}.patch`](./firefox/fix/01-test-{desc}.patch)
  ([log](./logs/test-{hypothesis}.log))
- **Verified claims:** {bullet list of evidenced statements}
- **Assumptions:** {`[Assumption]` items with "would-confirm/refute" lines}

#### Proof method: fault injection

> Include this subsection ONLY for injected proofs. See
> the blindspot skill's `references/injection-patterns.md` (this report lives in the
> run dir, so it is deliberately named rather than linked — every other link here is
> run-dir-relative).
> Reviewer T rejects committed injection patches lacking this section.

- **Reason a benign reproducer is impossible:** {one paragraph}
- **Injection name:** `BLINDSPOT_INJECT_{NAME}`
- **Injection site:** {file:line, revision-pinned}
- **Injection effect:** {one sentence}
- **Disabled by default:** {Yes — flag only enabled for this test}

## Lucky-prevented consequences

> One subsection per Lucky-prevented hypothesis.

### Lucky-prevented — {Hypothesis N}: {one line}

- **What the saving check is:** {short description}
- **Where it lives:** [`{symbol}`]({permalink}#L{n})
- **What it does:** {how it neutralises the hypothesised input range}
- **Would-become-real-if:** {trigger that would defeat the saving check}
- **Test that demonstrates the save:** {patch path or "n/a — read-only
  observation"}

## Unreachable violations

> One subsection per Unreachable hypothesis: the invariant really is broken, but
> nothing can currently reach the violating path. Worth reporting — the code is wrong
> and the next caller may not be so lucky — but it is not a consequence, and writing
> it up as one wastes a reviewer's time.

### Unreachable — {Hypothesis N}: {one line}

- **Invariant broken:** {ID + statement}
- **Violation site:** [`{symbol}`]({permalink}#L{n})
- **Why nothing reaches it:** {dead branch / no live callers / gated by a pref that
  no longer ships / platform never built}
- **Evidence:** {the call-site census that establishes this}
- **Would become real if:** {the caller that would make it reachable}

## Design-smell / footgun

> One subsection per Design-smell-only hypothesis, plus general code-smell
> observations from Team C even when no hypothesis was triggered.

- **What is fragile:** {one line}
- **Why it could become real:** {trigger conditions}
- **Suggested follow-up:** {one line — no fixes, just a pointer for whoever
  files the bug}

## Cross-browser & spec

> From Team X. Skip if no web surface; if skipped, say so here.

- **Spec section:** {URL + section, or "no spec — internal helper"}
- **Existing WPT coverage:** {paths or "none"}
- **Notable divergence:** {one line, or "none"}

Behaviour table:

| Engine | Behaviour | Source |
|---|---|---|
| Firefox | ... | [`...`]({permalink}) |
| Chrome | ... | {chromium link or "observed via playwright"} |
| Safari | ... | {webkit link or "not tested"} |

## Test artifacts

| File | Purpose |
|---|---|
| [`firefox/fix/01-test-{desc}.patch`](./firefox/fix/01-test-{desc}.patch) | Proof test for Hypothesis N |
| [`logs/build-{hypothesis}.log`](./logs/build-{hypothesis}.log) | Build output |
| [`logs/test-{hypothesis}.log`](./logs/test-{hypothesis}.log) | Test run output |
| [`firefox/debug/`](./firefox/debug/) | Investigation-only patches (NOT FOR LANDING) |

## Suggested follow-ups

- {one-line suggestions only — no fixes. e.g., "file as media/playback bug,
  attach this report"; "consider hardening the conformance-window clamp to
  reject non-power-of-two crops"; "WPT coverage missing for X — file separate
  WPT bug".}
- **Next skill:** `{/triage <component> | /sherlock <bug-id> once filed |
  /firefox-implementation if jumping straight to fix}`

## Review

> Reviewer R challenges the Invariant section first — if the stated property is not
> really owed, the rest of the report is decoration. Full red-pen review:
> [`review/blindspot-claim-review.md`](./review/blindspot-claim-review.md)

- **Reviewer L (links):** {pass / fail — link to `review/L.md`}
- **Reviewer T (test re-run):** {pass / fail — link to `review/T.md`}
- **Reviewer R (red-pen):** {approve / approve-with-concerns / revise / reject /
  redesign / needs-more-info — link to `review/R.md`}
