# Personal Dotfiles

Cross-platform shell configuration for Linux and macOS
with enhanced git workflows and Mozilla Firefox development tools.

## Quick Start

```bash
python setup.py                        # Basic setup
python setup.py --mozilla              # Add Mozilla dev tools
python setup.py --claude-security      # Add Claude Code security hooks
python setup.py --claude-session-sync  # Add session transcript sync
python setup.py --all                  # Install everything
python setup.py --dry-run              # Preview changes first

# Firefox Claude settings (per-project)
python setup.py --install-firefox-claude /path/to/firefox

bash uninstall.sh                  # Remove dotfiles
```

## What Gets Installed

**Symlinks:** `~/.dotfiles`, `~/.bashrc`, `~/.settings_{platform}`
(+ `~/.zshrc` on macOS)

**Git config:** `git/config` included via `~/.gitconfig`

**Mozilla (optional):** Mach aliases, machrc, pernosco-submit,
Rust/Cargo environment

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

Install Firefox-specific Claude hooks and skills
(auto-format, auto-lint, skills) to any Firefox project.
Uses symlinks so updates propagate to all linked projects.

```bash
# Install (prompts for path)
python setup.py --install-firefox-claude
# Install to specific path
python setup.py --install-firefox-claude /path/to/firefox
# Uninstall
python setup.py --uninstall-firefox-claude /path/to/firefox
```

During installation you can provide a path to a
**tech-docs index file**. This is a markdown file that
lists generated technical documents so Claude can look up
relevant references on demand. If `CLAUDE.local.md`
already references the file, the prompt is skipped
on re-runs.

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

Restart Claude Code after installation for changes
to take effect.

## Testing

```bash
bash test_all.sh                           # All suites (90+ tests)

python3 test_setup.py                      # Setup + Claude security
bash test_shell_utils.sh                   # Shell utilities
python3 test_claude_security.py            # Security hooks
bash test_prompt_colors.sh                 # Prompt colors
python3 claude/test_session_sync.py        # Session sync (51 tests)
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
