---
name: red-pen
description: >
  RedPen — independent review of a proposed root-cause-analysis solution.
  Spawns an isolated reviewer with no shared memory; returns a structured
  review doc with verdict, alternatives, and concerns. Reusable from any
  RCA/bugfix skill (sherlock, fuzzbug-fix, triage) and standalone.
argument-hint: "<analysis-doc-path> [solutions-doc-path] [output-path]"
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

Parse from the argument string:
- First path that exists and ends with a markdown file → **analysis doc** (required).
- Second path → **solutions doc** (optional). If omitted, the reviewer reads
  the `## Proposed Solutions` section of the analysis doc.
- Third path → **output path** (optional). If omitted, default to
  `<dirname(analysis-doc)>/<basename-without-ext>-review.md`.

If the analysis doc path is missing, ask the user via AskUserQuestion. Do not
guess.

---

## Pre-flight

1. Confirm the analysis doc exists and is readable (Read tool).
2. If a solutions doc was passed, confirm it exists.
3. Resolve the output path. If it already exists, append `-N` until unique
   (so re-running the skill produces a new review, never overwrites).
4. Identify the bug ID if present in the analysis doc (look for `Bug <id>`
   in the title or summary). Used only for naming.

---

## Spawn the reviewer

Single `Agent` invocation. Do **not** chain multiple reviewer calls — one
isolated review per skill run.

```
Agent(
  subagent_type: "red-pen-reviewer",
  description: "Independent review of bug-<id> solutions",
  prompt: <see template below>,
)
```

### Prompt template

The prompt MUST contain only file paths and instructions — never the
content of those files, never a summary of prior findings.

```
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

```
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

A user can invoke this skill directly without a calling skill — pass an
analysis doc and a solutions doc (or one combined doc), and a review will
land at the resolved output path. Useful for vetting a proposed fix from a
colleague's RCA write-up.

---

## Hard rules for this skill

- Never include conclusions in the reviewer prompt — only paths.
- Never re-invoke the reviewer in a single skill run. One review per call.
  If the caller wants iteration, it invokes again with revised inputs.
- Never modify the analysis doc or solutions doc. The skill writes one new
  file (the review doc) and reads everything else.
