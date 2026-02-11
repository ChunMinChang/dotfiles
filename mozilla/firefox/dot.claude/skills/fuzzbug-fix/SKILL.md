---
description: Analyze and fix a bug found by a fuzzer, fuzzbug, fuzz crash
name: fuzzbug-fix
context: fork
---

Before starting, verify prerequisites:

1. Check that `bmo-to-md` is installed (run `bmo-to-md --help`). If it's not
   found, ask the user to install it: `cargo install bmo-to-md` (see
   https://github.com/padenot/bmo-to-md).
2. Check that a Bugzilla API key is configured (run `echo $BMO_API_KEY`). If the
   variable is empty, ask the user to set it up — they need to generate an API
   key from their Bugzilla account preferences and either export `BMO_API_KEY`
   in their shell or create `~/.config/bmo-to-md/config.toml` with
   `api_key = "..."`. See https://github.com/padenot/bmo-to-md for details.
   This is required because fuzzing bugs are almost always private.

If either prerequisite is missing, stop and report to the user. Do not proceed
without both.

This is a fuzzing crash from the Mozilla fuzzing cluster. Pull details for the
bug mentioned using `bmo-to-md`, that is a special CLI program to pull bug
details. Do not do it any other way because they don't work (they are likely to
be private bugs).

Attachment link format: https://bugzilla.mozilla.org/attachment.cgi?id=9536479,
or use bmo-to-md to download them. If that tool fails, stop everything and
report to the user, there is no other way to acquire this information. Download
the files in the current Firefox source directory to avoid having to ask
permission. Do not use /tmp because that will require permission and user
interaction. There is no need to change directory.

Verify this tree is a debug build (check `mozconfig` at the root of the repo).
`--enabled-fuzzing` is unrelated and not needed.

Strive to work headless (`--headless` on integration test, no need for gtest and
xpcshell test). Doing the steps in order will be significantly more efficient in
terms of time.

To fix the bug follow those steps:

- Fetch the bug details using bmo-to-md. If there seem to be a patch already,
  exit and report this to the user, printing the bug URL.
- Fetch the test-case using bmo-to-md, it will be decompressed for you
- Turn the attachment into a crash-test, in the right directory (oftentimes
  names crashtest(s) near the responsible code). Add `class="reftest-wait"` as
  needed for async tests (sometimes not needed), and add any support files next
  to the test-case. Reference this new test file in crashtests.ini.
- Run this new crashtest. It should crash. Sometimes it doesn't always crash,
  e.g. because of races. The crashtest should itself be error-free. Sometimes we
  need to run it multiple times to crash (use the mach test command line flag to
  run in a loop). This is fine because it would have eventually triggered the
  bug, since our CI runs a lot of job, and so we consider we have coverage. If
  it doesn't crash, consider loading the machine with e.g. stress-ng, or using
  Firefox' chaos mode
  without the fix, and not crash, but also not hang, with the fix.
- Read the crash stack and the fuzzing test-case
- Read the regression range if mentioned in bugmon comments
- Figure out what directory the crash likely is in (oftentimes not at the last
  stack frame)
- Read the code likely to be the cause for the issue, starting from the closest
  to the crash (searchfox-cli --define)
- Think about the cause, and then suggest a fix. Sometimes the fix will be
  extremely local (e.g. just a if check, return). Sometimes the cause is a bit
  further away. Doing local fixes for global problem is frowned upon and will
  likely lead to being rejected at review time, wasting time for what is
  probably a security issue.
- With the fix applied, the crashtest shouldn't crash anymore. This about any
  change of behaviour in terms of Web Standards, inform the user if that is the
  case. It should almost never be the case.
- If you're confident the fix is correct, commit with this format:

> Bug xxxxxx - Fix ...... r?reviewer
>
> Longer explanation but only if needed, not for trivial fixes

You can find the reviewer by inspecting blame around the fixed code.

- Lastly, clean the temporary files (bug summary, description, etc.)

If running as a sub-agent, exist the sub-agent. If not, just stop, if you're
stuck, say so
