# Implementation-skill discovery (Implement phase)

Sherlock does not assume it is the best tool for writing the fix. The
destination repo usually ships its own skills, that set **changes over time**,
and the user may prefer one of them. So the Implement phase begins by
**discovering what is available at runtime** and asking.

**Never hard-code a catalogue of skill names.** Any list in this file is an
illustration of what the classifier should do with what it finds, not a lookup
table. mozilla-central shipped 19 in-tree skills when this was written and the
in-tree `README.md` actively invites more.

---

## Where skills actually live

Inspect both project-local skill trees in every destination repository:
**`<repo-root>/.codex/skills/<name>/SKILL.md`** and
**`<repo-root>/.claude/skills/<name>/SKILL.md`**. A Firefox fix normally has the
Firefox checkout as one destination; Branch A/C work can add a separate upstream
library repository as another. Run discovery independently in each one.

These directories can hold a mix of:

- **Real directories** — skills committed to mozilla-central itself.
- **Symlinks into a dotfiles checkout** — personal and project overlays, including
  the Codex overlay installed by `setup.py`.

Both kinds are ordinary skills at runtime; the distinction only matters because
**symlinks break naive globbing** (see below).

Determine the root the same way `setup.py` does — a checkout is a gecko tree if
`<root>/mach` exists:

```bash
REPO_ROOT="$(git rev-parse --show-toplevel)"
```

## Step 1 — Enumerate

```bash
for SKILL_ROOT in "$REPO_ROOT/.codex/skills" "$REPO_ROOT/.claude/skills"; do
  [ -d "$SKILL_ROOT" ] || continue
  find -L "$SKILL_ROOT" -mindepth 2 -maxdepth 2 -name SKILL.md 2>/dev/null
done | sort -u
```

**`-L` is load-bearing.** Plain `find` does not descend into symlinked skill
directories, so a naive glob can silently miss the overlay. De-duplicate by
declared skill name while retaining the origin path and destination repo.

When the same declared name exists in both trees, use the `.codex` definition as
the native candidate if their behavior is equivalent. If they differ materially,
show both origins and require an explicit choice. A Claude-only definition is
guidance that Codex can read and follow; do not pretend it is a registered Codex
skill when it is not.

**Cross-check against the session's available-skills listing.** Anything on disk
but absent from that listing is not directly invocable in the current session.
It may still be offered as **read-and-follow guidance**, clearly labelled as such.

## Step 2 — Read the frontmatter

Extract `name`, `description`, and `when_to_use` in one pass. This handles the
two shapes that actually occur: folded scalars (`description: >`) and a missing
`name:` key (several alwu-tier skills omit it and derive the name from the
directory).

```bash
for SKILL_ROOT in "$REPO_ROOT/.codex/skills" "$REPO_ROOT/.claude/skills"; do
  [ -d "$SKILL_ROOT" ] || continue
  find -L "$SKILL_ROOT" -mindepth 2 -maxdepth 2 -name SKILL.md -exec awk '
  FNR==1 {n="";d="";g=0; k=split(FILENAME,p,"/"); dir=p[k-1]}
  FNR==1 && $0!~/^---/ {nextfile}
  FNR>1 && /^---[[:space:]]*$/ {printf "%-38s %s\n",(n==""?dir:n),substr(d,1,160); nextfile}
  /^name:/{sub(/^name:[[:space:]]*/,"");n=$0}
  /^(description|when_to_use):/{sub(/^[a-z_]+:[[:space:]]*/,"");t=$0;g=(t==">"||t=="|"||t==">-"||t=="|-");if(!g)d=d (d==""?"":" | ") t; next}
  g && /^[[:space:]]+/{sub(/^[[:space:]]+/,"");d=d (d==""?"":" ") $0; next}
  g && /^[^[:space:]]/{g=0}
' {} \;
done | sort
```

If `awk` is unavailable or the output looks wrong, read the opening frontmatter
of each `SKILL.md` with an available filesystem reader (for example,
`sed -n '1,40p'`) — do not depend on a tool-specific `Read(limit: …)` API.

## Step 3 — Classify by capability

