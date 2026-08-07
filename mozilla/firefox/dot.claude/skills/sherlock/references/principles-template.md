# Bug {bug_id} — Design Principles

> Produced by the **Reframe** phase. Read `references/first-principles.md` for
> the method. This document states what must be **true**; it does not propose
> patches. Concrete approaches live in `bug-{bug_id}-solutions.md`.

- **Bug**: [Bug {bug_id}](https://bugzilla.mozilla.org/show_bug.cgi?id={bug_id})
- **Analysis**: [`bug-{bug_id}-analysis.md`](./bug-{bug_id}-analysis.md)
- **Searchfox revision**: [`{short_hash}`](https://searchfox.org/firefox-main/rev/{full_hash})
- **Reframe date**: {YYYY-MM-DD}
- **Broken invariant (from Diagnose)**: {the one-sentence statement carried over from the analysis doc}

## Q1 — Why is this a problem?

- **Guarantee broken**: {stated as a proposition}
- **Who relies on it**: {end user / web content / spec / internal caller / security boundary / maintainer}
- **Concrete harm**: {memory unsafety / wrong output / hang / API confusion / maintenance trap}
- **Harm class**: {correctness | security | performance | maintainability}
- **If never fixed**: {who notices, and how}

## Q2 — Why do we have this problem in the first place?

- **Origin category**: {missing contract | contract drift | layering violation | representable illegal state | duplicated path | lapsed purpose | defensive accretion}
- **The decision**: {commit hash / bug / the specific absence} — [`link`]({permalink})
- **What made it reasonable at the time**: {constraints the author faced}
- **What changed since**: {the event that invalidated it}

## Q3 — Elimination candidates

> Deletion is a first-class proposal. Every "no callers" claim needs a citation.

### E1: {what would be removed}
- **Reachability**: {live callers / tests only / dead branch} — evidence: [`census`](#call-site-census)
- **Superseded by**: {newer mechanism, or "nothing"}
- **Premise still true?**: {yes/no — platform, pref, codec, build config}
- **Deleting it deletes the bug?**: {yes / partially / no}
- **Also deletes**: {other behaviour that would go with it}
- **Confidence**: {high / medium / low} — {why}
- **Uplift-safe?**: {usually no — state the blast radius}

### Call-site census

> Produced by Team E, reused by Design's implementation overviews and Decide's
> blast-radius scoring. One grep, three consumers.

| Symbol | Call sites | Files | Notes |
|---|---|---|---|
| `{symbol}` | {n} | [`file:line`]({permalink}), … | {who depends on the current narrow contract} |

## Q4 — Invariants

> An invariant with no enforcement point and no verification method is a wish.
> Demote it to Open Questions.

| ID | Subject | Statement | Enforcement point | Verification | Current violation | Fixes / Prevents / Avoids | Strength |
|----|---------|-----------|-------------------|--------------|-------------------|---------------------------|----------|
| I1 | `{Class::method}` | {always true of it} | {ctor / factory / type / single entry point} | {type \| MOZ_ASSERT \| MOZ_DIAGNOSTIC_ASSERT \| static_assert \| test} | [`file:line`]({permalink}) | {which} | {unrepresentable \| enforced-at-one-point \| asserted \| checked-and-handled} |
| I2 | … | … | … | … | … | … | … |

**Strength** is the ranking from `first-principles.md`, strongest first. An
invariant that holds only because every caller remembers to maintain it is the
weakest form — record it as `checked-and-handled` and say so rather than rounding up.

### Demoted candidates
> Invariants missing an enforcement point or a verification method. They are not
> invariants yet, but they are worth keeping visible — one of them usually becomes
> real once a Design option gives it somewhere to live.

| Candidate | Subject | What it lacks |
|---|---|---|
| {statement} | `{symbol}` | {no enforcement point \| no verification method \| both} |

## Q5 — Widening opportunities

> Only valid when (a) a reliable result exists for the newly-accepted inputs and
> (b) downstream handling is predictable and controllable.

### W1: {which contract would widen}
- **Currently rejects**: {inputs / states}
- **Proposed accepted domain**: {what it would additionally accept}
- **(a) Reliable result**: {the defined answer for each new input}
- **(b) Downstream handling**: {error report / callback / return path, and how it is tested}
- **Guards that collapse**: [`file:line`]({permalink}), …
- **Paths that unify**: {the special case and general case that merge}
- **Callers that simplify**: {which stop pre-validating}
- **Security counter-case**: {does this move validation off a security boundary? If yes, do not widen — say so here}

## Designed today

> Direction, not a rewrite proposal. Migration cost deliberately ignored.
> The point is that the chosen fix should be a step *toward* this shape.

{Sketch of what this subsystem would look like if built today. Explicitly a sketch.}

## Design principles

> 2–5 named strategies. These are not competing options — they are the criteria
> the Design phase builds against. Multiple may be adopted at once.

### P1: {short memorable name}
- **Statement**: {one or two sentences}
- **What it buys**: {which failure classes it closes, beyond this bug}
- **What it costs**: {performance, churn, risk, review burden — state it honestly}
- **Implies**: {invariant IDs, elimination candidates}
- **Status**: {adopted | rejected | deferred} — {user decision at the gate}

### P2: {name}
…

## Open questions

- {Candidate invariants demoted for lacking an enforcement point or verification method}
- {Claims that could not be verified — labelled `[Assumption]` with what would confirm them}
