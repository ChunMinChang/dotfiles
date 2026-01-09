# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

This is a personal dotfiles repository for managing cross-platform shell configurations (Linux and macOS). The repository provides a Python-based setup system that symlinks configuration files and loads modular shell scripts for common utilities, git workflows, and Mozilla Gecko development.

## Setup and Installation

**Install all common settings:**
```bash
python setup.py
```

**Install with Mozilla toolkit:**
```bash
python setup.py --mozilla          # All Mozilla tools
python setup.py --mozilla hg       # Just Mercurial config
python setup.py --mozilla gecko    # Just mach alias and machrc
python setup.py --mozilla tools    # Just moz-phab
python setup.py --mozilla rust     # Just Rust/Cargo environment
```

**Uninstall:**
```bash
bash uninstall.sh
```

## Configuration

### Customizing Paths

The repository uses a centralized configuration system (`config.sh`) that allows you to customize installation paths without modifying the code. All paths have sensible defaults that match standard conventions.

**Default paths:**
- Mozilla build directory: `~/.mozbuild`
- Local bin directory: `~/.local/bin`
- Work bin directory: `~/Work/bin`
- Cargo directory: `~/.cargo`
- Trash directory (Linux): `~/.local/share/Trash/files`
- Trash directory (macOS): `~/.Trash`

**To customize paths:**

Create `~/.dotfiles_config` and override any variables:

```bash
# Example ~/.dotfiles_config
DOTFILES_MOZBUILD_DIR="$HOME/my-custom-mozbuild"
DOTFILES_LOCAL_BIN_DIR="$HOME/bin"
DOTFILES_WORK_BIN_DIR="$HOME/custom-work/bin"
DOTFILES_CARGO_DIR="$HOME/.cargo"
```

**Available configuration variables:**
- `DOTFILES_MOZBUILD_DIR` - Mozilla build directory
- `DOTFILES_LOCAL_BIN_DIR` - Local binaries directory
- `DOTFILES_WORK_BIN_DIR` - Work-related binaries
- `DOTFILES_CARGO_DIR` - Rust cargo directory
- `DOTFILES_TRASH_DIR_LINUX` - Linux trash directory
- `DOTFILES_TRASH_DIR_DARWIN` - macOS trash directory

The configuration is loaded by both Python scripts and shell scripts, ensuring consistent paths throughout the system.

## Architecture

### Entry Point Flow

The shell initialization follows this chain:

1. **Platform entry points** (OS-specific):
   - Linux: `~/.bashrc` → symlinked or loads `dot.bashrc`
   - macOS ≥10.15: `~/.zshrc` → symlinked to `dot.zshrc` → loads `~/.bashrc`
   - macOS ≤10.14: `~/.bash_profile` → symlinked to `dot.bash_profile` → loads `~/.bashrc`

2. **Common initialization** (`dot.bashrc`):
   - Sets `DOTFILES=~/.dotfiles` (symlinked to this repo)
   - Loads `utils.sh` (cross-platform utilities)
   - Loads `git/utils.sh` (git aliases and functions)
   - Loads platform-specific settings: `~/.settings_{linux|darwin}` (symlinked from `dot.settings_{linux|darwin}`)

3. **Optional Mozilla settings** (appended to `dot.bashrc` by `setup.py --mozilla`):
   - `mozilla/gecko/alias.sh` - mach shortcuts and WebCodecs test aliases
   - `mozilla/gecko/tools.sh` - moz-phab and pernosco-submit setup

### Module Organization

- **`setup.py`**: Installation orchestrator. Creates symlinks, appends loader commands to existing configs, and handles git/hg configuration includes.

- **`utils.sh`**: Cross-platform utility functions including `RecursivelyFind`, `RecursivelyRemove`, `Trash`, and `HostHTTP` (starts local HTTP server).

- **`git/`**:
  - `config`: Git aliases (included in `~/.gitconfig` via setup.py)
  - `utils.sh`: Git workflow functions like `GitLastCommit`, `GitUncommit`, `GitAddExcept`, `CreateGitBranchForPullRequest`, and prompt customization

- **`mozilla/gecko/`**: Gecko development tools
  - `alias.sh`: Mach command shortcuts (`mb`, `mr`, `mc`, `mfmt`, etc.) and numerous WebCodecs WPT test aliases (`vf1`-`vf11`, `vd1`-`vd7`, `ve1`-`ve10`)
  - `tools.sh`: Auto-setup for moz-phab and pernosco-submit
  - `machrc`: Custom mach configuration (symlinked to `~/.mozbuild/machrc`)

- **`mozilla/hg/config`**: Mercurial configuration (included in `~/.hgrc`)

## Key Development Commands

### Git Workflow Utilities

