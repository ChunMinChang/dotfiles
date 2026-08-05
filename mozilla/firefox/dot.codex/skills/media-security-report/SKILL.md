---
name: media-security-report
description: >
  Prepare, reproduce, and audit standalone upstream security reports for
  third-party media libraries Firefox vendors, including FFmpeg/ffvpx, libvpx,
  libaom, dav1d, the Xiph libraries, libpng, libjpeg-turbo, libsoundtouch,
  libsrtp, libwebrtc, libyuv, libwebp, nestegg, cubeb, mp4parse-rust, and
  in-tree components with no upstream. Use when Codex needs to determine the
  correct private reporting channel, reproduce a suspected vulnerability on a
  vendored revision, trace its root cause with revision-pinned links, export
  git-formatted patches, draft a submission without sending it, or audit an
  existing media-library security report.
---

# Media Security Report

## Purpose

Produce a self-contained report that the library's own maintainer can reproduce
without any Firefox context, and route it to the private channel that library
actually has. Treat the original bug report as evidence to verify, not as the
root cause.

Only FFmpeg and libjpeg-turbo publish required-contents lists, so the report
body is the same everywhere — [report-core.md](references/report-core.md). What
varies per library is the channel, the confidentiality mechanics, and how the
crash input travels: [channel-profiles.md](references/channel-profiles.md) and
[library-policies.md](references/library-policies.md).

Follow the `$source-permalinks` skill for every revision-pinned link.

## Inputs

Derive the inputs from the user's request; do not guess a missing path:

- `--audit <path.md> --library <id>` → **audit mode**. Skip to Step 6.
- `--library <id>` → library id or a tree path (`media/libdav1d` works).
- `--firefox <path>` → checkout root. Default: walk up from cwd, since this
  skill is symlinked into each worktree's `.codex/skills/`.
- `--report-dir <path>` → where the report and artifacts go.
- Remaining token: an existing directory or file → the evidence; otherwise a
  freeform claim to verify.
- Anything still unresolved → ask the user directly.

On a fresh run, use `update_plan` to create one item per workflow step. A report
spans several long builds, so keep the plan current and treat the evidence on
disk as the durable record of completed work.

## Guardrails

- **Never send, file, email, or submit.** Prepare the report and the submission
  draft; the user does the rest. This includes never opening a prefilled
  tracker URL in a way that creates the item.
- **Fail closed on routing.** A library with no policy row routes to a
  Bugzilla security bug with no external CC. Guessing an upstream security
  address is the one mistake that discloses a live vulnerability.
- **Crash-input delivery is the channel's decision, not yours.** Attaching a
  file to a confidential GitLab issue in a public project makes it
  world-readable. Follow the profile.
- **Verify the issue is real, security-relevant, and reproducible.** Do not send
  automated false positives, ordinary bugs, non-exploitable undefined behavior,
  or leaks to a security address. Several projects ban accounts for this.
- **Never invent** reviewer or finder identities, CVEs, generators, stack
  frames, introducing commits, or exploitability claims. Record `Unknown`,
  `Not available`, or `Not applicable` with a reason, and ask the user directly
  when a human attribution is required.
- **Never invent a revision either.** When the tree does not record one, say so.
- **Preserve user changes.** Never reset or clean a dirty tree destructively;
  use a fresh clone or a separate worktree. Inspect any existing worktree first.
- Keep the vulnerable, latest-upstream, and fixed revisions distinct. A
  successful run on latest master does not prove the vendored revision was
  affected.
- **Delegate research, never verdicts.** A subagent gathers stacks, traces and
  history; the main agent decides what is verified and where the report goes.
- Record the channel's known unknowns rather than resolving them by assumption.

## Inputs and output layout

- `EVIDENCE_DIR`: the supplied bug report, attachments, logs, existing patches.
- `UPSTREAM_WORKTREE`: a dedicated clone of the library, used only for this report.
- `REPORT_DIR`: the report and its artifacts.

