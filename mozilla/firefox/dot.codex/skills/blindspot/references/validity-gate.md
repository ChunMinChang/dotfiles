# Validity gate

Blindspot Phase 1. Goal: decide as cheaply as possible whether the claim is worth
the full investigation cost. Cannot be delegated — the main agent owns this call.

Everything here is static: `searchfox-cli` plus source-file inspection. No builds,
no tests.

## The framing question

**A bug is a broken invariant.** Before anything else, convert the suspicion into a
property that code either holds or does not:

> *If this claim were true, what would have to be false?*

A claim that cannot be turned into such a proposition is not yet investigable —
not because it is wrong, but because there is nothing to confirm or refute. Stating
the candidate invariant is cheap (it comes from the claim, not from the code) and it
is the sharpest coherence test available, so it comes first.

Write it as a proposition about a named subject:

| Claim | Candidate invariant |
|---|---|
| "`H265SPS::GetImageSize()` can overflow" | *The returned `gfx::IntSize` always equals the true decoded dimensions* |
| "This is missing a nullcheck after `Realloc`" | *Every pointer dereferenced after `Realloc` is non-null* |
| "There's a race on `mLastUpdated`" | *`mLastUpdated` is only read or written on the owning thread* |
| "This deviates from the spec" | *This function implements step N of `<algorithm>` as written* |
| "This code looks fishy" | *(cannot state one — Ambiguous, ask the user)* |

The candidate invariant is a **hypothesis about what the code owes its callers**,
not yet a finding. Team I derives the real invariants — with enforcement points and
verification methods — in Phase 2. The gate only needs the proposition.

## What to check

For each named symbol/file/path in the claim:

1. **Existence.** Run `searchfox-cli --define '<sym>'` (C++/Rust/Java identifiers)
   or `searchfox-cli --path '<glob>'` (file paths). At least one match must come
   back. Record the permalink for the **Validity assessment** section of the
   report.
2. **Signature match.** If the claim asserts a *specific* type-level mechanism
   (e.g. "this returns `int32_t` from a pair of `uint32_t`s"), read the function
   signature and the relevant declarations. Quote the line that confirms or
   refutes the assertion.
3. **Mechanism plausibility.** Map the alleged failure class to the code's
   actual shape:
   - "integer overflow / truncation" → must involve narrowing or unchecked arithmetic.
   - "buffer overflow / OOB read|write" → must involve pointer/index arithmetic on
     a sized buffer; refuse on value types (`nsString`, `std::string`, etc.).
   - "UAF" → must involve raw pointers / weak references / manual lifetime, not
     `RefPtr`/`UniquePtr` unless the claim names a specific path that escapes them.
   - "data race" → must involve mutable shared state across threads; verify the
     class doesn't already document single-threaded use.
   - "spec deviation" → must name (or be matchable to) a specific spec algorithm.
4. **Invariant statement.** Write the candidate invariant as a single proposition,
   naming its subject. If you cannot — because the claim names no property, or names
   one that is not about this code — the claim is Ambiguous or Nonsense, not
   Plausible. Do not proceed on a claim you cannot phrase this way; the whole of
   Phase 2 would have nothing to aim at.
5. **Could it even be violated?** A property that the type system already guarantees
   cannot be broken at runtime. If the candidate invariant is enforced by
   construction — the value is a `CheckedInt`, the field is `const`, the class is
   documented and asserted single-threaded — say so and mark the claim **Nonsense**,
   citing the enforcement. Do not invent a fourth outcome for this case, and do not
   call it `Refuted`: that is a Phase-4 verdict reached on evidence, and reusing the
   word here would make two different things share a name in the same report.

## Outcomes

| Outcome | What it means | Action |
|---|---|---|
| **Nonsense** | One or more named symbols do not exist, OR the mechanism is type-impossible, OR the claim is self-contradictory, OR no invariant can be stated, OR the candidate invariant is enforced by construction. | Write `report.md` with only Verdict (Nonsense), Claim verbatim, the candidate invariant (or why none could be stated), Validity assessment citing what failed, and "What would make it real". **STOP.** |
| **Ambiguous** | Claim is coherent but admits multiple interpretations, or several different invariants would fit it. | Ask the user directly which interpretation to pursue — quote the candidate invariants and let the user choose. Re-run gate. |
| **Plausible** | All symbols resolved, mechanism is type-possible, the invariant is stateable and is *not* enforced by construction. | Proceed to Phase 2 with the candidate invariant as the thing Team I must confirm or refute. Validity assessment still gets written (records what was confirmed). |

## What the gate is NOT

- It is **not** a verdict on whether the bug is real — that's Phases 2–4.
- It does **not** require the gate to prove the bug is impossible to discard the
  claim. "I couldn't find the named symbol" is enough.
- It does **not** decide whether the invariant is actually broken. The gate decides
  whether there is a *stateable* invariant worth testing; Team I finds out whether
  the code holds it.
- It does **not** rely on building Firefox or running tests.

## Quick examples

- **Nonsense (no such symbol).** "`nsString::Length` causes a buffer overflow because
  it returns `size_t`." → `nsString::Length` is a value-returning accessor; "buffer
  overflow" mechanism doesn't apply to a return value. Stop.
- **Nonsense (enforced by construction).** "This size computation can overflow." →
  the operands are `CheckedInt<uint32_t>` and the result is `.isValid()`-checked at
  the only call site. The invariant cannot be broken at runtime. Stop, citing the
  enforcement.
- **Ambiguous (no stateable invariant).** "H264 SPS parsing has an issue." → Which
  property is broken? Parsed values matching the bitstream? Bounds on the field?
  Termination? Ask the user directly and present those candidates.
- **Plausible.** "`H265SPS::GetImageSize()` returns `gfx::IntSize`
  (`int32_t × int32_t`) from a pair of `uint32_t`s, which can overflow." →
  Symbol resolves; signature confirms the narrowing; mechanism is type-possible.
  Candidate invariant: *the returned `IntSize` always equals the true decoded
  dimensions*. Nothing enforces it by construction. Proceed.
