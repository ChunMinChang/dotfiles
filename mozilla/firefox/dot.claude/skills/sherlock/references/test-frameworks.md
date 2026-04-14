# Test Framework Reference

## Framework Selection Decision Tree

```
Is it a crash bug?
├── YES: Can it be triggered from HTML/JS?
│   ├── YES → Crashtest (dom/media/crashtests/ or testing/crashtest/)
│   └── NO → GTest (dom/media/gtest/)
└── NO: Is it web-exposed behavior?
    ├── YES: Is it defined in a web specification?
    │   ├── YES → WPT (follow references/spec-check.md first)
    │   │         Location: testing/web-platform/tests/
    │   └── NO → Mochitest (dom/media/test/)
    └── NO: Internal C++/Rust?
        ├── YES → GTest (dom/media/gtest/)
        └── Mochitest for integration testing (dom/media/test/)
```

## Test Locations

| Framework | Location | When to Use |
|-----------|----------|-------------|
| WPT | `testing/web-platform/tests/` | Spec-defined web behavior |
| Mochitest | `dom/media/test/` (or component-specific) | Firefox-specific behavior |
| GTest | `dom/media/gtest/` | C++ unit tests |
| Crashtest | `dom/media/crashtests/` or `testing/crashtest/` | Crash reproduction |

## When NOT to Write a Test

Skip the test entirely when:
- **Data race / threading issue** with narrow, platform-gated race window. Mochitests
  are probabilistic and will be flaky, adding CI noise without trustworthy regression guard.
- **Code not exercisable from JS** in standard CI configuration (gated by `#ifdef` or
  Windows-only pref that CI doesn't enable).
- **Detection rate** in a typical CI run would be well below 50%.

**Crashtest acceptable (~50% detection) when:**
- Bug causes an **outright crash** (not just memory corruption) in normal CI builds
- Can run on the platforms where the crash actually occurs
- Cheap to write (a simple HTML page that triggers the crash path)

If no test is written, document the rationale in the analysis doc's Test Evidence section.

## Proof Tests vs TDD Tests

In sherlock, tests serve as **proof of root cause**:
- Must FAIL without fix (proving the bug exists)
- Designed to PASS after fix (making them reusable for TDD)
- The test is EVIDENCE for the root cause claim, not just a regression guard
- Run tests after creation to verify analysis claims with debugging logs

## FuzzingFunctions → SpecialPowers Mapping

When a bug-attached testcase uses `FuzzingFunctions.*`, it cannot run in CI as-is
(`fuzzing.enabled = true` required). Perform a per-call analysis:

| `FuzzingFunctions` call | SpecialPowers / plain-JS equivalent | Notes |
|---|---|---|
| `FuzzingFunctions.gc()` | `SpecialPowers.exactGC()` (async) | `exactGC` is more reliable than `forceGC` |
| `FuzzingFunctions.cycleCollect()` | `SpecialPowers.forceCC()` | Synchronous |
| `FuzzingFunctions.memoryPressure()` | `SpecialPowers.gc()` + observer | Approximate only |
| `FuzzingFunctions.spinEventLoopFor(ms)` | `await new Promise(r => setTimeout(r, ms))` | Exact |
| Custom IPC-triggering calls (e.g. `mediaSystemResourceStorm`) | **Requires C++ analysis** | Read the C++ implementation; check if the IPC path is reachable from content JS. If it requires direct `ImageBridgeChild` calls or other non-JS infrastructure, it cannot be adapted. |

### Decision Rule

- If **ALL** `FuzzingFunctions` calls have SpecialPowers/JS equivalents **AND** the
  equivalent triggers the same code path → write a mochitest/crashtest using them.
- If **ANY** call requires internal C++ IPC APIs unreachable from JS content → the
  testcase cannot be adapted. Document: which call blocks adaptation, what C++ API
  it needs, and why no JS equivalent exists.

### Per-Call Analysis (Required)

For each `FuzzingFunctions.*` call in the testcase:
1. What does this call actually do? Read the `FuzzingFunctions.cpp` implementation.
2. Is there a SpecialPowers or plain-JS equivalent?
3. Does the equivalent reproduce the bug? (Same IPC/JS code path?)

This analysis MUST appear in the analysis doc's Test Evidence section.

## Mozconfig Presets for Sanitizer Builds

### Check Normal Build First

Before requiring ASan/TSan, try these builds in order:
1. **Current build** — try reproducing with whatever is already built
2. **Standard debug build** — `ac_add_options --enable-debug`
3. **ASan or TSan** — only if the above don't reproduce

Signals that a sanitizer build is needed:
- Bug title/comments contain "data race", "race condition" → **TSan**
- Bug title/comments contain "heap-use-after-free", "buffer-overflow", "stack-buffer-overflow", ASan signature → **ASan**
- Bug report explicitly mentions ASan/TSan output
- Crash signature contains sanitizer frames

### ASan Optimized Build (Linux/macOS/Windows)

```bash
# ASan optimized build configuration
mk_add_options MOZ_OBJDIR=@TOPSRCDIR@/obj-asan

ac_add_options --enable-address-sanitizer
ac_add_options --disable-jemalloc
ac_add_options --disable-crashreporter
ac_add_options --disable-elf-hack
ac_add_options --disable-profiling
ac_add_options --disable-install-strip
ac_add_options --enable-debug-symbols=-gline-tables-only
# Linux only: ac_add_options --enable-valgrind
```

**Environment:**
```bash
export ASAN_SYMBOLIZER_PATH=$(which llvm-symbolizer)
```

### ASan Debug Build (Linux/macOS/Windows)

```bash
# ASan debug build configuration
mk_add_options MOZ_OBJDIR=@TOPSRCDIR@/obj-asan-debug

ac_add_options --enable-debug
ac_add_options --enable-optimize="-O1"
ac_add_options --enable-address-sanitizer
ac_add_options --disable-jemalloc
ac_add_options --disable-crashreporter
ac_add_options --disable-elf-hack
ac_add_options --disable-profiling
ac_add_options --disable-install-strip
# Linux only: ac_add_options --enable-valgrind
# Linux only: ac_add_options --enable-gczeal
```

### TSan Build (Linux Only)

```bash
# TSan build configuration (Linux only!)
mk_add_options MOZ_OBJDIR=@TOPSRCDIR@/obj-tsan

ac_add_options --enable-thread-sanitizer
ac_add_options --disable-jemalloc
ac_add_options --disable-crashreporter
ac_add_options --disable-elf-hack
ac_add_options --disable-profiling
ac_add_options --disable-sandbox
ac_add_options --disable-install-strip
ac_add_options --enable-debug-symbols=-gline-tables-only
ac_add_options --disable-warnings-as-errors

export RUSTFLAGS="-Zsanitizer=thread"
unset RUSTFMT
```

**TSan requires a custom Rust toolchain:**
```bash
./mach artifact toolchain --from-build linux64-rust-dev
rm -rf ~/.mozbuild/rustc-sanitizers
mv rustc ~/.mozbuild/rustc-sanitizers
rustup toolchain link gecko-sanitizers ~/.mozbuild/rustc-sanitizers
rustup override set gecko-sanitizers
```

**Environment:**
```bash
export TSAN_SYMBOLIZER_PATH=$(which llvm-symbolizer)
```

**Platform notes:**
- TSan is only supported on Linux
- TSan is not compatible with sandboxing (`--disable-sandbox`)
- Rust nightly may have warnings (`--disable-warnings-as-errors`)
