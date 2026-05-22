# Blindspot report: {slug}

## Verdict

Value: `Confirmed` | `Lucky-prevented` | `Design-smell-only` | `Refuted` | `Nonsense`.

{One-sentence reason, naming the strongest hypothesis or the strongest counter-
evidence.}

## Claim (verbatim)

> {Paste claim.md contents here, unedited.}

## Validity assessment

- **Symbols resolved:** {list with permalinks, e.g. `H265SPS::GetImageSize` at
  [`H265.cpp#L<n>`](https://searchfox.org/firefox-main/rev/{rev}/dom/media/...#L<n>)}
- **Signature confirms mechanism:** {Yes / No, with quoted line}
- **Mechanism type-possible:** {Yes / No, with reason}
- **Coherence:** {Concrete failure mode named: ...}
- **Gate outcome:** {Plausible / Ambiguous-then-clarified / Nonsense}

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

| # | Hypothesis | Predicted signal | Status | Rationale |
|---|---|---|---|---|
| 1 | {one line} | {observable} | Confirmed/Lucky-prevented/Refuted/Smell-only | {one line, cite evidence} |
| 2 | ... | ... | ... | ... |

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
> [`injection-patterns.md`](../../skills/blindspot/references/injection-patterns.md).
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

- **Reviewer L (links):** {pass / fail — link to `review/L.md`}
- **Reviewer T (test re-run):** {pass / fail — link to `review/T.md`}
- **Reviewer R (red-pen):** {accept / revise / redesign / reject / needs-more-info
  — link to `review/R.md`}
