---
name: red-pen
description: >
  RedPen — independent review of a proposed root-cause-analysis solution.
  Spawns an isolated reviewer with no shared memory; returns a structured
  review doc with verdict, alternatives, and concerns. Reusable from any
  RCA/bugfix skill (sherlock, fuzzbug-fix, triage) and standalone.
argument-hint: "<analysis-source> [solutions-source] [output-path]  # sources: *.md | bug:<id> | D<id> | *.patch | <sha> | diff | local | https://..."
allowed-tools:
  - Agent
  - Read
  - Write
  - AskUserQuestion
---

# RedPen

Get an **independent second opinion** on a proposed RCA solution before it
goes in front of a human reviewer or the user.

The reviewer runs in an isolated subagent context — it does not see the
calling agent's conversation, memory, or prior conclusions. Inputs are passed
**by file path only**. This is the dotfiles equivalent of bringing in an
outside engineer: no anchoring on what's already been decided, no rubber
stamping.

The reviewer's primary job is to **find a more elegant fix** if one exists,
including fixes that redesign the surrounding codebase when the right design
would resolve the root cause and other latent issues at once.

---

## Inputs contract

This skill accepts conclusions **only by file path**. Do not summarize or
restate the analysis in the prompt — the reviewer must read it themselves.

**Arguments:** $0

Tokens are classified by shape. **Disambiguation priority** — apply per
token, in order; first rule that matches wins:

1. **Token resolves to an existing file** (try as-given, then relative to
   CWD, then absolute):
   - `*.md` → markdown role (see role assignment below).
   - `*.patch` / `*.diff` → solutions source (distiller required).
   - any other extension or extensionless → AskUserQuestion. Do not guess.
2. `bug:<digits>` / `bz:<digits>` / `https://bugzilla.mozilla.org/show_bug.cgi?id=<digits>`
   → analysis source (intake required).
3. `D<digits>` / `https://phabricator.services.mozilla.com/D<digits>`
   → solutions source (distiller required).
4. `https://github.com/<owner>/<repo>/pull/<n>`
   → solutions source (distiller required).
5. URL ending in `.patch` or `.diff`
   → solutions source (distiller required).
6. Literal `diff` (and no file by that name in CWD)
   → solutions source: uncommitted working tree.
7. Literal `local` or `HEAD` (and no file by that name in CWD)
   → solutions source: branch tip vs `git merge-base`.
8. Token resolves to a git commit
   (`git rev-parse --verify "$tok^{commit}"` succeeds)
   → solutions source: that commit.
9. `--desc <text>` flag → analysis source: user free-text. The skill writes
   the text to a scratch file before invoking intake.
10. None of the above → AskUserQuestion. **Never silently fall back.**

**Role assignment for markdown files:** at most one analysis md and one
solutions md per invocation. First `*.md` token (in argument order) →
analysis; second `*.md` → solutions. A third `*.md` is rejected unless its
basename ends with `-review.md`, in which case it is the explicit output
path.

**Conflict rule:** at most one analysis source and one solutions source per
invocation. Two analysis-side or two solutions-side tokens →
AskUserQuestion. Never silently pick a winner.

**Output path resolution** (priority order):

1. Explicit token ending `-review.md`.
2. If any user-supplied `*.md` was given:
   `<dirname(that md)>/<bug-id-stripped-basename>-review.md`. Bug-id-strip
   rule: if basename matches `^bug-(\d+)-analysis$`, strip `-analysis`
   first — so sherlock's `bug-12345-analysis.md` produces
   `bug-12345-review.md`.
