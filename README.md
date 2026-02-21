# Personal Dotfiles

Cross-platform shell configuration for Linux and macOS
with enhanced git workflows and Mozilla Firefox development tools.

## Quick Start

```bash
python setup.py                    # Basic setup
python setup.py --mozilla          # Add Mozilla dev tools
python setup.py --claude-security  # Add Claude Code security hooks
python setup.py --all              # Install everything
python setup.py --dry-run          # Preview changes first

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
|--------|----------|-------------|
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
bash test_all.sh                   # All suites (90 tests)

python3 test_setup.py              # Setup + Claude security
bash test_shell_utils.sh           # Shell utilities
python3 test_claude_security.py    # Security hooks
bash test_prompt_colors.sh         # Prompt colors
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
`DOTFILES_LOCAL_BIN_DIR`, `DOTFILES_WORK_BIN_DIR`,
`DOTFILES_CARGO_DIR`, `DOTFILES_TRASH_DIR_LINUX`,
`DOTFILES_TRASH_DIR_DARWIN`

## Architecture

See [CLAUDE.md](CLAUDE.md) for architecture details, module
organization, naming conventions, and implementation notes.