```bash
# Open all files from last commit in editor
GitLastCommit vim     # In vim tabs
GitLastCommit code    # In VS Code

# Open all uncommitted/modified files
GitUncommit vim
GitUncommit code

# Stage files except specified ones
GitAddExcept -u file1 file2        # Add updated files except file1, file2
GitAddExcept -A path1 path2        # Add all files except path1, path2

# Create branch for upstream pull request
CreateGitBranchForPullRequest upstream 123
```

### Mozilla Gecko Development

**Build and run:**
```bash
mb              # ./mach build
mr              # ./mach run
mc              # ./mach clobber
mfb             # Format then build
```

**Code quality:**
```bash
mfmt            # ./mach clang-format
mfmtfor <path>  # Format specific path
mfmtuc          # Format uncommitted files
manal <file>    # ./mach static-analysis check
MozCheckDiff [commit-range]  # Check diff formatting and analysis
```

**Testing:**
```bash
mm              # mochitest
mg              # gtest
mw              # wpt
mt              # try server
vf1, vf2...     # WebCodecs VideoFrame WPT tests (vf1-vf11)
vd1, vd2...     # WebCodecs VideoDecoder WPT tests (vd1-vd7)
ve1, ve2...     # WebCodecs VideoEncoder WPT tests (ve1-ve10)
wcf             # Full-cycle WebCodecs test
```

**Utilities:**
```bash
UpdateCrate <crate-name>     # Update Rust crate and vendor
W3CSpec input.bs output.html # Generate W3C spec from bikeshed
```

### General Utilities

```bash
RecursivelyFind "*.ext"      # Find files recursively
RecursivelyRemove "*.ext"    # Delete files recursively
Trash file1 file2            # Move to trash (Linux: ~/.local/share/Trash/files)
HostHTTP [params]            # Start HTTP server (tries npx live-server, python3, python)
OpenWithWayland <cmd>        # Run command with Wayland flags (Linux only)
```

## Important Implementation Notes

### Setup Script Behavior

- `setup.py` is **non-destructive**: If target files exist, it appends loader commands rather than overwriting
- The script uses `os.path.samefile()` to detect existing symlinks before creating new ones
- Git config is included using `git config --global include.path`, not replaced
- Mozilla tools check for existence before installation and print helpful error messages

### Platform Detection

The `dot.bashrc` detects platform using `uname -s | tr '[:upper:]' '[:lower:]'` and loads the appropriate `~/.settings_{platform}` file. Platform-specific behavior:
- **Linux**: Enables git branch in prompt, sets `TRASH` path, provides `OpenWithWayland` function
- **macOS**: Relies on `.zshrc` or `.bash_profile` wrapper to source `.bashrc`

### Mozilla Tool Paths

The Mozilla tools expect specific directory structures:
- moz-phab: `~/.local/bin/moz-phab`
- pernosco-submit: `~/Work/bin/pernosco-submit` (Linux only, see `pernosco-submit_template`)

### Naming Conventions

This repository uses **language-specific naming conventions** rather than enforcing consistency across all languages. This follows best practices for each language and makes the code more familiar to developers.

**Python** (setup.py):
- **Functions and variables**: `snake_case` (follows PEP 8)
  - Examples: `print_hint()`, `print_warning()`, `git_init()`, `mozilla_init()`
- **Classes**: `PascalCase` (standard Python convention)
- **Constants**: `UPPER_CASE`

**Bash/Shell Scripts** (utils.sh, git/utils.sh, mozilla/gecko/*.sh, etc.):
- **Functions**: `PascalCase` (distinguishes from built-in Unix commands)
  - Examples: `PrintError()`, `GitLastCommit()`, `RecursivelyFind()`, `CreateGitBranchForPullRequest()`
- **Variables**: `snake_case`
  - Examples: `local cmd="$1"`, `git_config="..."`, `file_path="/path/to/file"`
- **Environment variables and constants**: `UPPER_CASE`
  - Examples: `DOTFILES`, `TRASH`, `SCRIPT_DIR`

**Rationale**:
- Python's PEP 8 is the official style guide and widely expected in the community
- Bash PascalCase functions are easily distinguished from Unix commands (e.g., `GitLastCommit` vs `git`, `PrintError` vs `echo`)
- Each language is internally consistent (most important for readability)
- Developers familiar with each language will recognize these conventions
- Following established conventions is better than inventing repository-specific ones

**For contributors**: When adding functions, use `snake_case` in Python files and `PascalCase` in shell scripts. Always maintain consistency within the file you're editing.

## Modification Guidelines

- When editing shell scripts, maintain cross-platform compatibility (bash-compatible syntax)
- New utilities should go in `utils.sh` for general use, `git/utils.sh` for git-specific functions
- Mozilla-specific additions belong in `mozilla/gecko/alias.sh` or `mozilla/gecko/tools.sh`
- Use the helper functions `PrintError()`, `PrintHint()`, `PrintWarning()` for consistent output formatting
- Always test modifications with `source ~/.bashrc` before committing
