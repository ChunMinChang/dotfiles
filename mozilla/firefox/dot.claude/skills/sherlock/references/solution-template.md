# Bug {bug_id} — Proposed Solutions

> Produced by the **Design** phase. This document holds the option set and how
> the options relate to each other. It does **not** rank them — ranking is
> `bug-{bug_id}-evaluation.md`, written in the Decide phase, deliberately kept
> separate so the independent reviewer is not anchored by our preference.

- **Bug**: [Bug {bug_id}](https://bugzilla.mozilla.org/show_bug.cgi?id={bug_id})
- **Analysis**: [`bug-{bug_id}-analysis.md`](./bug-{bug_id}-analysis.md)
- **Principles**: [`bug-{bug_id}-principles.md`](./bug-{bug_id}-principles.md)
- **Searchfox revision**: [`{short_hash}`](https://searchfox.org/firefox-main/rev/{full_hash})
- **Revision**: r{n} — bumped every time the Decide phase sends work back here
- **Options**: {count} ({n} guided, {n} free-mind, {n} merged)

## Comparison

> Produced by Team M. Kept at the top so a reader can orient before reading the
> option write-ups.

| Option | Philosophy | Scope | Effort | Risk | Perf | Invariants covered | Blast radius | Uplift-friendly | Test verifiable | Pros | Cons |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A | {P1} | {n files} | L/M/H | L/M/H | {none/±} | I1, I3 | {n call sites} | yes/no | yes/no | {summary} | {summary} |
| B | … | … | … | … | … | … | … | … | … | … | … |

**Blast radius** is taken from the call-site census in the principles doc, not
estimated. **Invariants covered** cites invariant IDs from that same doc.

## Convergence

> Where the guided fleet (which read the principles) and the free-mind fleet
> (which did not) arrived at the same approach independently. Convergence is
> strong evidence; divergence is where the interesting options usually are.

- **Converged**: {approach} — proposed by both {G-agent} and {F-agent}
- **Only guided**: {approaches that required the principles to see}
- **Only free-mind**: {approaches the principles framing would have excluded}

---

## Option A: {name}

- **Provenance**: {guided (principle P1) | free-mind (lens: smallest-change) | merged from A1 + B2}
- **Roadmap position**: {standalone | milestone M2 of roadmap R1}

### Summary
{2–3 sentences. What changes, and what that buys.}

### Core ideas
- {key idea}
- {key idea}

### Design principle
{Which principle from `bug-{bug_id}-principles.md` this realises (P1, P3, …), or —
for a free-mind proposal — the named strategy it follows. One paragraph on *why*
this philosophy fits the problem, not just which one it is.}

### Invariants established
| ID | How this option establishes it | Enforcement | Verification |
|----|--------------------------------|-------------|--------------|
| I1 | {mechanism} | {where} | {assert / type / test} |

{If the option establishes no invariant from the table, say so explicitly and
explain what it does instead — that is a legitimate answer for a pure symptom
fix, but it should be visible.}

### Implementation overview
- **Files touched**: [`path/to/file`]({permalink}), …
- **Order of work**: {1. … 2. … 3. …}
- **Test plan**: {which proof test flips FAIL→PASS; what new coverage is needed}
- **Migration / compat**: {callers to update, prefs, telemetry, staged rollout}

### Pros / Cons
**Pros:** {…}
**Cons:** {…}

---

## Option B: {name}
…

---

## Roadmaps

> Where one option is the natural next step of another. The milestone that fixes
> *this* bug is marked **K**; everything after it becomes a follow-up bug
> candidate and is carried into `bug-{bug_id}-followups.md`.

### Roadmap R1: {name — the through-line}

| Milestone | Option | What it does | Fixes this bug? |
|---|---|---|---|
| M1 | A | {…} | **K — yes** |
| M2 | C | {…} | no — follow-up |
| M3 | D | {…} | no — follow-up |

**Rationale**: {why this is a sequence rather than a set of alternatives —
what M2 depends on from M1.}

## Relation graph

> Categorisation is not mutually exclusive: A may merge with B, and merged AB may
> sit at a milestone of a roadmap that also holds C and D. Record it rather than
> flattening it.

- A **merges with** B → composite option AB
- C **supersedes** E (E is kept for the record; do not delete)
- A **precedes** C on roadmap R1
- D **conflicts with** B — cannot adopt both, because {reason}

## Change log

> Append-only. Every revision, reversal, and redirection lands here — including
> ones that happen after implementation. Never rewrite an earlier entry; add a
> new one.

| Date | Revision | Change | Why |
|---|---|---|---|
| {YYYY-MM-DD} | r1 | Initial option set (A–D) | Design phase |
| {YYYY-MM-DD} | r2 | Added option E | red-pen `pursue-redesign`; reviewer's alternative was not in the original set |
| {YYYY-MM-DD} | r3 | Option A implemented, then reverted | {what was wrong / what was missing / what changed} — moved to option B |
