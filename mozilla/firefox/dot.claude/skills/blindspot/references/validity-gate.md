# Validity gate

Blindspot Phase 1. Goal: decide as cheaply as possible whether the claim is worth
the full investigation cost. Cannot be delegated — the main agent owns this call.

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
4. **Coherence.** The claim describes a concrete failure mode with a guessed user-
   visible signal. Vague claims ("looks fishy", "could be wrong") need
   clarification.

## Outcomes

| Outcome | What it means | Action |
|---|---|---|
| **Nonsense** | One or more of the named symbols do not exist, OR the mechanism is type-impossible, OR the claim is self-contradictory. | Write `report.md` with only Verdict (Nonsense), Claim verbatim, Validity assessment citing what failed, and "What would make it real". **STOP.** |
| **Ambiguous** | Claim is coherent but admits multiple interpretations. | `AskUserQuestion` to pin down which interpretation. Re-run gate. |
| **Plausible** | All symbols resolved, mechanism is type-possible, claim is concrete. | Proceed to Phase 2. Validity assessment still gets written (records what was confirmed). |

## What the gate is NOT

- It is **not** a verdict on whether the bug is real — that's Phases 2–4.
- It does **not** require the gate to prove the bug is impossible to discard the
  claim. "I couldn't find the named symbol" is enough.
- It does **not** rely on building Firefox or running tests. All checks are
  static, via `searchfox-cli` + `Read`.

## Quick examples

- **Nonsense.** "`nsString::Length` causes a buffer overflow because it returns
  `size_t`." → `nsString::Length` is a value-returning accessor; "buffer
  overflow" mechanism doesn't apply to a return value. Stop.
- **Ambiguous.** "H264 SPS parsing has an issue." → Which field? Which step?
  AskUserQuestion.
- **Plausible.** "`H265SPS::GetImageSize()` returns `gfx::IntSize`
  (`int32_t × int32_t`) from a pair of `uint32_t`s, which can overflow." →
  Symbol resolves; signature confirms the narrowing; mechanism is type-possible.
  Proceed.
