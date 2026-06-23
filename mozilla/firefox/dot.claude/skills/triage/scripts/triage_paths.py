#!/usr/bin/env python3
"""Single source of truth for triage on-disk paths.

The output root is resolved from (first match wins):

  1. An explicit override set by the calling CLI (see set_override()).
  2. ``output_dir`` in ~/.config/firefox-triage/config.toml.

If neither is set, output_root() raises OutputRootUnset so non-interactive
callers fail loudly rather than block on a prompt. The skill prompt asks
the user for a path when it sees the unset state and may persist the
answer to the TOML via persist_output_dir().

Per-bug layout under the root:

    {OUTPUT_ROOT}/
      triage-log.json
      triage-bug-{ID}/
        triage.md       pending.json    test.html
        bug.json        findings.json   usage.json

A small CLI is provided for the skill prompt to read/write config keys
without having to inline Python.
"""

import argparse
import os
import sys

CONFIG_PATH = os.path.expanduser("~/.config/firefox-triage/config.toml")

# Per-process override; intentionally not exported in the public API.
_OVERRIDE = None


class OutputRootUnset(Exception):
    """Raised when no output root can be determined from any source."""


# ---------------------------------------------------------------------------
# Override (CLI / tests)
# ---------------------------------------------------------------------------


def set_override(path):
    """Pin the output root for the duration of the current process."""
    global _OVERRIDE
    if path:
        _OVERRIDE = os.path.abspath(os.path.expanduser(path))
    else:
        _OVERRIDE = None


def clear_override():
    set_override(None)


# ---------------------------------------------------------------------------
# Minimal TOML reader (stdlib only, single-line top-level scalars)
# ---------------------------------------------------------------------------


def _read_toml_field(path, field):
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                if "=" not in stripped:
                    continue
                key, _, val = stripped.partition("=")
                if key.strip() != field:
                    continue
                val = val.split("#", 1)[0].strip()
                val = val.strip('"').strip("'")
                return val or None
    except OSError:
        pass
    return None


def _write_toml_field(path, field, value):
    """Set (or replace) a top-level scalar field. Preserves other lines.

    The parser is minimal — it doesn't handle TOML sections — but that's
    enough for the flat config layout this skill uses.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    new_line = '{} = "{}"\n'.format(field, value)
    if not os.path.isfile(path):
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(new_line)
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
        return
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    replaced = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if "=" not in stripped or stripped.startswith("#"):
            continue
        if stripped.split("=", 1)[0].strip() == field:
            lines[i] = new_line
            replaced = True
            break
    if not replaced:
        if lines and not lines[-1].endswith("\n"):
            lines[-1] = lines[-1] + "\n"
        lines.append(new_line)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.writelines(lines)
    os.replace(tmp, path)


# ---------------------------------------------------------------------------
# Config readers / writers
# ---------------------------------------------------------------------------


def config_path():
    return CONFIG_PATH


def read_output_dir_from_config():
    return _read_toml_field(CONFIG_PATH, "output_dir")


def read_default_scope_from_config():
    return _read_toml_field(CONFIG_PATH, "default_scope")


def read_api_key_from_config():
    return _read_toml_field(CONFIG_PATH, "api_key")


def persist_output_dir(value):
    """Write output_dir to the TOML config. Returns the resolved path."""
    abs_path = os.path.abspath(os.path.expanduser(value))
    _write_toml_field(CONFIG_PATH, "output_dir", abs_path)
    return abs_path


# ---------------------------------------------------------------------------
# Output root + per-bug paths
# ---------------------------------------------------------------------------


def output_root():
    """Return the resolved output root, or raise OutputRootUnset."""
    if _OVERRIDE:
        return _OVERRIDE
    val = read_output_dir_from_config()
    if val:
        return os.path.abspath(os.path.expanduser(val))
    raise OutputRootUnset(
        "no output_dir configured — set it in {} or pass an override "
        "via --output-dir".format(CONFIG_PATH)
    )


def bug_dir(bug_id):
    # Prefixed with the skill name so a triage run dir never collides with
    # another per-bug skill (e.g. /sherlock's sherlock-bug-<id>/) when both
    # are pointed at the same output root.
    return os.path.join(output_root(), "triage-bug-{}".format(int(bug_id)))


def report_path(bug_id):
    return os.path.join(bug_dir(bug_id), "triage.md")


def pending_path(bug_id):
    return os.path.join(bug_dir(bug_id), "pending.json")


def test_page_path(bug_id):
    return os.path.join(bug_dir(bug_id), "test.html")


def bug_snapshot_path(bug_id):
    return os.path.join(bug_dir(bug_id), "bug.json")


def log_path():
    return os.path.join(output_root(), "triage-log.json")


# ---------------------------------------------------------------------------
# CLI — used by the skill prompt to read/persist config without inline Python
# ---------------------------------------------------------------------------


def _cli(argv=None):
    parser = argparse.ArgumentParser(description="Read or write triage config keys.")
    parser.add_argument(
        "--get-output-dir",
        action="store_true",
        help="Print output_dir from config, or empty.",
    )
    parser.add_argument(
        "--set-output-dir",
        metavar="PATH",
        help="Persist output_dir to the TOML config.",
    )
    parser.add_argument(
        "--get-default-scope",
        action="store_true",
        help="Print default_scope from config, or empty.",
    )
    parser.add_argument(
        "--config-path",
        action="store_true",
        help="Print the absolute config file path.",
    )
    args = parser.parse_args(argv)

    if args.config_path:
        sys.stdout.write(CONFIG_PATH + "\n")
        return 0
    if args.get_output_dir:
        sys.stdout.write((read_output_dir_from_config() or "") + "\n")
        return 0
    if args.get_default_scope:
        sys.stdout.write((read_default_scope_from_config() or "") + "\n")
        return 0
    if args.set_output_dir is not None:
        resolved = persist_output_dir(args.set_output_dir)
        sys.stdout.write(resolved + "\n")
        return 0
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(_cli())