Bucket each skill on **what its description says it does**, never on whether you
recognise the name. A skill added to the tree next month must classify correctly
without this file being touched.

| Bucket | Signal in the description | Consumed by |
|---|---|---|
| `implements` | writes or modifies source code (C++/Rust/JS/WebIDL, front-end, Android, l10n) | `Implement.2` |
| `shapes` | reorders, splits, squashes, or rewrites commits; manages the patch stack | `Implement.3` |
| `checks` | lint, build, test, format, or self-review gates | `Implement.4` |
| `files` | creates bugs or reports | `Consolidate` |
| `routes` | reviewer selection, submission | list only, out of scope |

Skills that match no bucket are ignored silently — do not list investigation,
profiling, or documentation skills as implementation candidates.

Narrow the `implements` bucket against the actual change: a skill scoped to
`dom/media`, Android, or Fluent is only a candidate when the approved option
touches that area. Use its `description` / `when_to_use` scope wording, and the
file list from the option's implementation overview.

## Step 4 — Ask

Present the candidates grouped by destination repo and bucket, using the
available user-input mechanism. Always include **"implement directly (no
skill)"** as an option. Show each candidate's name, origin (`.codex` or
`.claude`), availability (`invocable` or `guidance-only`), and one-line purpose
so the user is choosing on substance.

Do not pick silently, even when exactly one candidate matches — the point of the
step is that the user decides.

## Step 5 — Use what was chosen

Most in-tree skills are **behavioural overlays** — "You MUST use this skill when
working with C++…" — rather than delegated executors. They typically declare only
`name` and `description`, have no `argument-hint`, and perform no `$0` /
`$ARGUMENTS` substitution.

For a registered Codex skill, load it through the runtime's skill mechanism. For
an on-disk guidance-only skill, read its `SKILL.md` completely and follow it as
repository guidance. In both cases, read any required references exactly as that
skill directs, then implement with the absolute analysis and solutions paths in
scope. Never act on frontmatter alone.

A minority are genuine workflow skills with their own multi-step process. Read
what came back before assuming which kind you have.

### Reconciling a skill that wants its own worktree

Some implementation skills set up their own worktree and branch (for example, one
that creates `~/firefox-{bug_id}` on branch `bug-{bug_id}`). Sherlock has already
committed its proof tests to `sherlock/bug-<id>` in the main tree, so a fresh
worktree branched from trunk would **lose the proof tests** — and with them the
FAIL→PASS evidence that the whole run is built on.

Rule: branch the worktree **from `sherlock/bug-<id>`**, not from trunk, so the
test commits carry over. Then tell the skill, in the prompt, that the proof tests
already exist and where they are, so it does not re-author them.

```bash
WORKTREE_FORK=$(git rev-parse sherlock/bug-<id>)
git worktree add <worktree-path> -b <its-branch-name> sherlock/bug-<id>
```

Record `WORKTREE_FORK` and the worktree branch in plan.md Notes. Consolidation
must cherry-pick only `WORKTREE_FORK..<its-branch-name>`; using
`SHERLOCK_BASE..<its-branch-name>` would replay the proof tests onto a branch that
already contains them.

Also reconcile the commit-shape rules: a skill's own patch-split rules may agree
with Sherlock's on *separation* ("tests must be a separate patch from the fix"
for security bugs) while saying nothing about *ordering*. Sherlock's ordering
requirement still applies — see `Implement.3`.

## Degradation

Discovery never blocks the phase.

- **Neither `.codex/skills/` nor `.claude/skills/` exists** in a destination repo
  → say so in one line and implement directly there.
- **`find` unavailable or permission-denied** → enumerate the immediate child
  directories of both skill roots, read each `SKILL.md`, then continue.
- **Candidates found but none suitable** → say what was found and why it does not
  fit, then implement directly.

In practice a checkout may carry only one skill tree because an overlay is not
materialised in every worktree. Treat that as normal, not an error.

## Resume

Record in `plan.md` Notes: the **detected set**, the **timestamp**, and the
**user's pick** per bucket.

On `--resume`, re-run discovery — the tree may have changed — but carry the
recorded pick forward without re-asking, unless the chosen skill has disappeared,
in which case re-ask for that bucket only.
