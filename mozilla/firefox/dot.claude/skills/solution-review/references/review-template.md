# Solution Review — Bug {bug_id}

> Review of: [`{analysis-doc-basename}`]({relative-path-to-analysis-doc})
> Reviewed: {YYYY-MM-DD}
> Reviewer revision pin: `{short_hash}` (the reviewer's view of the source tree)

## Verdict

**`{approve | approve-with-concerns | revise | reject | redesign | needs-more-info}`**

> Choose exactly one. Definitions:
> - `approve` — the proposed solution is the right fix; ship it.
> - `approve-with-concerns` — the solution is correct, but the reviewer has
>   non-blocking suggestions (style, secondary improvements).
> - `revise` — the solution has a concrete defect (cited at file:line) that
>   must be fixed; the overall direction is right.
> - `reject` — the proposed solution does not address the root cause, or
>   addresses the wrong cause. Direction must change.
> - `redesign` — there is a structurally cleaner fix that addresses this root
>   cause **and** other latent issues. Scope exceeds the original solutions.
>   The caller must escalate to the user before pursuing.
> - `needs-more-info` — the analysis or solutions doc has gaps the reviewer
>   could not fill from the inputs alone. Call out specific questions in
>   *Open questions*.

## Headline finding

{1–2 sentences. The single most important thing the caller needs to know.
This is the only thing the calling skill will surface verbatim, so make it
count.}

## Better alternative

> The reviewer's primary section. Fill this in unless the verdict is `approve`.
> Choose the smallest scope that captures the right fix.

### Scope

`(i) tweak | (ii) different fix at a different layer | (iii) codebase redesign`

### Description

{What the alternative is, in concrete terms. Include code-shape (function
signatures, structural changes) where useful, NOT a full patch — that's the
implementer's job.}

### Why it is better

{One paragraph. What about this design fixes the root cause more cleanly,
restores an invariant, eliminates a class of bug, etc.}

### Latent issues this also fixes
> Required for scope (iii) redesign. Optional for (ii). Skip for (i).

| Issue | Citation | Why this design fixes it |
|-------|----------|--------------------------|
| {short description} | [`file:line`]({permalink}) | {one line} |
| {short description} | [`file:line`]({permalink}) | {one line} |

### Scope estimate
> Required for scope (ii) and (iii).

- Files touched: {rough count}
- Net diff: {rough line count}
- Migration cost / cross-cutting risk: {low / medium / high — one line why}

---

## Per-solution critique

> One subsection per option in the proposed solutions. Skip options that
> don't appear. Each finding cites `file:line` and is categorized:
> `[critical]` (blocks approval), `[important]` (should fix), `[minor]`
> (nice to have).

### Option {A}: {name}

**Addresses root cause?** {yes / partially / no — one line why}

**Findings**:
- `[critical]` {what's wrong} — [`file:line`]({permalink})
- `[important]` {what's questionable} — [`file:line`]({permalink})
- `[minor]` {what could be improved} — [`file:line`]({permalink})

### Option {B}: {name}

{Same shape.}

---

## Root cause re-check

> Include this section ONLY if the alternative or critique surfaced a gap in
> the original analysis. Otherwise, delete the section entirely.

### Verified Claims (re-checked)

| Claim from analysis | Status | Notes |
|---------------------|--------|-------|
| {claim} | ✓ confirmed / ✗ refuted / ~ shifted | {if shifted: actual file:line} |

### Claims I could not verify

- {claim} — needs {what evidence} to confirm or refute.

### Proximate vs structural cause

> Use this if the analysis identified a proximate cause but a structural
> cause is the real driver.

- **Proximate cause (per analysis)**: {restate}
- **Structural cause (reviewer's read)**: {description, with citations}
- **Why this matters**: {what bugs the structural fix would prevent that
  the proximate fix would not}

---

## Open questions

> Things the reviewer could not resolve from the inputs alone. The caller
> should answer these (or escalate to the user) before iterating.

- {question 1}
- {question 2}

---

## Iteration recommendation

> One of:
> - `accept` — caller proceeds with the proposed solution unchanged.
> - `revise <option-id>` — caller applies the cited changes to that option,
>   then re-invokes solution-review if the changes are non-trivial.
> - `adopt-alternative` — caller replaces proposed solutions with the *Better
>   alternative* above (after user confirmation if scope ≥ ii).
> - `pursue-redesign` — caller escalates the redesign proposal to the user
>   with the latent-issue list and scope estimate; does NOT silently expand
>   scope.
> - `escalate` — caller asks the user the open questions before continuing.

**Recommendation**: {one of the above}

**Reason**: {one sentence}