3. Else if a bug id is derivable (from `bug:<id>`, from front-matter of a
   scratch analysis doc, or from a Phab revision's commit message):
   `$PWD/bug-<id>-review.md`.
4. Else `$PWD/red-pen-review-<run-id>.md`.

Print the resolved output path before invoking the critic so the user can
abort.

If after parsing there is no analysis source, ask the user via
AskUserQuestion. Do not guess.

---

## Adapter step (only when non-md sources present)

If every supplied source is already an existing `*.md` file, **skip this
section entirely** and go to Pre-flight. (Sherlock Phase 2 always passes
two `*.md` paths, so it never triggers an adapter spawn.)

Otherwise, normalize non-md inputs into markdown docs in a scratch
directory at `~/.claude/red-pen-scratch/<run-id>/`, where `<run-id>` is
`<bug-id-or-arg-hash>-<utc-timestamp>-<4-char-suffix>`. The scratch dir
persists after the run for debugging; it is never auto-deleted.

Order is fixed and sequential. Each step waits for the previous to write
its output file before the next is invoked:

1. **Intake** — invoked only if no analysis md was supplied. Single
   `Agent` call:

   ```text
   Agent(
     subagent_type: "red-pen-intake",
     description: "Intake for <source-descriptor>",
     prompt: <descriptor + output-path + template-path; no conclusions>,
   )
   ```

   Confirm the output file exists and is non-empty before continuing. If
   intake reports an error, abort the skill — do not invoke the critic on
   partial inputs.

2. **Distiller** — invoked only if no solutions md was supplied **or** the
   solutions source is non-md (Phab revision, patch file, commit, working
   tree, GitHub PR, raw URL). Single `Agent` call, same discipline as
   intake.

3. **Critic** — same invocation as in *Spawn the reviewer* below. The
   resolved analysis-doc path and solutions-doc path (whether
   user-supplied or scratch) are passed to the critic exactly as today.

The intake and distiller subagents each return only short summaries to
this skill (paths and metadata). **Never** quote the body of an
intake/distiller doc into the critic's prompt. The critic reads files by
path; the skill is just a path-handler.

---

## Pre-flight

1. Confirm the analysis doc exists and is readable (Read tool). For
   adapter-produced scratch docs, this also confirms the adapter wrote
   non-empty output.
2. If a solutions doc was passed (or produced by the distiller), confirm
   it exists.
3. Resolve the output path per the rules in *Inputs contract*. If the
   resolved path already exists, append `-N` until unique (so re-running
   the skill produces a new review, never overwrites).
4. Identify the bug ID if present in the analysis doc (look for
   `Bug <id>` in the title, summary, or front-matter). Used only for
   naming.

---

## Spawn the reviewer

Single `Agent` invocation. Do **not** chain multiple reviewer calls — one
isolated review per skill run.

```text
Agent(
  subagent_type: "red-pen-critic",
  description: "Independent review of bug-<id> solutions",
  prompt: <see template below>,
)
```

### Prompt template

The prompt MUST contain only file paths and instructions — never the
content of those files, never a summary of prior findings.

```text
You are reviewing a proposed root-cause-analysis solution. You have NO prior
context — read every input fresh.

Inputs (read these directly with the Read tool):
- Analysis doc: <absolute path to analysis doc>
- Solutions doc: <absolute path to solutions doc, OR the same as analysis
  doc with a note: "read the ## Proposed Solutions section">
- Repo root: <absolute path>
- Output path for your review: <absolute path>

Your task:
1. Read the analysis doc and the solutions.
2. Verify cited file:line references against the actual source. Do not
   trust any claim until you have re-read the cited code.
3. Search for a more elegant fix — including codebase redesigns when a
   better design would also resolve other latent issues. See your system
   prompt for what counts as a redesign worth proposing.
4. Write your review to the output path using the structure in
   <skill-dir>/references/review-template.md.
5. Return a 4-line summary in the format your system prompt specifies.

Hard rules:
- No prior context. Trust nothing until verified against source.
- No editing of code or patches.
- No phantom citations. Open the file or admit you couldn't.
```

Replace `<skill-dir>` with the absolute path to this skill's directory so the
reviewer can locate the template.

---

## Result handling

When the reviewer returns:

1. Read the review doc at the output path (Read tool, single call).
2. Extract the verdict, headline finding, and iteration recommendation from
   the review-doc front matter or first section.
3. Surface to the caller (whether human or another skill) with this exact
   shape, no additional commentary:

   ```markdown
   **Independent review** ([review doc](<relative-path-to-review-doc>))
   - Verdict: <verdict>
   - Headline: <one-sentence headline finding>
   - Iteration: <iteration recommendation>
   ```

4. Do **not** re-summarize the reviewer's reasoning. The review doc on disk
   is the canonical artifact; both human and caller can read it directly. Re-
   summarizing both wastes context and risks distorting the review.

---

## When called from another skill

The calling skill should:

- Pass absolute paths only.
- Pass the analysis doc *as it stands* — do not pre-edit it to "look better"
  for the reviewer.
- Wait for the review result before continuing its own workflow.
- Handle each verdict per its own rules. Common pattern (see sherlock Phase
  2 for the canonical version):
  - `approve` → proceed.
  - `approve-with-concerns` / `revise` → apply changes, re-invoke if changes
    are non-trivial.
  - `redesign` → escalate to user; do **not** silently expand scope.
  - `reject` / `needs-more-info` → loop back to the relevant analysis step.

---

## Standalone use

A user can invoke this skill directly without a calling skill. Beyond the
classic "two markdown docs" form, any of the wider input shapes documented
in *Inputs contract* work standalone too:

- `red-pen bug:1234567 D45678` — review the Phabricator revision against
  the Bugzilla bug.
- `red-pen <abs>/analysis.md foo.patch` — review a colleague's patch file
  against an existing analysis doc.
- `red-pen <abs>/analysis.md diff` — review uncommitted working-tree
  changes.
- `red-pen <abs>/analysis.md <commit-sha>` — review a specific commit.
- `red-pen --desc "frob crashes on second call" diff` — quick review
  against a free-text problem description.

Useful for vetting a proposed fix from a colleague's RCA write-up, a
Phabricator revision out for review, or your own in-progress changes
before posting.

---

## Hard rules for this skill

- Never include conclusions in the reviewer prompt — only paths. The same
  applies to the intake and distiller subagent prompts: pass descriptors
  and output paths, never embed prior analysis or summaries.
- Never invoke `red-pen-critic` more than once per skill run. The adapter
  subagents (`red-pen-intake`, `red-pen-distiller`) are each invoked at
  most once, and only before the critic. Order is fixed: intake →
  distiller → critic, sequential. None run in parallel. If the caller
  wants iteration, it invokes the skill again with revised inputs.
- Never modify the analysis doc or solutions doc, nor any user-supplied
  source artifact (Bugzilla bug, patch file, git commit, working tree,
  remote repo). The skill writes the review doc and any number of scratch
  transport docs in `~/.claude/red-pen-scratch/<run-id>/`; everything
  else is read-only.
- The distiller doc is mechanical-only (provenance + raw diff). Do not
  let the distiller editorialize. The critic reads the diff itself; it
  does not need a human-readable summary.

---

## Future work

- **`red-pen-loop` (deferred).** An iteration-driver skill that reads the
  verdict and either re-invokes the critic on revised inputs
  (`approve-with-concerns`, `revise`) or surfaces to the user (`redesign`,
  `reject`, `needs-more-info`). Two open design questions block this:
  (1) the `revise` verdict needs an "applier" subagent that mutates a
  *copy* of the solutions doc without violating the no-mutation rule
  above; (2) sherlock already encodes the verdict-ladder loop in its
  Phase 2, so a generic loop skill is only worth building once a
  non-sherlock caller appears. Build separately; do not embed iteration
  logic in this skill.