```text
REPORT_DIR/
  <library>-security-report.md
  submission-draft.md                       # ready to paste; never sent
  01-test-<unique-name>.patch
  02-fix-<unique-name>.patch
  input-<unique-name>.<ext>                 # if the channel takes attachments
  generate-<unique-name>.<sh|py>            # if available
  stack-<unique-name>.log                   # optional, cited by the report
  research/                                 # working notes, never submitted
    repro-matrix.md
    code-path.md
    history.md
    audit.md
```

Never reuse a generic name such as `input.bin` or `crash.log`. Preserve the
source extension and give every artifact a report-specific unique name.

## Subagent delegation policy

Main-agent context is reserved for synthesis: the security-relevance decision,
**the routing decision**, separating verified facts from assumptions, and the
report wording.

Delegate with `spawn_agent` when a task is bounded, voluminous, or parallelisable.
Each subagent writes to its own file under `REPORT_DIR/research/` and returns a
short summary plus that path. Once the revision is pinned (Step 2), issue these
as parallel subagent tasks when slots are available:

- **Repro runner** → `research/repro-matrix.md`. Builds and runs the vendored,
  latest-upstream and fixed revisions; records compiler, configure flags,
  platform, thread count, round count, command line, exit/signal status, and
  symbolized stacks.
- **Code-path tracer** → `research/code-path.md`. Reads every function in the
  claimed call path at the pinned revision and drafts the numbered trace with
  revision-pinned links.
- **History archaeologist** → `research/history.md`. `git log -S`, `git log -G`,
  `git blame`, parent comparison; reports what was checked when inconclusive.

**Never delegate**: which channel the report goes to, whether the issue is
security-relevant, the fix design, or any claim that the issue reproduces.

## Workflow

### 0. Identify the library and route

```sh
python3 .codex/skills/media-security-report/scripts/media_lib_facts.py --library <id>
```

Read the library's row in [library-policies.md](references/library-policies.md)
and its channel section in
[channel-profiles.md](references/channel-profiles.md), then print a routing
block and confirm it with the user before doing any work:

```text
Library:      <id>            (paths: <tree paths>)
Revision:     <ref> (<kind>)  <- <where the tree records it>
Repository:   <url> [<forge>]
Bugzilla:     <product> :: <component>  <- <where that came from>
Channel:      <profile>  →  <intake>
Secondary:    <… or none>
Crash input:  <attach | inline base64 | encrypted attachment | unverified>
One-shot:     <the irreversible step, or none>
Test harness: <framework> — <where its tests live>
```

**Gate:** if the library has no upstream (`has_upstream: false` — libmkv,
openmax_il, mozva, psshparser, gmp-clearkey, wmf-clearkey), stop the upstream
workflow here. The deliverable becomes a Bugzilla security bug with **no
external CC**, reproduction is a Firefox test, and the code is cited with
revision-pinned searchfox links.

If the tool reports an assumed Bugzilla component, verify it before filing:
`./mach file-info bugzilla-component <path>`.

### 1. Intake and evidence inventory

- Read the supplied report and list every claimed manifestation, input, command
  or API sequence, build mode, stack, patch, and observed result. Inspect
  attachments and logs directly; do not rely on a summary when the
  source evidence is available.
- Identify the human reviewer(s) who will stand behind the verification and the
  human finder(s) to credit. Ask the user directly; a bot is not a human
  reviewer. In the same question, capture **whether and where AI was used** —
  never assume, and never answer it on the user's behalf.
- Separate facts from assumptions. Mark anything still needing a run, source
  read, or symbolized stack as pending.
- Decide whether the issue belongs at this library's security channel, against
  that library's scope gate where it has one (libjpeg-turbo's is explicit). If
  it is an ordinary bug, say so and stop.

### 2. Pin and prepare the source

- Clone from the repository URL the routing block printed — not from
  `origin.url` in `moz.yaml`, which is often just the project homepage.
- Check out the vendored revision. Confirm the tree and hash before each run:

  ```sh
  git -C UPSTREAM_WORKTREE status --short
  git -C UPSTREAM_WORKTREE rev-parse HEAD
  ```

