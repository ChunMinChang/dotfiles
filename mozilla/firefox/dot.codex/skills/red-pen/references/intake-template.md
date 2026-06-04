# Bug {bug_id_or_NONE} — {one-line summary from BMO summary or user desc}

> Source: `bugzilla:<id>` | `url:<...>` | `user free-text`
> Captured: {YYYY-MM-DDTHH:MM:SSZ}
> Mode: `description-only` | `full-thread`

## Summary (BMO comment 0 / user free-text)

{verbatim or near-verbatim summary, attribution-tagged}

## Reproduction (BMO comment N)

{steps to reproduce, attribution-tagged per comment}

## Observed behavior (BMO comment N)

{what actually happens, with attribution}

## Expected behavior (BMO comment N or reporter inference)

{what should happen, with attribution}

## Attached artifacts

| Type   | ID                | Description       | Source URL |
|--------|-------------------|-------------------|------------|
| patch  | {bz-attach-id}    | {description}     | {url}      |
| log    | {bz-attach-id}    | {description}     | {url}      |
| Phab   | D{revision-id}    | {description}     | {url}      |

## Reporter / commenter speculation (quoted, NOT reviewer-endorsed)

> {quote} — comment {N}, {commenter}
>
> {quote} — comment {N}, {commenter}

<!--
Notes for fillers (delete this block when emitting):

- This template has NO `## Proposed Solutions` section by design. The
  critic reads solutions from a separate doc; intake never produces
  solutions or root-cause framing.
- Provenance tags on section headers are mandatory.
- For `full-thread` mode, prepend a `## Thread digest` section above
  `## Summary` listing every comment as `comment N — author — first 80
  chars`.
- For `desc-file:` source, replace `## Summary (BMO comment 0)` with
  `## User-supplied problem statement (treat as reporter input, not
  verified fact)` and skip the BMO-specific sections that have no
  source content.
-->
