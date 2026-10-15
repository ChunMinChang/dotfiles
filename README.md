# Personal Dotfiles

Cross-platform shell configuration for Linux, macOS, and
Windows (Git Bash / mozilla-build MSYS2) with enhanced git
workflows and Mozilla Firefox development tools.

## Quick Start

```bash
python setup.py                        # Basic setup
python setup.py --mozilla              # Add Mozilla dev tools
python setup.py --claude-security      # Add Claude Code security hooks
python setup.py --claude-session-sync  # Add session transcript sync
python setup.py --all                  # Install everything
python setup.py --dry-run              # Preview changes first

# Firefox agent settings (per-project)
python setup.py --install-firefox-claude /path/to/firefox
python setup.py --install-firefox-codex /path/to/firefox

bash uninstall.sh                  # Remove dotfiles
```

## What Gets Installed

**Symlinks:** `~/.dotfiles`, `~/.bashrc`, `~/.settings_{platform}`
(+ `~/.zshrc` on macOS).
On Windows, `{platform}` is `windows` (Git Bash / MSYS2 / Cygwin).

**Windows note:** `setup.py` creates symlinks, which require either
Developer Mode (Settings → System → For developers → Developer Mode)
or running the script as Administrator. The installer will probe
symlink capability and prompt before any symlink-creating step.
Mozilla toolkit aliases are skipped on Windows; Firefox dev on
Windows uses `mozilla-build` directly.

For `--install-firefox-claude` and `--install-firefox-codex`,
setup.py refuses to commit overlay branches on Windows unless
Developer Mode is enabled — this guarantees the committed symlink
entries (mode 120000) can be checked out from any shell on the
machine.

**Git config:** `git/config` included via `~/.gitconfig`, plus
`git restack` (symlinked into `~/.local/bin` as `git-restack`)

**Mozilla (optional):** Mach aliases, machrc, pernosco-submit,
Rust/Cargo environment, plus the CLI tools Firefox skills rely on
(`bmo-to-md`, `profiler-cli`).

> **Run `./mach bootstrap` in your Firefox checkout too.** It installs
> `searchfox-cli`, `socorro-cli`, `stmo-cli`, `treeherder-cli` and
> `webspec-index` into `~/.cargo/bin` as prebuilt binaries when you
> answer yes to *"Will you be using agentic coding tools to work on
> Firefox?"*. `--mozilla cli-tools` deliberately does not duplicate
> that — it detects those tools and only offers a slower local
> `cargo install` build as a fallback if you have no checkout.
> (`./mach bootstrap --no-interactive` skips them, so use the
> fallback in that case.)

**Node/npm:** if `./mach bootstrap` has run, its Node install is added
to your PATH (appended, so any real Node install still wins). That's
what makes `markdownlint` and `profiler-cli` reachable. Our own
`npm install -g` always uses an explicit `--prefix` under
`~/.local`, so nothing is ever written into Mozilla's `~/.mozbuild`
tree — and a bootstrap Node update can't take those packages with it.
Tools declaring a newer Node than you have will warn and ask before
installing, rather than being silently skipped.

## Key Commands

### Git

```bash
git st / br / co / ci    # status, branch, checkout, commit
git df / pl / ps         # diff, pull, push
git rb / cp              # rebase, cherry-pick
git l / la / lg / ll     # Log views (one-line, all, graph)
git search "text"        # Search commit messages
git file-log <file>      # File history
```

### Git Workflow

```bash
GitLastCommit vim              # Open last commit files in editor
GitUncommit code               # Open modified files in editor
GitAddExcept -u file1 file2    # Add all except listed files
GitDeleteBranch <branch>       # Delete local+remote branch
GitRenameBranch <old> <new>    # Rename local+remote branch
```

### Keeping branches up to date: `git restack`

Fast-forwards the base branch from its upstream, then rebases the
current branch (or the branches you name) onto it. Works in any repo:

```bash
git restack                  # update base, rebase current branch onto it
git restack a b              # restack branches a and b (stacks detected)
git restack --push           # also push the base to <base>@{push}
git restack --push=origin    # ... or to a named remote
git restack --autostash      # stash local changes around the rebase
git restack -n               # show the plan only
```