- When the tree pins a **tag**, record both the tag and the hash it resolves to,
  and cite the hash in the trace. When it records a **short hash** (libwebrtc),
  say so rather than padding it out.
- List the library's local Firefox patches; a defect may be Mozilla's, not
  upstream's. The facts tool prints them.
- Cite code with the forge template the facts tool printed, always pinned.

### 3. Reproduce the issue and the fix

Hand the matrix to the repro-runner subagent when the builds are long, then read
`research/repro-matrix.md` before making any reproduction claim.

- Start with the smallest command or API sequence that exercises the issue. A
  custom harness is fine when it is complete and easy to build. Build/test hints
  per library are in [library-policies.md](references/library-policies.md).
- Build and run the vendored revision first. Use a normal or debug build before
  reaching for ASan, UBSan, or guard pages. Keep compiler, configure flags,
  platform, thread count, environment, command line, and exit/signal status.
- Run the same test on latest upstream and with the proposed fix. The matrix
  must distinguish vulnerable failure, fixed pass, and latest-upstream status.
  Repeat scheduling-sensitive tests enough to justify reliability and record the
  number of rounds.
- Capture complete symbolized stacks with file and line numbers, each tied to
  one exact revision and build. Preserve the original numbering and every frame
  from the first emitted frame (`#0` or `#1`) through the final `#N`; never omit
  frames in the middle or replace them with an ellipsis. Label and include each
  stack separately when the report has faulting-thread, thread-creation, or
  multiple-manifestation stacks.
- Use a uniquely named input. If a generator exists, run it and confirm it
  produces that input; if none can be recovered, say so rather than claiming
  reproducibility that was not tested.

**Standalone test gate.** A CLI reproduction gets the issue triaged; a test in
the project's own harness gets it *fixed*, and stays as a regression guard
afterwards. If the evidence does not already include one, decide whether you can
write one — do not quietly settle for a command line. The routing block prints
the harness, where its tests live, and how a new one is registered.

Ask the user directly first whether a test already exists and whether they want
one attached; a build cycle is expensive. If no test is provided, evaluate the
available harness and then:

1. Read an existing test in that harness and copy its shape.
2. Write the smallest test that fails on the vendored revision and passes with
   the fix, and register it the way that harness requires (a FATE `.mak` entry
   and ref file, a `test.mk`/`CMakeLists.txt` line, a `meson.build` entry, a
   `#[test]` fn, …).
3. Run it both ways and record both results in the matrix.
4. Export it as `01-test-<desc>.patch`, separate from the fix, and confirm it
   applies and runs on its own.

Three libraries have no usable upstream suite — libsoundtouch (SoundStretch CLI
only), nICEr and widevine-adapter. There, a self-contained `main()` or a Firefox
gtest is the honest substitute; say which you chose.

If a test genuinely cannot be written, record the **concrete blocker**: no
upstream suite at all, an input that cannot be redistributed, a failure that
needs a sanitizer the harness does not build with, or timing dependence that
makes it unreliable under the runner. "No test was written" with no reason is
not an acceptable answer, and the validator rejects the report for it.

### 4. Trace the root cause and identify history

The tracer and archaeologist subagents draft `research/code-path.md` and
`research/history.md`. The main agent re-opens the cited lines, decides what is
verified, and writes the trace that ships.

- Read every function in the claimed call path at the pinned revision. For
  stateful or frame-threaded codecs, explain worker contexts, reference/frame
  state, and how decoding state is handed from one worker or frame to the next.
- Write the **Code Path Trace** as a numbered 1…N sequence: function name,
  arrowed call chain, short explanation, revision-pinned links with line
  anchors. Keep READ and WRITE paths separate when they share state but fail in
  different functions. Explain non-obvious pointer arithmetic in plain language.
- Find the introducing commit with `git log -S`, `git log -G`, `git blame`, and
  parent comparison. Call it "first affected" only when the evidence supports
  it; otherwise say "introducing commit unknown" and state what was checked.
- Create the fix on top of the test commit and export both with
  `git format-patch`. The test patch must apply independently; the fix patch
  goes on top. Squash exploratory commits so the test attachment is one complete
  patch. Keep debug instrumentation out of both.
