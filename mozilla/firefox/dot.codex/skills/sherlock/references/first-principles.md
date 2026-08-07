# First-principles toolkit (Reframe phase)

Diagnose answers **why the bug happens**. Reframe answers **what must be true so
that it cannot happen**. These are different questions, and the second one is
where the leverage is.

The failure mode this phase exists to prevent: reading a root cause and
immediately writing the smallest patch that suppresses the symptom. That patch
is often correct and still wrong — it leaves the shape of the code that produced
the bug intact, so the next bug of the same family is already scheduled.

**Reframe produces principles, invariants, and elimination candidates. It never
produces patches.** Concrete approaches are the Design phase's job.

---

## The five questions

Work them in order. Each one can make the later ones unnecessary.

### Q1. Why is this a problem?

Not "what goes wrong" — Diagnose answered that. *Why does it matter, and to
whom?*

- Which **guarantee** is broken? Name it as a proposition: "a decoded frame's
  dimensions always match the ones negotiated at init", not "the sizes differ".
- **Who relies on that guarantee?** End user, web content, the spec, a caller
  inside Gecko, a security boundary, a future maintainer. Each has a different
  remedy.
- What is the **concrete harm**? Memory unsafety, wrong pixels, a hang, a
  confusing API, a maintenance trap. Harm class drives urgency and therefore the
  Decide phase's weighting.
- Would anyone notice if it were **never** fixed? If the honest answer is no,
  say so — that is a legitimate finding and it changes the whole conversation.

### Q2. Why do we have this problem in the first place?

Bugs are rarely typos. Something *permitted* this.

Look for the specific origin:

| Origin | Signature | Typical remedy direction |
|---|---|---|
| **Missing contract** | The function never said what it required; callers guessed | State and enforce an invariant |
| **Contract drift** | The contract was true when written; a later change invalidated it | Re-establish, or widen the contract to cover the new reality |
| **Layering violation** | The caller knows something it should not, or vice versa | Move the check to the layer that owns the knowledge |
| **Representable illegal state** | The type system allows a value that is never valid | Make it unrepresentable |
| **Duplicated path** | Two code paths that must agree, don't | Unify |
| **Lapsed purpose** | The code solves a problem that no longer exists | Delete (see Q3) |
| **Defensive accretion** | Layers of guards added by successive bugs, none removed | Collapse to one invariant |

Team D's design archaeology and Team P's history trail are the evidence here.
Name the *decision* — a commit, a bug, an absence — not a vague "technical debt".

### Q3. Does this code still deserve to exist?

The cheapest fix is deletion. Sometimes a piece of code has quietly lost its
purpose and the bug is the first time anyone looked at it in years.

Ask:
- Is it **reachable**? Any live callers, or only tests and dead branches?
- Has it been **superseded**? A newer mechanism may already do this job, with the
  old path surviving only as a fallback nobody exercises.
- Is its **premise still true**? Code written for a platform, a pref, a codec, or
  a build configuration that no longer ships is not a fix candidate — it is a
  removal candidate.
- Is it a **workaround** for a bug that has since been fixed upstream?
- Would deleting it delete the bug, and what else would it delete?

Deletion is a real proposal and belongs in the principles doc with the same rigor
as any other. It needs the call-site census as evidence — a "no callers" claim
without a searchfox or grep citation is not evidence, and Team E's contract
requires the citation.

Two honest constraints on deletion: it is usually *not* an uplift candidate (too
much blast radius for a shipped branch), and it may be the milestone-N end of a
roadmap whose milestone-1 is a small guard. Both are fine — record it, and let
the Decide phase sequence it.

### Q4. What invariant must hold?

This is the core of the phase. For each function, method, field, or class on the
failing path, state the property that — if it always held — would make this bug
**impossible** rather than **handled**.

An invariant is only real if it has all four of these. Anything missing one is a
wish; write it down as an open question instead of promoting it.

| Part | Question it answers |
|---|---|
| **Subject** | Which symbol does this bind? |
| **Statement** | What is always true of it, phrased as a proposition? |
| **Enforcement point** | Where does it become true, and stay true? Constructor, factory, type, setter, single entry point? |
| **Verification method** | How would we *know* it holds? Type, `MOZ_ASSERT`, `MOZ_DIAGNOSTIC_ASSERT`, `static_assert`, release check, test? |

