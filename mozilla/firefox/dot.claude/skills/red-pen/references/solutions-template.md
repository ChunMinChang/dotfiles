---
source: {phab:D12345 | commit:abc123... | gh-pr:mozilla/gecko-dev#42 | working-tree | branch-tip | patch-file:<path> | url:<https-url>}
resolved-revision: {full-sha-or-phab-id-or-NA}
working-tree-head: {git-rev-parse-HEAD-output, ONLY for working-tree mode, else omit}
command: {the exact shell command that produced the diff below, copy-pasted verbatim}
captured-utc: {YYYY-MM-DDTHH:MM:SSZ}
files-changed: {N}
---

## Files changed

```
{verbatim `git diff --name-only` (or equivalent) output, no sorting, no edits}
```

## Unified diff

```diff
{verbatim unified diff, no edits, no normalization}
```

<!--
Notes for fillers (delete this block when emitting):

- The body of this doc must be byte-identical to the output of the
  `command:` field above (plus the section headers and code fences).
  No prose. No section headers other than the two above. No reordering.
  The critic reads the diff itself.
- For `working-tree` mode, `working-tree-head` records what the diff is
  *against* so the critic can detect drift if the user keeps editing.
- For `patch-file:` and `url:` modes, set `resolved-revision: NA` and
  put the path / URL in the `source:` field.
-->
