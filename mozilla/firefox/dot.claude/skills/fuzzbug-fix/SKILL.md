---
description: Analyze and fix a bug found by a fuzzer, fuzzbug, fuzz crash
name: fuzzbug-fix
context: fork
---

# Fuzzbug Fix Skill

This skill guides the analysis and fix of a fuzzing crash from the Mozilla
fuzzing cluster.

## General Principles

- **Before starting work, create a plan** with one item per step below (Steps
  1–6, including sub-steps). Present the plan to the user and get approval before
  proceeding.
- Work headless (`--headless` on integration tests; not needed for gtest/xpcshell).
- When stuck, need clarification, or need the user to manually check something,
  **stop and discuss** with the user rather than guessing.
- Follow the steps in order for efficiency.

---

## Step 1: Fetch Bug Details

### Determine if the bug is private

1. First, try fetching the bug via the MCP tool `mcp__moz__get_bugzilla_bug`.
   This works for public bugs and provides metadata quickly.
2. If the MCP tool returns limited info or an access error, the bug is private.
   Proceed with `bmo-to-md` (see below).
3. If the MCP tool succeeds with full details, you can use that data. You will
   still need `bmo-to-md` if there are binary attachments or test cases to
   download.

### Using bmo-to-md for private bugs (most fuzz bugs)

