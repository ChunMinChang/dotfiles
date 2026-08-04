---
name: ffmpeg-security-report
description: >
  Prepare, reproduce, and audit standalone upstream FFmpeg security reports.
  Verifies that an issue is real, security-relevant, and reproducible on pinned
  upstream revisions, traces the root cause with revision-pinned links, exports
  git-formatted test and fix patches, and checks the result against the ten
  requirements on ffmpeg.org/security.html. Triggers on:
  "/ffmpeg-security-report", "report this to ffmpeg-security@ffmpeg.org",
  "prepare an upstream FFmpeg security report", "is this FFmpeg crash worth a
  security report", "audit this FFmpeg security report".
argument-hint: "<evidence-path-or-claim> [--worktree <path>] [--report-dir <path>] | --audit <report.md>"
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - AskUserQuestion
  - WebFetch
  - TaskCreate
  - Agent
  - Skill
---

# FFmpeg Security Report

## Purpose

Produce a self-contained report that an FFmpeg maintainer can reproduce without
downstream-specific context. Treat the original bug report as evidence to verify,
not as the root cause. The normal deliverable is a Markdown report plus uniquely
named testcase, input, generator, stack, and git-formatted patch attachments.

Use the official [FFmpeg security-report requirements](https://ffmpeg.org/security.html)
and read [security-checklist.md](references/security-checklist.md) before writing.
Follow the `source-permalinks` skill for every revision-pinned source link.

**Arguments:** $0

Parse the arguments; do not guess a missing path:

- `--audit <path.md>` → **audit mode**. Skip Steps 1–5 and run Step 6 against the
  named report and the attachments beside it.
- `--worktree <path>` → `FFMPEG_WORKTREE`.
- `--report-dir <path>` → `REPORT_DIR`.
- Remaining token: an existing directory or file → `EVIDENCE_DIR` / evidence file;
  otherwise treat it as a freeform claim to verify.
- Anything still unresolved → ask with `AskUserQuestion` before starting.

Create one task per workflow step with `TaskCreate` at the start of a fresh run,
and mark each `in_progress` / `completed` as you go. A report is assembled over
several long builds; the task list is what tells the user (and a resumed session)
which steps already have evidence on disk.

## Guardrails

- Verify that the issue is real, security-relevant, and reproducible. FFmpeg asks
  for careful human verification and an easy testcase; do not submit automated
  false positives or ordinary bugs, non-exploitable undefined behavior, or leaks
  to the security address.
- Do not email, file, or otherwise submit the report. Prepare the artifacts and
  let the user review and send them.
- Keep the standalone report upstream-only. Remove private paths, credentials, and
  downstream policy details unless they are required to reproduce the FFmpeg issue.
- Do not invent reviewer/finder identities, CVEs, input generators, stack frames,
  introducing commits, or exploitability claims. Record `Unknown`, `Not available`,
  or `Not applicable` with a reason, and use `AskUserQuestion` when a human
  attribution is required.
- Preserve user changes. Never reset or clean a dirty FFmpeg tree destructively;
  use a fresh clone or a separate worktree for reproduction. Inspect any existing
  worktree first and preserve its work.
- Keep the vulnerable revision, latest-upstream revision, compiler/configuration,
  platform, and fixed revision distinct. A successful run on latest master does
  not prove that the original revision was affected.
- Delegate research, never verdicts. A subagent may gather stacks, traces, or
  history; the main agent decides what is verified, what is an assumption, and
  whether the issue belongs at the security address.

## Inputs and output layout

Identify these paths before starting:

- `EVIDENCE_DIR`: supplied bug report, attachments, logs, existing patches, and
  any downstream analysis.
- `FFMPEG_WORKTREE`: a dedicated FFmpeg clone/worktree used only for this report.
- `REPORT_DIR`: the standalone report and its attachments.

Use a predictable output layout such as:

```text
REPORT_DIR/
  ffmpeg-security-report.md
  01-test-<unique-name>.patch
  02-test-<unique-name>.patch
  03-fix-<unique-name>.patch
  input-<unique-name>.<ext>                 # if an external input exists
  generate-<unique-name>.<sh|py>            # if available
  stack-<unique-name>.log                   # optional, cited by the report
  research/                                 # local working notes, never attached
    repro-matrix.md
    code-path.md
    history.md
    audit.md
```

Never reuse a generic attachment name such as `input.bin`, `testcase`, or
`crash.log` when several files are attached. Preserve the source extension and
give every attached file a report-specific unique name. Everything under
`research/` is a working note for this run — attach only what the upstream
reviewer needs.

## Subagent delegation policy

Main-agent context is reserved for synthesis: the security-relevance decision,
separating verified facts from assumptions, report wording, and the hand-off.

**Delegate** with `Agent` when the task is bounded (clear input and output shape),
voluminous (build logs, `git log -S` archaeology, multi-file traces), or
parallelisable. Each subagent **writes its findings to its own file** under
`REPORT_DIR/research/` and returns only a short summary plus that path.

Once the revisions are pinned (Step 2), these run concurrently — issue them as
multiple `Agent` calls in a single message:

- **Repro runner** → `research/repro-matrix.md`. Builds and runs the vulnerable,
  latest-upstream, and fixed revisions; records compiler, configure flags,
  platform, thread count, round count, command line, exit/signal status, and
  symbolized stacks.
- **Code-path tracer** → `research/code-path.md`. Reads every function in the
  claimed call path at the pinned revision and drafts the numbered trace with
  revision-pinned links.
- **History archaeologist** → `research/history.md`. Runs `git log -S`,
  `git log -G`, `git blame`, and parent comparison for the introducing commit,
  and reports what was checked when the result is inconclusive.

**Do not delegate**: the security-relevance decision, the final report text, the
fix design, or any claim that the issue reproduces. Never let a subagent's
summary stand in for evidence on disk — read the file it wrote.

## Workflow

### 1. Intake and evidence inventory

- Read the supplied report and list every claimed manifestation, input packet/file,
  command/API sequence, build mode, stack, patch, and observed result. Inspect
  attachments and logs directly with `Read`; do not rely on a summary when source
  evidence is available.
- Identify the human reviewer(s) who will stand behind the verification and the
  human finder(s) to credit. Ask for missing names with `AskUserQuestion`; an
  automated bot is not a human reviewer.
- Separate facts from assumptions. Mark claims that still need a run, source read,
  or symbolized stack as pending rather than presenting them as verified.
- Decide whether the issue belongs at `ffmpeg-security@ffmpeg.org`. If it is only
  a normal bug, leak, or non-exploitable source-level issue, say so and stop —
  explain that the security report workflow is not appropriate.

### 2. Pin and prepare FFmpeg source

- If no dedicated tree exists, clone from an official upstream URL:

  ```sh
  git clone https://git.ffmpeg.org/ffmpeg.git FFMPEG_WORKTREE
  # or: git clone https://code.ffmpeg.org/FFmpeg/FFmpeg/ FFMPEG_WORKTREE
  ```

- Confirm the tree and source hash before each run:

  ```sh
  git -C FFMPEG_WORKTREE status --short
  git -C FFMPEG_WORKTREE rev-parse HEAD
  ```

- Record the exact vulnerable/reported commit, the independently tested latest
  upstream commit, and any fixed commit. If the report reproduces on more than
  one revision, list every full 40-hex hash. Do not use `HEAD`, `master`, or a
  branch name as the source identifier.
- For code citations, use revision-pinned URLs such as
  `https://github.com/FFmpeg/FFmpeg/blob/<hash>/libavcodec/<file>.c#L123`.
  Recalculate line numbers for the revision named by the report. Link functions,
  call sites, and the exact state-transition and memory-access lines.

### 3. Reproduce the issue and the fix

Hand the build/run matrix to the repro-runner subagent when the builds are long,
then read `research/repro-matrix.md` before making any reproduction claim.

- Start with the smallest public API or `ffmpeg` command that exercises the
  issue. A custom API/FATE harness is acceptable when it is complete and easy to
  build. Include all source and FATE registration needed to run it.
- Build and run the vulnerable revision first. Use a normal/debug build before
  requiring ASan, UBSan, guard pages, or temporary signal handlers. Keep compiler,
  configure flags, platform, thread count, environment overrides, command line,
  and exit/signal status in the evidence.
- Run the same test on latest upstream and with the proposed fix. The matrix must
  distinguish: vulnerable failure, fixed pass/changed behavior, and latest-master
  status. Repeat scheduling-sensitive tests enough to justify reliability and
  record the number of rounds.
- Capture symbolized stack traces with file and line numbers. Keep raw logs as
  attachments when useful, but summarize the relevant frames in the report and
  tie each stack to an exact source revision.
- Use independent, uniquely named input files. Embedded data is valid when the
  test patch is self-contained. If a generator script exists, run it and verify
  that it produces the attached input. If no generator can be recovered, state
  that explicitly; never claim reproducibility that was not tested.

### 4. Trace the root cause and identify history

The code-path tracer and history archaeologist subagents draft
`research/code-path.md` and `research/history.md`. The main agent re-opens the
cited lines, decides what is verified, and writes the trace that ships.

- Read every function in the claimed call path at the pinned revision. For
  stateful or frame-threaded codecs, explain worker contexts, reference/frame
  state, and how decoding state is handed from one worker or frame to the next.
- Write the report's **Code Path Trace** as a numbered 1…N sequence. Each item
  should contain a function name, an arrowed call chain, a short explanation, and
  permanent source links with line anchors. Keep separate READ and WRITE paths
  when they share state but fail in different functions. Explain any non-obvious
  pointer arithmetic or indexing in plain language.
- Find the introducing commit with `git log -S`, `git log -G`, `git blame`, and
  parent comparison. Call it "first affected" only when the evidence supports
  that claim; otherwise say "introducing commit unknown" and state what was checked.
- Create the proposed fix on top of the test commit and export it with
  `git format-patch`. Ensure the test patch is independently applicable and the
  fix patch is separate, ordered, and reviewable. If exploratory commits created
  a partial test and later edits, squash or re-export them so the final test
  attachment is one complete patch rather than "create, then modify" patches.
  Do not mix debug instrumentation into the clean patch.
- For complicated multithreaded or stateful bugs, add a companion note for
  readers with no codec knowledge. Explain the state variables, worker-to-worker
  hand-off, call order, and the source of every suspicious scalar or pointer
  index; keep the main report's numbered trace concise.

### 5. Write the standalone report

Use the order in [security-checklist.md](references/security-checklist.md). Make
each of the ten requirements visible either as a populated field or an explicit
`Unknown`/`Not available`/`Not applicable` entry with a reason:

- human reviewer identity and finder credit;
- copy/paste reproduction and uniquely named inputs;
- full source commit hash(es);
- symbolized stacks with line numbers;
- evidence-backed description and impact;
- introducing commit, if known;
- input-generation script, if available;
- git-formatted proposed fix, if available; and
- CVE or related identifier, including "none assigned" when appropriate.

Keep the report self-contained: state build prerequisites, exact commands or API
sequence, expected unfixed/fixed result, and how to apply attachments. Include
the source revision beside every stack and code trace. Cite code with pinned
links, never trunk/tip URLs. Do not bury the only testcase or patch reference in
an external private report.

### 6. Audit and hand off

- Name patches and inputs uniquely. Prefer `01-test-...patch`, `02-test-...patch`,
  and `03-fix-...patch`; attach only artifacts needed by the upstream reviewer.
- Run the structural validator and fix every error; warnings require an explicit
  decision:

  ```sh
  python3 .claude/skills/ffmpeg-security-report/scripts/validate_ffmpeg_report.py \
      REPORT_DIR/ffmpeg-security-report.md
  ```

- Launch an independent audit subagent (`Agent`) that has not seen this run's
  reasoning. Give it the report path only, and have it write
  `research/audit.md`: open every source link and confirm the cited file and line
  still say what the report claims, confirm every FFmpeg URL uses a full commit
  hash, confirm the fixed/unfixed/latest matrix matches the attached logs, and
  flag private or downstream details that leaked into the report.
- When a proposed fix patch exists, get a second opinion on the fix itself with
  `Skill(red-pen, …)`, passing the report path and the patch path. The reviewer
  may argue for a different fix design; treat that as in scope and escalate the
  redesign to the user rather than quietly keeping the original patch.
- Report what was not available instead of silently omitting it.

Hand off with this shape, and nothing more:

```markdown
**FFmpeg security report** ([report](<path-to-report>))
- Verdict: <security-relevant and reproducible | not security-relevant | unverified>
- Revisions: vulnerable `<hash>` / latest `<hash>` / fixed `<hash or n/a>`
- Attachments: <list of uniquely named files>
- Validator: <PASS/FAILED, error and warning counts>
- Unresolved: <checklist items recorded as Unknown/Not available, or "none">
```

The user sends the report. This skill never does.

## Resources

- [security-checklist.md](references/security-checklist.md): the ten FFmpeg fields,
  evidence standards, report skeleton, and attachment rules.
- [validate_ffmpeg_report.py](scripts/validate_ffmpeg_report.py): deterministic
  pre-submission checker for report fields, pinned source links, and stacks.
- `source-permalinks` skill: revision-pinned URL patterns, including the FFmpeg
  GitHub mirror.
- `red-pen` skill: independent review of the proposed fix.
