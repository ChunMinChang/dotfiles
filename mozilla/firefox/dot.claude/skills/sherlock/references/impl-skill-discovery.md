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

Skills resolve at **`<repo-root>/.claude/skills/<name>/SKILL.md`** — project-local,
not `~/.claude/skills/`. That directory holds a mix of:

- **Real directories** — skills committed to mozilla-central itself.
- **Symlinks into a dotfiles checkout** — personal, alwu, and media tiers, placed
  there by `setup.py`'s `install_firefox_claude()`.

Both kinds are ordinary skills at runtime; the distinction only matters because
**symlinks break naive globbing** (see below).

Determine the root the same way `setup.py` does — a checkout is a gecko tree if
`<root>/mach` exists:

```bash
REPO_ROOT="$(git rev-parse --show-toplevel)"
```

## Step 1 — Enumerate

```bash
find -L "$REPO_ROOT/.claude/skills" -mindepth 2 -maxdepth 2 -name SKILL.md 2>/dev/null | sort
```

**`-L` is load-bearing.** The `Glob` tool and plain `find` do not descend into
symlinked directories, and roughly half the entries here can be symlinks — so a
bare `.claude/skills/*/SKILL.md` glob silently reports only the in-tree skills
and misses every dotfiles-tier one. Use `find -L` via `Bash`.

Also check, best-effort:

- `$HOME/.claude/skills/*/SKILL.md` — the user tier. Often empty on machines that
  install into the repo instead, but valid in general.
- Marketplace plugins declared in `$REPO_ROOT/.claude/settings.json`. The in-tree
  README routes component-specific skills to the `firefox-aidev-plugins` /
  `aidev-plugins` marketplaces rather than into the tree; those live under
  `~/.claude/plugins/marketplaces/` and are invoked as `plugin:skill`.

Union the results and de-duplicate by skill name, remembering which tier each came
from (a dotfiles symlink shadowing an in-tree name is possible).

**Cross-check against the session's available-skills listing.** Per the in-tree
README, every skill's description is loaded into context at session start. So
anything on disk but absent from that listing is not actually invocable — report
it as present-but-unavailable rather than offering it.

## Step 2 — Read the frontmatter

Extract `name`, `description`, and `when_to_use` in one pass. This handles the
two shapes that actually occur: folded scalars (`description: >`) and a missing
`name:` key (several alwu-tier skills omit it and derive the name from the
directory).

```bash
find -L "$REPO_ROOT/.claude/skills" -mindepth 2 -maxdepth 2 -name SKILL.md -exec awk '
  FNR==1 {n="";d="";g=0; k=split(FILENAME,p,"/"); dir=p[k-1]}
  FNR==1 && $0!~/^---/ {nextfile}
  FNR>1 && /^---[[:space:]]*$/ {printf "%-38s %s\n",(n==""?dir:n),substr(d,1,160); nextfile}
  /^name:/{sub(/^name:[[:space:]]*/,"");n=$0}
  /^(description|when_to_use):/{sub(/^[a-z_]+:[[:space:]]*/,"");t=$0;g=(t==">"||t=="|"||t==">-"||t=="|-");if(!g)d=d (d==""?"":" | ") t; next}
  g && /^[[:space:]]+/{sub(/^[[:space:]]+/,"");d=d (d==""?"":" ") $0; next}
  g && /^[^[:space:]]/{g=0}
' {} \; | sort
```

If `awk` is unavailable or the output looks wrong, fall back to `Read` on each
`SKILL.md` with `limit: 20` — the frontmatter is always at the top.

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

Present the candidates grouped by bucket via `AskUserQuestion`, one question per
bucket that has candidates. Always include **"implement directly (no skill)"** as
an option. Show each candidate's name and a one-line purpose so the user is
choosing on substance.

Do not pick silently, even when exactly one candidate matches — the point of the
step is that the user decides.

## Step 5 — Use what was chosen

Most in-tree skills are **behavioural overlays** — "You MUST use this skill when
working with C++…" — rather than delegated executors. They typically declare only
`name` and `description`, have no `argument-hint`, and perform no `$0` /
`$ARGUMENTS` substitution.

So "use" means: `Skill(<name>)` to load its guidance into the turn, then implement
under that guidance, passing the relevant absolute doc paths in the prompt text.
This is the same pattern Sherlock already uses for `red-pen`.

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
git worktree add <worktree-path> -b <its-branch-name> sherlock/bug-<id>
```

Also reconcile the commit-shape rules: a skill's own patch-split rules may agree
with Sherlock's on *separation* ("tests must be a separate patch from the fix"
for security bugs) while saying nothing about *ordering*. Sherlock's ordering
requirement still applies — see `Implement.3`.

## Degradation

Discovery never blocks the phase.

- **No `.claude/skills/` directory** (non-gecko repo, or a checkout without the
  overlay materialised) → say so in one line and implement directly.
- **`find` unavailable or permission-denied** → fall back to `ls -d
  "$REPO_ROOT"/.claude/skills/*/` and `Read`, then continue.
- **Candidates found but none suitable** → say what was found and why it does not
  fit, then implement directly.

In practice a checkout may carry only the in-tree skills, because the dotfiles
overlay is committed to a side branch and is not materialised on every worktree.
Treat "only in-tree skills present" as the normal case, not an error.

## Resume

Record in `plan.md` Notes: the **detected set**, the **timestamp**, and the
**user's pick** per bucket.

On `--resume`, re-run discovery — the tree may have changed — but carry the
recorded pick forward without re-asking, unless the chosen skill has disappeared,
in which case re-ask for that bucket only.