Defaults come from git itself. The base is `restack.base`, else what
`upstream/HEAD` or `origin/HEAD` points to, else `main` or `master`.
Its upstream is `<base>@{upstream}`. Override with `--base` and
`--upstream <remote>/<branch>`.

*Layers* are long-lived branches kept on top of the base (e.g.
Firefox's `claude-overlay`/`codex-overlay`). They are always rebased,
and branches built on them follow them. Configure per repo:

```bash
git config --add restack.layer claude-overlay
git config --add restack.layer codex-overlay
git config restack.push origin          # push the base by default
git config remote.pushDefault origin    # make bare `git push` go to your fork
```

Each branch's parent is detected before anything moves, even if its
layer was rewritten, deleted or recreated since. Only the current
branch is rebased in the working tree; others are rebased in memory
(`git merge-tree`) and branches open in other worktrees are rebased
there if clean. On a conflict that branch and anything stacked on it
are left as they were, and the summary says how to finish by hand.

To find what a branch left alone for months was built on, each run
notes the layers' tips and where it placed each branch in
`.git/restack-tips` (shared by all worktrees). An entry is dropped once
no other local branch contains it, so the file follows your live
branches, not time. It is only a hint: deleting it is always safe, and
it goes away with the repository. A branch placed on the base that
carries a commit titled like a layer's (e.g. an old `Install Claude
overlay`) gets a warning with the `git rebase --onto` to move it.

### Shell

```bash
RecursivelyFind "*.sh"         # Find files recursively
RecursivelyRemove "*.DS_Store" # Delete files (with confirm)
Trash file1 file2              # Move files to trash
HostHTTP                       # Start local HTTP server
```

### Mozilla Firefox

```bash
mb / mr / mc / mfb             # Build, run, clobber, fmt+build
mfmt / mfmtfor / mfmtuc       # Format: all, path, uncommitted
mm / mg / mw / mt              # Test: mochi, gtest, wpt, try
UpdateCrate <crate>            # Update Rust crate
```

## Claude Code (Optional)

### Security Hooks

System-wide hooks that protect sensitive files
(SSH keys, cloud credentials, API tokens, password managers)
across all Claude Code sessions.

```bash
python setup.py --claude-security           # Install
python setup.py --show-claude-hooks         # Show hooks
python setup.py --show-claude-security-log  # View log
python setup.py --remove-claude-security    # Uninstall
```

See [CLAUDE_SECURITY.md](CLAUDE_SECURITY.md) for details.

### Session Sync

Export Claude Code session transcripts (JSONL) to
readable markdown or raw copies, with batch sync and
manifest-based state tracking.

```bash
python setup.py --claude-session-sync   # Install
```

This symlinks `claude-session-sync` into `~/.local/bin`
and appends session-sync instructions to `~/.claude/CLAUDE.md`.

Set `CLAUDE_TRANSCRIPT_DIR` to avoid repeating the destination:

```bash
export CLAUDE_TRANSCRIPT_DIR=~/transcripts   # add to .bashrc
```

When set, all commands use it as the default `<dest>`.
An explicit `<dest>` argument still takes priority.

#### Commands

**Export a single session:**

```bash
claude-session-sync export <session.jsonl>                          # uses $CLAUDE_TRANSCRIPT_DIR
claude-session-sync export <session.jsonl> ~/transcripts            # explicit dest
claude-session-sync export <session.jsonl> --format raw             # Copy JSONL as-is
claude-session-sync export <session.jsonl> --force                  # Re-export even if unchanged
claude-session-sync export <session.jsonl> --include-subagents      # Include subagent messages
```

**Batch sync all sessions:**

```bash
claude-session-sync sync-all                                        # uses $CLAUDE_TRANSCRIPT_DIR
claude-session-sync sync-all ~/transcripts --project-filter ~/Work  # Only projects under ~/Work
claude-session-sync sync-all --force                                # Re-export everything
claude-session-sync sync-all --include-subagents                    # Include subagent messages
```

**Check sync status:**

```bash
claude-session-sync status                                          # uses $CLAUDE_TRANSCRIPT_DIR
claude-session-sync status ~/transcripts --project-filter ~/Work
```

**Export current session (auto-detect by cwd):**

```bash
claude-session-sync export-current                                  # uses $PWD + $CLAUDE_TRANSCRIPT_DIR
claude-session-sync export-current --project-dir ~/Work/firefox
```

#### Output Structure

```
~/transcripts/
  firefox/                          # Project name (from cwd)
    2026-02-24_9191a42c.md          # Markdown transcript
  worklog/
    2026-02-24_abc12345.md
  .claude-sync-manifest.json        # Tracks sync state (mtime-based)
```

When `sync-all` encounters projects with the same basename
(e.g., `/Work/X/Z` and `/Work/Y/Z`), it automatically uses
enough trailing path components to disambiguate (`X/Z/` vs `Y/Z/`).

### Firefox Project Settings

Install Firefox-specific agent hooks and skills to any Firefox
project. Uses symlinks so updates propagate to all linked projects.

```bash
# Install (prompts for path)
python setup.py --install-firefox-claude
# Install to specific path
python setup.py --install-firefox-claude /path/to/firefox
# Install Codex settings and rewritten skills
python setup.py --install-firefox-codex /path/to/firefox
# Uninstall
python setup.py --uninstall-firefox-claude /path/to/firefox
```

The Claude installer links `.claude/hooks`, `.claude/agents`,
`.claude/skills`, and `.claude/settings.local.json`. The Codex
installer links `.codex/config.toml`, `.codex/hooks`, `.codex/agents`,
and `.codex/skills` from `mozilla/firefox/dot.codex`. It also links
the Firefox `rumination` profile to `$CODEX_HOME/rumination.config.toml`
(or `~/.codex/rumination.config.toml`) because Codex does not support
`[profiles.*]` inside project-local `.codex/config.toml`. Use it with
`codex --profile rumination`.

During installation you can provide a path to a
**tech-docs index file**. This is a markdown file that
lists generated technical documents so the agent can look up
relevant references on demand.

For Claude, setup writes the reference to `CLAUDE.local.md`.
For Codex, there is no direct additive `CLAUDE.local.md`
equivalent that preserves `AGENTS.md` in the same directory:
`AGENTS.override.md` shadows `AGENTS.md`. Codex setup therefore
creates or updates a local `AGENTS.override.md` that includes a
snapshot of the current `AGENTS.md` content and appends the
tech-docs index reference. Re-run setup after `AGENTS.md`
changes to refresh that local snapshot.

Codex setup excludes `AGENTS.override.md` through `.git/info/exclude`,
not tracked `.gitignore`, and the Codex overlay commit prompt still
stages only `.codex/` and `.gitignore`.

Example `INDEX.md`:

```markdown
# Tech Docs Index

| Domain | Document | Description |
| ------ | -------- | ----------- |
| WebCodecs | webcodecs.md | Codec pipeline |
| Media | media-playback.md | Decoder lifecycle |
| MSE | mse.md | SourceBuffer management |
```

Generate these documents with the `/tech-doc` skill
after installation.

Restart the corresponding agent after installation for changes to
take effect.

## Testing

```bash
bash test_all.sh                           # All suites (90+ tests)

python3 test_setup.py                      # Setup + Claude security
bash test_shell_utils.sh                   # Shell utilities
python3 test_claude_security.py            # Security hooks
bash test_prompt_colors.sh                 # Prompt colors
python3 claude/test_session_sync.py        # Session sync (51 tests)
python3 git/test_restack.py                # git restack (56 tests)
```

See [TESTING.md](TESTING.md) for details.

## Configuration

Customize paths via `~/.dotfiles_config`:

```bash
DOTFILES_MOZBUILD_DIR="$HOME/my-mozbuild"
DOTFILES_LOCAL_BIN_DIR="$HOME/bin"
DOTFILES_TRASH_DIR_LINUX="$HOME/.trash"
```

Available: `DOTFILES_MOZBUILD_DIR`,
`DOTFILES_LOCAL_BIN_DIR`,
`DOTFILES_CARGO_DIR`, `DOTFILES_TRASH_DIR_LINUX`,
`DOTFILES_TRASH_DIR_DARWIN`

## Architecture

See [CLAUDE.md](CLAUDE.md) for architecture details, module
organization, naming conventions, and implementation notes.