Also record, per invariant:
- The **current violation site** — where today's code breaks it.
- Whether it **fixes** (repairs the identified cause), **prevents** (stops the
  cause arising), or **avoids** (routes around it).

Prefer, in this order:

1. **Unrepresentable** — the type makes the bad state impossible. No runtime cost,
   no way to forget. A `struct` that cannot be constructed in an invalid state
   beats a check every caller must remember.
2. **Enforced at one point** — a single constructor, factory, or entry point
   establishes it. One place to audit.
3. **Asserted** — `MOZ_DIAGNOSTIC_ASSERT` catches violations in Nightly and
   early Beta without a release cost.
4. **Checked and handled** — a runtime branch. Necessary for untrusted input;
   a smell for internal callers, because it means the invariant is not actually
   an invariant.

An invariant that can only be maintained by every caller remembering to do
something is the weakest form. Say so when that is the best available.

### Q5. Can we widen instead of narrow?

The reflex when input breaks a function is to reject that input harder. The
opposite move is often better: **extend the contract to accept it.**

Widening is justified only when both hold:

- **(a) A reliable result exists.** There is a well-defined, correct answer for
  the newly-accepted inputs — not a guess, not a silent default that papers over
  a caller bug.
- **(b) Downstream handling is predictable and controllable.** The error report,
  callback, or return path for the new cases is explicit and testable.

When both hold, widening tends to pay compound interest:
- **Redundant checks collapse.** Guards that existed only to keep inputs inside
  the old narrow domain can go.
- **Code paths unify.** The special case and the general case become one path,
  so they can no longer disagree — which is often the actual bug family.
- **Callers simplify.** Every caller that was pre-validating stops needing to.

Team W must name, concretely: which guards collapse, which paths unify, and what
the defined result is for each newly-accepted input. "We could be more permissive"
is not a proposal.

The counter-case is real and must be stated when it applies: widening a function
that sits on a security boundary moves validation away from the boundary. If the
narrow domain *is* the security property, say so and do not widen.

---

## Designing today

After Q1–Q5, sketch the answer to: **if this subsystem were designed today,
knowing what we now know, what would it look like?**

Ignore migration cost entirely. The point is not to propose a rewrite; it is to
establish the direction, so that the fix chosen in Decide is a step *toward* that
shape rather than away from it. A small fix that moves toward the right model is
worth more than an equally small fix that entrenches the wrong one.

Record it as a sketch, explicitly labelled as such.

---

## From questions to principles

The principles doc closes with **2–5 named design principles**. A principle is
the reusable strategy behind one or more invariants and elimination candidates —
the thing a reader could apply to a *different* bug in the same subsystem.

Each principle needs:
- **Name** — short and memorable, e.g. "Validate at the boundary, trust within",
  "One source of truth for frame geometry", "Delete the fallback".
- **Statement** — one or two sentences.
- **What it buys** — which failure classes it closes, not just this bug.
- **What it costs** — performance, churn, risk, review burden. Name it honestly;
  Decide will weigh it, and an unstated cost reads as a hidden one.
- **Implies** — which invariant IDs and elimination candidates follow from it.

**Multiple principles may be adopted at once.** They are not competing options —
they are the criteria that the Design phase's options will be built against and
that the Decide phase will score against. Competing *options* come later.

---

## Rules for this phase

1. **No patches.** If you catch yourself writing a diff, you are in the wrong
   phase. Write the invariant that the diff would establish instead.
2. **Cost is not an argument here.** "Too big", "the reviewer will object", "we'd
   never land that" — all out of scope. Revamping the architecture is on the
   table. Practicality is the Decide phase's job, and it does that job badly if
   Reframe has already pre-filtered the space.
3. **Evidence, same as Diagnose.** The two-tier rule still applies: every claim is
   Verified with a citation or labelled `[Assumption]`. A first-principles phase
   is not a licence to speculate.
4. **Name the origin, not the vibe.** "Technical debt" and "legacy code" are not
   answers to Q2.
5. **Deletion is a first-class proposal**, not a throwaway remark.
6. **An invariant without an enforcement point and a verification method is not
   an invariant.** Demote it to an open question.
