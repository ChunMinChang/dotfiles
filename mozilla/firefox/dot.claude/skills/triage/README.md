# Firefox Bug Triage skill

Single-bug interactive triage for bugzilla.mozilla.org. Fetches a bug,
classifies signals, scopes Bugzilla searches to a profile
(`media` / `web-conferencing` / `media-and-web-conferencing` /
`graphics` / `android`), drafts a response, optionally generates a
test page, and stages a pending draft that can be applied to BMO via
REST after explicit user approval.

See `SKILL.md` for the full prompt; this file is the operator-facing
README.

## Invocation

- `/triage` — prompt for a bug number.
- `/triage 1234567` — analyse bug 1234567 (scope inferred).
- `/triage Bug 1234567`
- `/triage https://bugzilla.mozilla.org/show_bug.cgi?id=1234567`
- `/triage 1234567 scope:graphics` — override scope.
- `/triage 1234567 out:/path/to/dir` — one-shot output-root override.

## Outputs

Every artifact for one bug lives in one folder under `{OUTPUT_ROOT}`:

```
{OUTPUT_ROOT}/
├── triage-log.json                  # append-only audit array
└── bug-{ID}/
    ├── triage.md                    # the report
    ├── pending.json                 # staged draft (consumed by apply_pending.py)
    ├── test.html                    # optional test page
    ├── bug.json                     # snapshot used for the stale check
    ├── findings.json                # optional — codebase findings
    └── usage.json                   # optional — Bugzilla usage stats
```

## Configuration

`OUTPUT_ROOT` resolution order (first match wins):

1. `out:<path>` token on the `/triage` command (per-invocation).
2. `output_dir` in `~/.config/firefox-triage/config.toml`.
3. Interactive prompt — the skill asks where the folder should live
   and offers to persist the answer to the TOML.

There is **no built-in default**. If no source is set and the skill is
invoked non-interactively (e.g. running `apply_pending.py` directly),
the call exits with a clear error rather than guessing a location.

### TOML config — `~/.config/firefox-triage/config.toml`

```toml
output_dir    = "/home/cm/triage"
api_key       = "…"                 # optional
default_scope = "media"             # optional — fallback when neither
                                    #   inference nor scope: matches
```

The TOML reader is a minimal stdlib parser that understands top-level
scalars only (no sections, no arrays).

## API key (REST writes only)

Reads of public bugs work anonymously. To `apply` a draft you need a
BMO API key. Resolution order:

1. `api_key` in `~/.config/firefox-triage/config.toml`.
2. `$BMO_API_KEY` environment variable.
3. `~/.config/bmo/api_key` — single line, `chmod 600` recommended
   (warning emitted if world-readable).

Generate a key at <https://bugzilla.mozilla.org/userprefs.cgi?tab=apikey>.
The wrapper redacts the key from every log line and exception path;
`apply_pending.py --dry-run` lets you preview the calls without
issuing them.

## scripts/

| File | Role |
|---|---|
| `triage_paths.py` | Library + CLI — output-root resolution, per-bug path helpers, TOML reader/writer. CLI is used by the prompt-and-persist flow (`--get-output-dir`, `--set-output-dir PATH`, `--get-default-scope`, `--config-path`). |
| `bmo_rest.py` | Library — stdlib REST wrapper, key redaction, write-gate. |
| `pending_store.py` | Library — atomic JSON I/O for pending drafts, bug snapshots, and the audit log. |
| `scope_profiles.py` | Library — five profile tables + `infer_profile()`. |
| `apply_pending.py` | CLI — invoked on `apply {id}`. Accepts `--output-dir PATH`. Exit codes 0/1/2/3/4/5/6. |
| `render_report.py` | CLI — renders `{root}/bug-{id}/triage.md`. Accepts `--output-dir PATH`. |
| `test_triage_scripts.py` | stdlib unittest, 74 tests. |

### Tests

```sh
cd mozilla/firefox/dot.claude/skills/triage/scripts
python3 -m unittest test_triage_scripts
```

All tests are stdlib-only; no network is touched (urllib is mocked).

### Dry-run an apply

```sh
python3 mozilla/firefox/dot.claude/skills/triage/scripts/apply_pending.py \
    1234567 --dry-run
```

Prints the planned `PUT /bug/{id}` and `POST /bug/{id}/comment` calls,
issues none.

## Required external tools

| Tool | Path | Required? | Used for |
|---|---|---|---|
| `mcp__moz__get_bugzilla_bug` | MCP | yes (primary read) | Bug + comments + history fetch. |
| `bmo-to-md` | `~/.cargo/bin/bmo-to-md` | optional | Markdown render of a bug. |
| `searchfox-cli` | `~/.cargo/bin/searchfox-cli` | optional | Codebase search (Step 7). |
| `socorro-cli`, `profiler-cli` | not installed by default | optional | Skipped gracefully if absent. |

## Out of scope

This skill is **single-bug interactive only**. The following are
intentionally not implemented (hooks reserved):

- Batch from a buglist URL.
- Watch-list polling / stale-NI detection across sessions.
- Cron daemon mode.
- Wiki write-back via `/firefox-wiki:add`.

See `~/Work/worklog/mozilla/triage-skills-comparison.md` for a
landscape view of other triage tooling (`media-bug-triage`,
`alwu-claude-skills/triage`, `triage-wizard`) and when to use each.