1. Check that `bmo-to-md` is installed: run `bmo-to-md --help`. If not found,
   ask the user to install it: `cargo install bmo-to-md`
   (see https://github.com/padenot/bmo-to-md).
2. Check that a Bugzilla API key is configured: run `echo $BMO_API_KEY`. If
   empty, ask the user to set it up — they need to generate an API key from
   their Bugzilla account preferences and either export `BMO_API_KEY` in their
   shell or create `~/.config/bmo-to-md/config.toml` with `api_key = "..."`.

If either prerequisite is missing, **stop and report to the user**. Do not
proceed without both.

### Downloading bug data

Ask the user if they want to download bug details and attachments to markdown
files for persistent access throughout the conversation.
- If yes: ask if they already have a folder (e.g., `bug-md/`) or create one.
  Use: `bmo-to-md -o <folder> -a <bug_id>`.
- If no: use `bmo-to-md` without `-o` to fetch directly.

If `bmo-to-md` fails, **stop and report** — there is no alternative for private
bugs. Do not use /tmp or temporary locations.

### Check for existing patches

After fetching, if there already seems to be a patch attached, **stop and
report** this to the user, printing the bug URL.

---

## Step 2: Verify Build Configuration

Check the `mozconfig` at the root of the repo. Verify this is a **debug build**
(look for `--enable-debug` or `ac_add_options --enable-debug`).
`--enable-fuzzing` is unrelated and not needed for reproducing most fuzz bugs.

If the mozconfig looks wrong or doesn't exist, inform the user and suggest using
the `/mozconfig` skill to generate an appropriate debug configuration. Some bugs
may require specific build configurations (e.g., ASan, TSan). Check the bug
comments for hints about which configuration was used by the fuzzer.

---

## Step 3: Create the Crashtest

If there is **no test attachment** (some bugs only have stack traces or minimal
descriptions), skip to [Step 3b: No Test Attachment](#step-3b-no-test-attachment).

### Find the right directory

Crashtests live in `crashtests/` subdirectories near the responsible code:
- Search for existing `crashtests/` directories near the component:
  `find dom/media/crashtests` or `find layout/base/crashtests`, etc.
- The directory is almost always named `crashtests` (not `crashtest`).
- If no `crashtests/` directory exists nearby, look for the closest one in the
  parent module, or create one if appropriate.

### Create the test file

Name the file after the bug number: `<bug_number>.html` (or `.xhtml` if needed).

**Minimal crashtest (synchronous):**
```html
<!DOCTYPE html>
<html>
<body>
<script>
  // Code that triggers the crash
</script>
</body>
</html>
```

**Async crashtest with reftest-wait:**

Use `class="reftest-wait"` on the root `<html>` element when the crash requires
asynchronous operations (resource loading, media playback, event handlers, etc.).
Remove the class when the test is ready to signal completion:

```html
<!DOCTYPE html>
<html class="reftest-wait">
<body>
<script>
  // Set up async operation...
  someAsyncThing.onload = function() {
    // Test logic here
    document.documentElement.removeAttribute("class");
  };
  // Add a failsafe timeout to prevent hangs:
  setTimeout(() => {
    document.documentElement.removeAttribute("class");
  }, 5000);
</script>
</body>
</html>
```

**Key patterns:**
- Always add a failsafe `setTimeout` for reftest-wait tests to prevent hangs.
- Place support files (iframes, media files, etc.) next to the test file.
- For media-related crashes, the test case from the fuzzer is often a binary
  file (e.g., `.webm`, `.mp4`, `.ogg`) — reference it in the HTML via
  `<audio>`, `<video>`, or `new AudioContext()`.

### Register the test in crashtests.list

Add a line to the `crashtests.list` file in the same directory:

```
load <bug_number>.html
```

**Common syntax patterns:**
```
load 1234567.html                                    # simple
skip-if(Android) load 1234567.html                   # skip on Android
skip-if(ThreadSanitizer) load 1234567.html           # skip under TSan
skip-if(isDebugBuild) load 1234567.html # bug NNNNN  # skip in debug with comment
```

---

### Step 3b: No Test Attachment

When the bug has no test attachment (only a stack trace, crash signature, or
description):

1. **Analyze the bug directly**: read the crash stack, regression range, and any
   bugmon comments.
2. **Trace the code path**: use `searchfox-cli --define` to read the relevant
   code from the crash stack. Identify the likely root cause.
3. **Present your analysis to the user**: show the code path, explain the
   reasoning for the likely cause, and propose a fix. **Wait for user agreement
   before proceeding.**
4. Once the user agrees with the analysis, try to **generate a test** (crashtest,
   gtest, or other appropriate format) that reproduces the issue. The test should
   fail or crash without the fix.
5. If generating a test is not feasible, discuss with the user whether to proceed
   with the fix without a regression test, or explore other testing approaches.

---

## Step 4: Reproduce the Crash

Run the crashtest **without** the fix applied. The goal is to confirm it crashes.

### Case 1: Crashes reliably

The test crashes on every run. This is the ideal case. Proceed to Step 5.

### Case 2: Crashes intermittently

The crash is non-deterministic (e.g., due to race conditions). Try these
approaches in order:

1. **Run in a loop**: use `./mach test <path> --headless --repeat N` (e.g.,
   `--repeat 20`) to run it multiple times.
2. **Use Firefox chaos mode**: set `MOZ_CHAOSMODE=3` environment variable to
   introduce random scheduling jitter:
   ```
   MOZ_CHAOSMODE=3 ./mach test <path> --headless --repeat 10
   ```
3. **Load the machine**: use `stress-ng` to add CPU/memory pressure that makes
   race conditions more likely:
   ```
   stress-ng --cpu $(nproc) --timeout 60 &
   MOZ_CHAOSMODE=3 ./mach test <path> --headless --repeat 10
   ```

If it crashes at least once across multiple runs, that is sufficient — CI runs
many jobs and will eventually trigger the bug.

### Case 3: Does not crash

If the test never crashes even with the above techniques:

1. Verify the build configuration matches what the fuzzer used (check bug
   comments for ASan, debug, etc.).
2. Verify the test case is correct (right format, no corruption).
3. Discuss with the user — the test may require a specific build or environment.

**Important**: the crashtest itself must be error-free (no JS errors, no missing
resources). Errors other than the crash indicate a problem with the test.

---

## Step 5: Analyze and Fix

### Read the crash details

- Read the crash stack from the bug or from running the test locally.
- Read the regression range if mentioned in bugmon comments.
- The root cause is **often not at the top stack frame** — look deeper.

### Investigate the code

- Use `searchfox-cli --define <ClassName::Method>` to find the relevant code.
- Start from the frame closest to the crash and work outward.
- Check `git log --oneline -20 -- <file>` or `git blame` on suspicious areas,
  especially if a regression range is available.

### Third-party / vendored code

If the crash is in third-party code (libvpx, ffvpx, libdav1d, cubeb, libopus,
libaom, etc.):

1. **Check if this is a known upstream issue** — search the upstream bug tracker.
2. **Prefer upstream fixes**: if there's already an upstream fix, the right
   approach is to update the vendored library (see `/update-media-lib` skill).
3. **Mozilla-side workaround**: if the upstream fix is complex or unavailable,
   a workaround at the Mozilla integration layer may be appropriate (e.g.,
   input validation before calling into the library).
4. **Discuss with the user** before deciding — upstream updates vs. local
   workarounds have different trade-offs for maintenance.

### Common crash type patterns

| Crash Type | Typical Indicators | Common Fix Approaches |
|---|---|---|
| **Use-after-free** | ASan report "heap-use-after-free", accessing freed memory | Fix the ownership/prevent access after free. Often involves preventing deletion of ref-counted/prevent access after release. Don't just null-check — fix the lifetime. |
| **Null dereference** | SIGSEGV at low address, null pointer in stack | Check why the pointer is null — may indicate an unexpected state. A null check is sometimes correct, but may mask a deeper issue. |
| **Buffer overflow** | ASan "heap-buffer-overflow" or "stack-buffer-overflow" | Fix bounds checking. Usually a missing length/size validation on input data. |
| **Assertion failure** | `MOZ_ASSERT` / `MOZ_CRASH` triggered | The assertion is usually correct — the bug is reaching that state. Fix the code path that leads to the invalid state, not the assertion. |
| **Integer overflow** | Large values causing unexpected behavior, CheckedInt failures | Add overflow checks before the arithmetic. Use `CheckedInt` or validate input bounds. |
| **OOM / allocation failure** | Very large allocation sizes from malformed input | Validate sizes from untrusted input before allocating. Return error/reject rather than proceeding. |

**Important**: avoid purely local fixes for systemic problems. A band-aid
`if (!ptr) return;` will likely be rejected at review if the real problem is a
lifetime issue. Think about *why* the bad state occurs.

### Propose the fix

- Suggest a fix and explain your reasoning.
- Think about whether the fix changes any Web Standards behavior — inform the
  user if so (this should almost never happen).

### Verify the fix

1. Apply the fix and rebuild: `./mach build`
2. Run the crashtest again — it should **not crash** and **not hang**.
3. For intermittent crashes, run multiple times with chaos mode to confirm.

---

## Step 6: Finalize

### Ask the user about creating a patch

Ask the user:
1. **Patch format**: what format do they want?
   - Git commit (via `/patch` skill)
   - `git format-patch` file
   - Plain diff file
   - Just show the diff (for manual handling)

2. **Commit message**: for security-sensitive bugs (most fuzz bugs are), the
   commit message should be **deliberately ambiguous** — do not reveal the
   nature of the vulnerability.

   **Good (ambiguous) examples:**
   - `Bug XXXXXX - Improve bounds checking in MediaDecoder`
   - `Bug XXXXXX - Add validation for buffer size in AudioData::CopyTo`
   - `Bug XXXXXX - Handle edge case in WebAudio graph processing`

   **Bad (reveals vulnerability) examples:**
   - `Bug XXXXXX - Fix use-after-free in MediaDecoder::Shutdown`
   - `Bug XXXXXX - Fix heap buffer overflow when parsing VP9`
   - `Bug XXXXXX - Fix null dereference crash in AudioNode`

   Always show the proposed commit message to the user for review before
   creating the patch.

3. **Reviewer**: suggest a reviewer by inspecting `git blame` around the fixed
   code.

If the user wants a git commit, delegate to the `/patch` skill.

### Cleanup

If bug files were downloaded to a folder, ask the user if they want to keep them
(for reference) or clean them up.

---

## When You're Stuck

If you get stuck at any point:
- **Stop and discuss** with the user rather than guessing or trying random things.
- Explain what you've tried and what's not working.
- Ask for manual verification if needed (e.g., "can you check if this crashes
  when you run it?").

If running as a sub-agent, exit the sub-agent. If not, just stop.
