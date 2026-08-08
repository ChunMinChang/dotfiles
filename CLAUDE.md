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

**Cross-shell portability (bash + zsh):**

- `utils.sh`, `git/utils.sh`, `dot.settings_*`, and the
  `mozilla/firefox/*.sh` helpers are *sourced* into the interactive
  shell — zsh on macOS, bash elsewhere. Bash-isms in them fail at
  **runtime**, so `bash -n` and the syntax tests do not catch them.
- Known traps, each of which shipped as a real bug:
  - `[ x == y ]` — zsh's `[` builtin rejects `==` (`= not found`).
    Use `=` or `[[ ]]`.
  - `read -p` — in zsh `-p` means *read from the coprocess*, so it
    errors with `no coprocess` and leaves the variable empty. Use the
    `Confirm` helper in `utils.sh`.
  - Single-keypress reads differ (`read -n 1` vs `read -k 1`), so
    confirmations require Enter.
  - zsh does not word-split unquoted variables, so `for f in $files`
    and `cmd=$(...)` + `xargs $cmd` behave differently. Keep commands
    in arrays and expand with `"${arr[@]}"`.
  - zsh arrays are 1-based; avoid `${arr[0]}`.
- `test_shell_utils.sh` Test Suite 6 greps for these patterns and
  runs the sourced files under zsh. Add a guard there when you find
  a new one.
- Each sourced fragment starts with `# shellcheck shell=bash` (it has
  no shebang, and shellcheck has no zsh dialect), so `shellcheck` is
  a best-effort lint only — it will not flag the traps above.

**Platform detection:**

- `dot.bashrc` normalizes `uname -s` via a case statement
  (`MINGW*|MSYS*|CYGWIN*` → `windows`, `Darwin` → `darwin`,
  `Linux` → `linux`). Loads `~/.settings_{platform}` accordingly.
- Python side: `is_windows() / is_macos() / is_linux()` and
  `get_home_dir()` helpers in `setup.py` (top of file). All HOME
  resolution goes through `get_home_dir()`; tests can still assign
  `setup.HOME_DIR` directly to mock home.
- `can_create_symlinks()` probes via trial-symlink in a temp dir;
  `ensure_symlink_capability()` is the gate for symlink-creating
  steps and prompts the user to enable Developer Mode on Windows.
  Result is cached in `_SYMLINK_CHECK_DONE` so the prompt fires
  only once per `setup.py` invocation.

**Mozilla CLI tools (`--mozilla cli-tools`):**

- Split by who owns the install. `mozilla_cli_tools_init()` installs
  only what `./mach bootstrap` does *not* provide: `bmo-to-md` (cargo)
  and `profiler-cli` (npm).
- `MACH_BOOTSTRAP_CARGO_TOOLS` mirrors `BaseBootstrapper.CARGO_TOOLS`
  in firefox's `python/mozboot/mozboot/base.py`:
  `searchfox-cli`, `socorro-cli`, `stmo-cli`, `treeherder-cli`,
  `webspec-index`. Bootstrap's `ensure_cargo_tools()` unpacks a
  per-tool *prebuilt* toolchain artifact (win32/win64, macOS
  x86_64/aarch64, linux64/aarch64 all exist) and copies the binary
  into `~/.cargo/bin`. Gated behind
  `check_agentic_tools()`'s "Will you be using agentic coding tools to
  work on Firefox?" prompt, and skipped entirely under
  `--no-interactive`.
- `mach_bootstrap_cli_tools_init()` therefore *recommends* bootstrap
  rather than duplicating it, and only offers `cargo install` as a
  per-tool opt-in fallback (default No) for people with no checkout.
  Upstream builds all five from crates.io, so the fallback matches.
- Beware two false equivalences: bootstrap's `profiler-node-tools`
  artifact is the Firefox Profiler's bundled node-tools `.js` files,
  **not** a `profiler-cli` executable; and `bmo-to-md` has no
  toolchain definition upstream at all. Both stay ours.
- We never look for the Firefox checkout to decide whether bootstrap
  ran — we look at where it *writes*. `_cli_tool_present()` checks PATH
  and then `_cargo_bin_dir()`, which mirrors mozboot's `cargo_home()`
  (`$CARGO_HOME` if set, else `~/.cargo`) — a location that depends
  only on the environment, never the repo path. Keep the two in sync:
  hardcoding `~/.cargo` misses tools on a `$CARGO_HOME` machine and
  offers a pointless rebuild.
- `is_tool()` alone is not enough: it only consults PATH via
  `where`/`which`, and cargo's bin dir is only on PATH once
  `~/.cargo/env` is sourced, which the shell running `setup.py` may
  not have done.
- If upstream's `CARGO_TOOLS` gains a tool,
  `test_bootstrap_cargo_tools_matches_upstream_list` is the tripwire.

**Line endings (LF everywhere):**

- `.gitattributes` declares `* text=auto eol=lf` so checkouts always
  produce LF, regardless of the user's `core.autocrlf`.
- `git/config` sets `[core] autocrlf = input` to override Git for
  Windows' system-level `autocrlf = true` (which would otherwise
  rewrite LF→CRLF on checkout).
- `.editorconfig` enforces LF on the editor side for tools that
  respect it (VS Code, vim+plugin, JetBrains, etc.).
- If new files land with CRLF: `git add --renormalize .` re-stages
  them per the rules above; convert the working copy with a
  `\r\n` → `\n` rewrite if needed.

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

- `test_setup.py` - 139 tests (symlinks, file ops, main flow,
  Windows elevation/Dev Mode probes, Windows Dev Mode commit
  gate, claude-overlay branch-exists handling, stuck-state
  auto-switch, Windows post-checkout hook for re-materializing
  symlink-blob entries that git checkout failed to create)
- `test_shell_utils.sh` - 26 tests (functions, git utils, and
  Test Suite 6's guards against bash-isms that break zsh)
- `test_claude_security.py` - 23 tests (security hooks)
- `test_prompt_colors.sh` - 22 tests (prompt colors)
- `claude/test_session_sync.py` - 56 tests (parsing, rendering, manifest, discovery, env var)

Skill test suites (run manually, not part of `test_all.sh`):

- `mozilla/firefox/dot.claude/skills/triage/scripts/test_triage_scripts.py` -
  72 tests (scope profiles, pending store, BMO REST, apply-pending, render-report)
- `mozilla/firefox/dot.claude/skills/media-security-report/scripts/test_media_security_report.py` -
  54 tests (moz.yaml parsing, revision/BUG_COMPONENT fallbacks, checkout
  resolution, forge grammars, revision pinning, report requirements per
  channel, hygiene scan, policy/markdown sync)

Both run with `python3 -m unittest discover -s <that scripts dir>`.

**Coverage:**

- Path handling, file operations, symlink validation
- Append operations with deduplication
- Git workflow functions, verification functions
- Integration tests (--mozilla, --dev-tools, -v, --dry-run)
- Session sync: JSONL parsing, markdown rendering, tool pairing,
  manifest roundtrip, project disambiguation, env var fallback