- For complicated multithreaded or stateful bugs, add a companion note for a
  reader with no codec knowledge, and keep the numbered trace concise.

### 5. Write the report and the submission draft

**5a — core evidence.** Write `REPORT_DIR/<library>-security-report.md` using
the skeleton in [report-template.md](references/report-template.md) and the
content rules in [report-core.md](references/report-core.md). Every core item is
either populated or explicitly `Unknown`/`Not available`/`Not applicable` with a
reason.

Name the report for the defect, not the library alone —
`vp9-frame-thread-flush-oob.md` tells a maintainer what it is before they open
it. Fill every placeholder from evidence; never invent or hardcode a name, an
email address, an employer, a disclosure deadline, or an AI-usage statement —
ask the user directly.

**5b — channel packaging.** Apply the profile: deliver the crash input the way
the channel requires, add the metadata it wants, and omit the metadata it
forbids (CVSS and CWE are welcome on GitHub and forbidden on Bugzilla). Write
the confidentiality mechanics into the report so the user cannot miss them.

**5c — submission draft.** Fill the channel's template from
[submission-drafts.md](references/submission-drafts.md) into
`REPORT_DIR/submission-draft.md`. It is a draft. Do not send it.

### 6. Audit and hand off

- Run the validator and fix every error; warnings require an explicit decision:

  ```sh
  python3 .codex/skills/media-security-report/scripts/validate_media_report.py \
      REPORT_DIR/<library>-security-report.md --library <id>
  ```

- Launch an independent audit with `spawn_agent`, using a subagent that has not
  seen this run's reasoning. Give it the report path only, and have it write
  `research/audit.md`: open every source link and confirm the cited file and line still say what the
  report claims; confirm every link into the library's repository is pinned to
  the vendored revision; confirm the crash input is delivered the way the
  channel requires; confirm the fixed/unfixed/latest matrix matches the logs; confirm every
  crash stack is complete and consecutively numbered with no omitted middle frames;
  flag any downstream detail that leaked.
- When a proposed fix exists, get a second opinion with the `$red-pen` skill,
  passing the report path and the patch path. The reviewer may argue for a
  different fix design — that is in scope; escalate it to the user rather than
  quietly keeping the original patch.
- Report what was not available instead of silently omitting it.

Hand off with this shape, and nothing more:

```markdown
**Security report — <library>** ([report](<path>) · [draft](<path>))
- Verdict: <security-relevant and reproducible | not security-relevant | unverified>
- Channel: <profile> → <intake>   (secondary: <… | none>)
- Revisions: vendored `<ref>` / vulnerable `<ref>` / latest `<ref>` / fixed `<ref|n/a>`
- Crash input: <attached <name> | inline base64 | encrypted attachment>
- Standalone test: <in <harness>, attached as <patch> | not feasible: <blocker>>
- Artifacts: <list>
- Validator: <PASS/FAILED, error and warning counts>
- Do these in order when you file:
  1. <one-shot / irreversible step first>
  2. <access-preservation step>
  3. <post-filing verification>
- Unresolved: <… | none>
```

The user files the report. This skill never does.

## Resources

- [report-template.md](references/report-template.md): the section skeleton a
  finished report follows, derived from an accepted upstream report.
- [report-core.md](references/report-core.md): the universal evidence core,
  report order, evidence rules, artifact naming, hygiene.
- [channel-profiles.md](references/channel-profiles.md): the six channels, their
  mechanics, traps, and what each one wants or forbids.
- [library-policies.md](references/library-policies.md): the routing table,
  per-library extras, build/test hints, known unknowns.
- [submission-drafts.md](references/submission-drafts.md): one draft template
  per channel.
- `scripts/media_lib_facts.py`: live per-library facts from the checkout.
- `scripts/validate_media_report.py`: pre-submission structural checker.
- `scripts/channel_policy.py`: the machine-readable policy tables.
- `$source-permalinks` skill: revision-pinned URL patterns per forge.
- `$red-pen` skill: independent review of the proposed fix.
