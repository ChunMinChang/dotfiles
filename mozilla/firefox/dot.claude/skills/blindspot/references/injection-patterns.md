# Fault-injection patterns (LAST RESORT)

End-to-end proof tests must reproduce the user-facing consequence without modifying
the suspect function. When that is genuinely impossible — e.g. the hypothesis
requires allocator OOM at a specific call site, or a compromised IPC peer — a
fault-injection proof is allowed, but only with the safeguards below.

Phase 5's Reviewer T rejects any committed injection that violates these rules.

## When injection is permitted

Exactly one of:

- **Allocator OOM at a specific site.** The hypothesis claims a missing
  null-check after `malloc`/`new`/`MakeUnique`. A benign reproducer would need to
  exhaust process memory, which is too disruptive and unreliable for CI.
- **Compromised IPC peer.** The hypothesis claims a content-process actor can
  send a malformed/oversized message that the parent doesn't validate. A benign
  reproducer would need a real compromised process. Inject by patching the
  serializer to emit the malformed message.
- **Sandbox-internal corruption.** The hypothesis claims a TOCTOU between two
  reads of a shared buffer. A benign reproducer would need adversarial timing.
- **Compiler/optimiser-dependent.** The hypothesis claims UB that
  manifests only with certain optimisation flags. Injection: compile the test
  with the suspect flags.

If none of the above apply, the hypothesis is `lucky-prevented` or
`design-smell-only`, not `to-test`. Reclassify.

## Required safeguards

Every injected patch MUST:

1. **Be gated** behind `#ifdef BLINDSPOT_INJECT_<NAME>` (C++) or
   `#[cfg(blindspot_inject_<name>)]` (Rust). Never modify shipping code paths
   reached without the flag.
2. **Be in a test-only file** (under `dom/.../gtest/`, `testing/`, or similar),
   not in production source. The flag check at a production-source call site is
   acceptable only when the injection point itself has no other home.
3. **Have a justification subsection** in `report.md`:

   ```markdown
   ### Proof method: fault injection

   The hypothesis "<one line>" cannot be reproduced by a benign test because
   <one paragraph naming the specific blocker — e.g., "OOM at this exact
   allocation requires either process-wide memory exhaustion or a compromised
   peer">.

   Injection name: `BLINDSPOT_INJECT_<NAME>`
   Injection site: <file:line> (revision-pinned)
   Injection effect: <one sentence — "forces malloc to return NULL at line X">

   The injection is disabled by default and only activated when running this
   specific test.
   ```

4. **Restore state on teardown** if the injection mutates global/static state.
5. **Be auditable in `git format-patch`** output. The committed patch is what
   the reviewer reads.

## Common patterns

### Forced allocator return

```cpp
#ifdef BLINDSPOT_INJECT_NULL_ALLOC
  // BLINDSPOT_INJECT_NULL_ALLOC: simulate malloc returning NULL at this site
  // to prove the missing-nullcheck hypothesis in <symbol>.
  auto* p = static_cast<T*>(nullptr);
#else
  auto* p = static_cast<T*>(moz_xmalloc(size));
#endif
```

### Forced IPC payload tamper

```cpp
#ifdef BLINDSPOT_INJECT_OVERSIZED_FRAME
  // BLINDSPOT_INJECT_OVERSIZED_FRAME: emit a frame with width=UINT32_MAX
  // to prove the missing-validation hypothesis in <recipient>.
  msg.set_width(UINT32_MAX);
#endif
```

### Forced optimiser/UB-exposing build

No code patch needed; emit a `mozconfig` snippet:

```bash
ac_add_options --enable-optimize="-O3 -fstrict-aliasing"
```

Save to `<run_dir>/firefox/debug/bug-blindspot-mozconfig` and reference it in
the "Proof method: fault injection" section.

## What injection is NOT for

- **Force a specific return value from the suspect function.** That's a
  simulated test. Reject.
- **Skip a check** in the suspect code so the path executes. That's just
  proving the code does what it would do without the check, not proving the
  bug. Reject.
- **Override RNG / time / scheduling** to get specific orderings. If the
  hypothesis is a race, write a stress test that runs many iterations and
  reports the failure rate; reclassify as `design-smell-only` if the rate is
  too low for CI.

## Format-patch checklist before commit

- `grep -r 'BLINDSPOT_INJECT_' <run_dir>/firefox/fix/` returns only the
  expected file(s).
- The "Proof method: fault injection" subsection exists and matches the patch.
- The injection is gated; running the unmodified tree builds cleanly without
  the flag.
- The patch carries the blindspot author via
  `blindspot-config --get-patch-author`.
