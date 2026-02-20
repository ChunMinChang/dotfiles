# Personal Dotfiles

Cross-platform shell configuration for Linux and macOS with enhanced git workflows and Mozilla Gecko development tools.

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

**Symlinks:** `~/.dotfiles`, `~/.bashrc`, `~/.settings_{platform}` (+ `~/.zshrc` on macOS)

**Git config:** `git/config` included via `~/.gitconfig`

**Mozilla (optional):** Mach aliases, machrc, pernosco-submit, Rust/Cargo environment

## Key Commands

### Git

```bash
git st / br / co / ci / df / pl / ps / rb / cp   # status, branch, checkout, commit, diff, pull, push, rebase, cherry-pick
git l / la / lg / ll / lll                        # Log views (one-line, all branches, graph variants)
git search "text"                                 # Search commit messages
git file-log <file>                               # File history
```

### Git Workflow

```bash
GitLastCommit vim              # Open last commit files in editor
GitUncommit code               # Open modified files in editor
GitAddExcept -u file1 file2    # Add all updated except listed files
GitDeleteBranch <branch>       # Delete local and remote branch
GitRenameBranch <old> <new>    # Rename local and remote branch
```

### Shell

```bash
RecursivelyFind "*.sh"         # Find files recursively
RecursivelyRemove "*.DS_Store" # Delete files recursively (with confirmation)
Trash file1 file2              # Move files to trash
HostHTTP                       # Start local HTTP server
```

### Mozilla Gecko

```bash
mb / mr / mc / mfb             # Build, run, clobber, format+build
mfmt / mfmtfor / mfmtuc       # Format: all, path, uncommitted
mm / mg / mw / mt              # Test: mochitest, gtest, wpt, try
UpdateCrate <crate>            # Update Rust crate
```

## Claude Code (Optional)

### Security Hooks

System-wide hooks that protect sensitive files (SSH keys, cloud credentials, API tokens, password managers) across all Claude Code sessions.

```bash
python setup.py --claude-security           # Install
python setup.py --show-claude-hooks         # Show installed hooks
python setup.py --show-claude-security-log  # View blocked attempts
python setup.py --remove-claude-security    # Uninstall
```

See [CLAUDE_SECURITY.md](CLAUDE_SECURITY.md) for details.

### Firefox Project Settings

Install Firefox-specific Claude hooks and skills (auto-format, auto-lint, skills) to any Gecko project. Uses symlinks so updates propagate to all linked projects.

```bash
python setup.py --install-firefox-claude                    # Install (prompts for path)
python setup.py --install-firefox-claude /path/to/firefox   # Install to specific path
python setup.py --uninstall-firefox-claude /path/to/firefox # Uninstall
```

During installation you can provide a path to a **tech-docs index file**. This is a markdown file that lists generated technical documents so Claude can look up relevant references on demand. If `CLAUDE.local.md` already references the file, the prompt is skipped on re-runs.

Example `INDEX.md`:

```markdown
# Tech Docs Index

| Domain | Document | Description |
|--------|----------|-------------|
| WebCodecs | [webcodecs.md](webcodecs.md) | Architecture, codec pipeline, process model |
| Media Playback | [media-playback.md](media-playback.md) | HTMLMediaElement, decoder lifecycle |
| MSE | [mse.md](mse.md) | Media Source Extensions, SourceBuffer management |
```

Generate these documents with the `/tech-doc` skill after installation.

Restart Claude Code after installation for changes to take effect.

## Testing

```bash
bash test_all.sh                   # Run all test suites (90 tests)

python3 test_setup.py              # Setup infrastructure + Claude security
bash test_shell_utils.sh           # Shell utilities
python3 test_claude_security.py    # Security hooks behavior
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

Available: `DOTFILES_MOZBUILD_DIR`, `DOTFILES_LOCAL_BIN_DIR`, `DOTFILES_WORK_BIN_DIR`, `DOTFILES_CARGO_DIR`, `DOTFILES_TRASH_DIR_LINUX`, `DOTFILES_TRASH_DIR_DARWIN`

---

## For Claude Code

### Architecture

**Shell initialization flow:**
1. Platform entry: `~/.bashrc` (Linux) or `~/.zshrc`/`~/.bash_profile` (macOS)
2. Common init: `dot.bashrc` sets `DOTFILES`, loads `utils.sh`, `git/utils.sh`, platform settings
3. Optional: Mozilla tools (`mozilla/firefox/alias.sh`, `mozilla/firefox/tools.sh`)

**Module organization:**
- `setup.py` - Installation orchestrator (symlinks, loaders, git config)
- `config.sh` - Centralized configuration (sourced by both Python and shell)
- `utils.sh` - Cross-platform utilities (RecursivelyFind, Trash, HostHTTP, Print functions)
- `git/config` - Git aliases (included in ~/.gitconfig)
- `git/utils.sh` - Git workflow functions (GitLastCommit, GitUncommit, GitAddExcept, etc.)
- `mozilla/firefox/alias.sh` - Mach shortcuts and WebCodecs test aliases
- `mozilla/firefox/tools.sh` - pernosco-submit setup
- `mozilla/firefox/machrc` - Custom mach config (symlinked to ~/.mozbuild/machrc)
- `mozilla/firefox/dot.claude/` - Firefox Claude hooks/skills overlay (symlinked per-project)

### Key Implementation Details

**Non-destructive setup:**
- Existing files preserved: appends loader commands instead of overwriting
- Uses `os.path.samefile()` to detect existing symlinks
- Git config uses `include.path` mechanism

**Platform detection:**
- Uses `uname -s | tr '[:upper:]' '[:lower:]'`
- Loads appropriate `~/.settings_{platform}` file

**Naming conventions:**
- Python (setup.py): `snake_case` for functions/variables (PEP 8)
- Shell scripts: `PascalCase` for functions (distinguishes from Unix commands)
- Variables: `snake_case`
- Constants/env vars: `UPPER_CASE`

**Rollback mechanism:**
- `ChangeTracker` class records all changes during setup
- On failure: offers to rollback changes in reverse order (LIFO)
- Restores previous symlinks, removes appended lines, unsets git config

**Verification:**
- After setup: validates symlinks, file readability, bash syntax, git config
- Exit code 0 only if all verifications pass
- ~300ms overhead

**Error handling:**
- All functions return True/False/None (success/failure/skipped)
- `show_setup_summary()` displays clear results with ✓/✗/⊘ symbols
- Proper exit codes: 0=success, 1=failure, 130=Ctrl+C

### Testing

**Test suites:**
- `test_setup.py` - 22 tests covering setup.py (symlinks, file ops, verification, main flow)
- `test_shell_utils.sh` - 19 tests covering shell utilities (functions, syntax, git utils)

**Run before:**
- Committing changes to setup.py or shell scripts
- Refactoring core functionality
- Adding new features

**Coverage:**
- Path handling, file operations, symlink creation/validation
- Append operations with deduplication and substring handling
- Git workflow functions, verification functions
- Integration tests with various flags (--mozilla, --dev-tools, -v, --dry-run)
