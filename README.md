# Personal Dotfiles

Cross-platform shell configuration for Linux and macOS with enhanced git workflows and Mozilla Gecko development tools.

## Quick Start

```bash
# Install
python setup.py                    # Basic setup
python setup.py --dry-run          # Preview changes first
python setup.py --mozilla          # Add Mozilla dev tools
python setup.py --dev-tools        # Add pre-commit hooks
python setup.py --claude-security  # Add Claude Code security hooks
python setup.py --all              # Install everything

# Firefox Claude settings (per-project)
python setup.py --install-firefox-claude ~/Work/firefox

# Uninstall
bash uninstall.sh --dry-run        # Preview removal
bash uninstall.sh                  # Remove dotfiles
```

## What You Get

### All Platforms

**Symlinks created:**
- `~/.dotfiles` → this repository
- `~/.bashrc` → `dot.bashrc` (or loader appended if exists)
- `~/.settings_{linux|darwin}` → platform-specific settings

**Git configuration:**
- `git/config` included in `~/.gitconfig`

### Linux Specific

**Symlinks:**
- `~/.settings_linux` → `dot.settings_linux`

**Features:**
- Git branch in shell prompt
- Trash directory: `~/.local/share/Trash/files`
- `OpenWithWayland` command for running GUI apps

### macOS Specific

**Symlinks:**
- `~/.zshrc` → `dot.zshrc` (macOS ≥10.15)
- `~/.bash_profile` → `dot.bash_profile` (macOS ≤10.14)
- `~/.settings_darwin` → `dot.settings_darwin`

**Features:**
- Trash directory: `~/.Trash`
- zsh entry point that loads bash configuration

### Mozilla Development (Optional)

Run `python setup.py --mozilla` to add:
- Mach aliases and machrc
- pernosco-submit setup
- Rust/Cargo environment

## Available Commands

### Git Aliases (Short)

```bash
git st          # status
git br          # branch -v
git co          # checkout
git ci          # commit
git df          # diff --patience
git pl          # pull
git ps          # push
git rb          # rebase
git cp          # cherry-pick
```

### Git Aliases (Log)

```bash
git l           # Last 10 commits (one-line)
git la          # Last 20 commits, all branches
git lg          # Graph view (compact)
git ll          # Graph view (detailed with dates)
git lll         # Graph view (very detailed, 2-line)
git search "text"    # Search commit messages
git file-log <file>  # File history (one-line)
git file-history <file>  # File history with patches
```

### Git Workflow Functions

```bash
GitLastCommit vim              # Open last commit files in vim
GitUncommit code               # Open modified files in VS Code
GitAddExcept -u file1 file2    # Add all updated except file1, file2
CreateGitBranchForPullRequest upstream 123  # Create PR branch
GitDeleteBranch <branch> [remote]      # Delete local and remote branch
GitDeleteBranch -f <branch> [remote]   # Force delete unmerged branch
GitRenameBranch <old> <new> [remote]   # Rename local and remote branch
```

### Shell Utilities

```bash
RecursivelyFind "*.sh"         # Find files recursively
RecursivelyRemove "*.DS_Store" # Delete files recursively (with confirmation)
Trash file1 file2              # Move files to trash
HostHTTP                       # Start local HTTP server
```

### Mozilla Gecko Development

**Build & Run:**
```bash
mb              # ./mach build
mr              # ./mach run
mc              # ./mach clobber
mfb             # Format then build
```

**Code Quality:**
```bash
mfmt            # Format all files
mfmtfor <path>  # Format specific path
mfmtuc          # Format uncommitted files
manal <file>    # Static analysis check
MozCheckDiff    # Check diff formatting
```

**Testing:**
```bash
mm              # mochitest
mg              # gtest
mw              # wpt
mt              # try server
vf1-vf11        # WebCodecs VideoFrame tests
vd1-vd7         # WebCodecs VideoDecoder tests
ve1-ve10        # WebCodecs VideoEncoder tests
wcf             # Full-cycle WebCodecs test
```

**Utilities:**
```bash
UpdateCrate <crate>      # Update Rust crate
W3CSpec input.bs out.html  # Generate W3C spec
```

## Claude Code (Optional)

### Security Hooks

Run `python setup.py --claude-security` to install **system-wide security hooks** that protect sensitive files across all Claude Code sessions.

**What it protects:**
- SSH keys (`~/.ssh/id_*`)
- Cloud credentials (AWS, GCP, Azure, DigitalOcean)
- Mozilla credentials (`~/.arcrc`, pernosco-submit scripts)
- API tokens (GitHub, npm, PyPI)
- Password managers (KeePass, 1Password, LastPass)
- Sensitive .env files (only those with API_KEY, SECRET, TOKEN keywords)

