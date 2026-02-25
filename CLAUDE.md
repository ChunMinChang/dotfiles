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
- `claude/session_sync.py` - Session transcript export CLI
- `claude/CLAUDE.md.template` - Template appended to `~/.claude/CLAUDE.md`
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

## Session Sync (`claude/session_sync.py`)

**Architecture:** Single-file stdlib-only CLI with two-pass
streaming (metadata scan, then markdown render). Never holds
entire JSONL in memory.

**JSONL format quirks:**

- User text can be a plain string or a list of single chars
  (`extract_user_text()` handles both)
- Tool results pair with tool_use by `tool_use_id` — state
  machine in `render_markdown()` uses `pending_tool_uses` dict
- `file-history-snapshot`, `hook_progress` types: skip
- `system` with `subtype: "local_command"`: skip (noisy)
- `progress` type: subagent messages, excluded by default

**Project path disambiguation:**

- `compute_project_paths()` uses minimum trailing path
  components to make each cwd unique across all sessions
- Only computed in `sync-all`; single `export` uses basename

**State tracking:**

- `.claude-sync-manifest.json` in dest dir, mtime-based
- `needs_sync()` compares stored mtime; `--force` bypasses
- Atomic writes via `.tmp` + `os.rename()`

**Setup integration:** `claude_session_sync_init()` in
`setup.py` — symlinks script to `~/.local/bin`, appends
`CLAUDE.md.template` to `~/.claude/CLAUDE.md` with dedup
check on `## Session Transcript Sync` marker.

**Env var:** `$CLAUDE_TRANSCRIPT_DIR` — default dest for all
subcommands. `resolve_dest()` checks args first, then env.

## Testing

See [README.md](README.md#testing) for how to run tests.

**Test suites:**

- `test_setup.py` - 26 tests (symlinks, file ops, main flow)
- `test_shell_utils.sh` - 19 tests (functions, git utils)
- `test_claude_security.py` - 23 tests (security hooks)
- `test_prompt_colors.sh` - 22 tests (prompt colors)
- `claude/test_session_sync.py` - 56 tests (parsing, rendering, manifest, discovery, env var)

**Coverage:**

- Path handling, file operations, symlink validation
- Append operations with deduplication
- Git workflow functions, verification functions
- Integration tests (--mozilla, --dev-tools, -v, --dry-run)
- Session sync: JSONL parsing, markdown rendering, tool pairing,
  manifest roundtrip, project disambiguation, env var fallback
