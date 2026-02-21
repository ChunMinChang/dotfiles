# Claude Code Project Context

> For user-facing documentation (commands, setup, configuration),
> see [README.md](README.md). This file contains implementation
> details for Claude Code sessions working on this repo.

## Architecture

**Shell initialization flow:**

1. Platform entry: `~/.bashrc` (Linux) or
   `~/.zshrc`/`~/.bash_profile` (macOS)
2. Common init: `dot.bashrc` sets `DOTFILES`, loads
   `utils.sh`, `git/utils.sh`, platform settings
3. Optional: Mozilla tools
   (`mozilla/firefox/alias.sh`, `mozilla/firefox/tools.sh`)

**Module organization:**

- `setup.py` - Installation orchestrator
- `config.sh` - Centralized configuration
- `utils.sh` - Cross-platform utilities
- `git/config` - Git aliases (included in ~/.gitconfig)
- `git/utils.sh` - Git workflow functions
- `mozilla/firefox/alias.sh` - Mach shortcuts
- `mozilla/firefox/tools.sh` - pernosco-submit setup
- `mozilla/firefox/machrc` - Custom mach config
- `mozilla/firefox/dot.claude/` - Firefox Claude overlay

## Key Implementation Details

**Non-destructive setup:**

- Existing files preserved: appends loaders, not overwrites
- Uses `os.path.samefile()` to detect existing symlinks
- Git config uses `include.path` mechanism

**Platform detection:**

- Uses `uname -s | tr '[:upper:]' '[:lower:]'`
- Loads appropriate `~/.settings_{platform}` file

**Naming conventions:**

- Python: `snake_case` (PEP 8)
- Shell functions: `PascalCase`
- Variables: `snake_case`
- Constants/env vars: `UPPER_CASE`

**Rollback mechanism:**

- `ChangeTracker` records all changes during setup
- On failure: rollback in reverse order (LIFO)
- Restores symlinks, removes appended lines, unsets config

**Verification:**

- Validates symlinks, readability, bash syntax, git config
- Exit code 0 only if all verifications pass

**Error handling:**

- Functions return True/False/None (success/failure/skipped)
- `show_setup_summary()` with symbols
- Exit codes: 0=success, 1=failure, 130=Ctrl+C

## Testing

See [README.md](README.md#testing) for how to run tests.

**Test suites:**

- `test_setup.py` - 26 tests (symlinks, file ops, main flow)
- `test_shell_utils.sh` - 19 tests (functions, git utils)
- `test_claude_security.py` - 23 tests (security hooks)
- `test_prompt_colors.sh` - 22 tests (prompt colors)

**Coverage:**

- Path handling, file operations, symlink validation
- Append operations with deduplication
- Git workflow functions, verification functions
- Integration tests (--mozilla, --dev-tools, -v, --dry-run)