**What it allows:**
- All source code and project files
- Build artifacts (`~/.mozbuild/*`, `node_modules/`)
- Non-sensitive config files
- Safe .env files without secrets

**Commands:**
```bash
python setup.py --claude-security           # Install hooks
python setup.py --show-claude-hooks         # Show installed hooks
python setup.py --show-claude-security-log  # View blocked attempts log
python setup.py --remove-claude-security    # Uninstall hooks

# Emergency override (temporary)
export DOTFILES_CLAUDE_SECURITY_DISABLED=true
```

**How it works:**
- Installs `~/.dotfiles-claude-hooks/security-read-blocker.py`
- Registers PreToolUse hook in `~/.claude.json` (system-wide)
- Blocks Read/Bash/Grep/Glob tools from accessing sensitive files
- Logs all blocked attempts to `~/.dotfiles-claude-hooks/security-blocks.log`
- Uses content-based filtering for .env files (not all .env blocked)

**Important:** Restart Claude Code after installation for hooks to take effect.

See [CLAUDE_SECURITY.md](CLAUDE_SECURITY.md) for detailed documentation, troubleshooting, and advanced usage.

### Firefox Project Settings

Install Firefox-specific Claude hooks and skills to any Firefox/Gecko project. Uses symlinks for easy management across multiple repos.

**What's included:**
- `post-edit-format.sh` - Auto-formats files after edits (`./mach format`)
- `post-edit-lint.sh` - Auto-lints files after edits (`./mach lint --fix`)
- `should-format-lint.sh` - File extension filter for format/lint hooks
- `update-media-lib` skill - Guide for updating vendored media libraries

**Commands:**
```bash
# Install (prompts for Firefox project path)
python setup.py --install-firefox-claude

# Install to specific path
python setup.py --install-firefox-claude ~/Work/gecko

# Preview what would be installed
python setup.py --install-firefox-claude ~/Work/firefox --dry-run

# Uninstall
python setup.py --uninstall-firefox-claude ~/Work/firefox
```

**How it works:**
- Symlinks hooks/skills from `mozilla/firefox/dot.claude/` to target project
- Creates/updates `settings.local.json` (local-only, not committed)
- If existing settings found, prompts to merge or override
- Uninstall only removes dotfiles symlinks (preserves other settings)

**Why symlinks?**
- Single source of truth in dotfiles
- Updates to hooks/skills propagate to all linked projects
- Easy to manage multiple Firefox repos
- Sync across machines via git

**Important:** Restart Claude Code after installation for changes to take effect.

## Testing

Run tests to verify the installation works correctly:

```bash
# Run all test suites (90 tests total)
bash test_all.sh

# Or run individually:
python3 test_setup.py              # 26 tests - setup infrastructure + Claude security integration
bash test_shell_utils.sh           # 19 tests - shell utilities
python3 test_claude_security.py    # 23 tests - security hooks behavior
bash test_prompt_colors.sh         # 22 tests - prompt colors
```

**When to run:**
- After installation to verify everything works
- After modifying setup.py or shell scripts
- Before committing changes

**What they test:**
- `test_setup.py`: Symlink creation, file operations, configuration loading, setup flow, Claude security flags
- `test_shell_utils.sh`: All shell functions (CommandExists, Print functions, Git utils, RecursivelyFind, etc.)
- `test_claude_security.py`: Claude security hook functionality, installation, logging, cross-platform compatibility
- `test_prompt_colors.sh`: Prompt color formatting across bash and zsh

**See [TESTING.md](TESTING.md) for detailed testing documentation.**

## Configuration

Customize paths without modifying code. Create `~/.dotfiles_config`:

```bash
# Example ~/.dotfiles_config
DOTFILES_MOZBUILD_DIR="$HOME/my-mozbuild"
DOTFILES_LOCAL_BIN_DIR="$HOME/bin"
DOTFILES_TRASH_DIR_LINUX="$HOME/.trash"
```

**Available variables:**
- `DOTFILES_MOZBUILD_DIR` - Mozilla build directory (default: `~/.mozbuild`)
- `DOTFILES_LOCAL_BIN_DIR` - Local binaries (default: `~/.local/bin`)
- `DOTFILES_WORK_BIN_DIR` - Work binaries (default: `~/Work/bin`)
- `DOTFILES_CARGO_DIR` - Rust cargo (default: `~/.cargo`)
- `DOTFILES_TRASH_DIR_LINUX` - Linux trash (default: `~/.local/share/Trash/files`)
- `DOTFILES_TRASH_DIR_DARWIN` - macOS trash (default: `~/.Trash`)

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
