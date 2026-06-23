#!/usr/bin/env python3
"""On-disk store for pending triage drafts, bug snapshots, and the audit log.

Layout under the configured output root (see triage_paths.output_root()):

  {OUTPUT_ROOT}/
    triage-log.json                  Append-only JSON array of decision records.
    triage-bug-{id}/pending.json     Staged draft for one bug.
    triage-bug-{id}/bug.json         Snapshot of the bug we triaged against.

Writes are atomic (.tmp + os.replace). The triage-log append uses
fcntl.flock on POSIX to serialise the read-modify-write window; if the
lock can't be acquired within a few retries the entry is dropped to a
per-PID side file and a warning is emitted to stderr.
"""

import datetime
import errno
import json
import os
import sys
import time

import triage_paths

# fcntl is POSIX-only; on Windows we fall back to a best-effort append.
try:
    import fcntl  # type: ignore
except ImportError:  # pragma: no cover - non-POSIX path
    fcntl = None  # type: ignore


# ---------------------------------------------------------------------------
# Paths (thin delegators to triage_paths)
# ---------------------------------------------------------------------------


def state_dir():
    """Root of the triage state tree."""
    return triage_paths.output_root()


def pending_path(bug_id):
    return triage_paths.pending_path(bug_id)


def log_path():
    return triage_paths.log_path()


def bug_snapshot_path(bug_id):
    return triage_paths.bug_snapshot_path(bug_id)


# ---------------------------------------------------------------------------
# Atomic JSON I/O
# ---------------------------------------------------------------------------


def _atomic_write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp_path, path)


# ---------------------------------------------------------------------------
# Pending I/O
# ---------------------------------------------------------------------------


def load_pending(bug_id):
    """Return the pending payload dict, or None if no file exists."""
    path = pending_path(bug_id)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, IsADirectoryError):
        return None
    except (OSError, json.JSONDecodeError, ValueError) as e:
        sys.stderr.write("pending_store: cannot read {}: {}\n".format(path, e))
        return None


def save_pending(payload):
    """Write a pending payload. Returns the final path."""
    if "bug_id" not in payload:
        raise ValueError("save_pending: payload missing 'bug_id'")
    if "created_at" not in payload:
        raise ValueError("save_pending: payload missing 'created_at'")
    path = pending_path(payload["bug_id"])
    _atomic_write_json(path, payload)
    return path


def delete_pending(bug_id):
    """Remove the pending file. Returns True if a file was removed."""
    path = pending_path(bug_id)
    try:
        os.unlink(path)
        return True
    except FileNotFoundError:
        return False


# ---------------------------------------------------------------------------
# Bug snapshot I/O
# ---------------------------------------------------------------------------


def save_bug_snapshot(bug_id, bug):
    """Persist the bug dict we triaged against. Returns the final path."""
    path = bug_snapshot_path(bug_id)
    _atomic_write_json(path, bug)
    return path


def load_bug_snapshot(bug_id):
    """Return the saved bug snapshot dict, or None if absent/unreadable."""
    path = bug_snapshot_path(bug_id)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, IsADirectoryError):
        return None
    except (OSError, json.JSONDecodeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Stale detection
# ---------------------------------------------------------------------------


def is_stale(payload, last_change_time):
    """True if the bug changed after the draft was staged (created_at)."""
    if not payload or "created_at" not in payload or not last_change_time:
        return False
    return str(last_change_time) > str(payload["created_at"])


def is_stale_against_snapshot(bug_id, fresh_last_change_time):
    """True if the bug changed after the saved snapshot was taken.

    Prefer this over ``is_stale`` when a snapshot exists — the snapshot's
    last_change_time is what the draft was reasoned against, which is a
    stricter and more accurate comparison than draft.created_at.
    """
    snap = load_bug_snapshot(bug_id)
    if not snap or not fresh_last_change_time:
        return False
    snap_lct = snap.get("last_change_time")
    if not snap_lct:
        return False
    return str(fresh_last_change_time) > str(snap_lct)


# ---------------------------------------------------------------------------
# Audit log append
# ---------------------------------------------------------------------------


def _try_lock(fileobj, retries=3, backoff=0.1):
    if fcntl is None:
        return True
    for _ in range(retries):
        try:
            fcntl.flock(fileobj.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except (BlockingIOError, OSError) as e:
            if e.errno not in (errno.EAGAIN, errno.EACCES):
                return False
            time.sleep(backoff)
    return False


def append_log_entry(entry):
    """Append a record to triage-log.json under an exclusive lock."""
    path = log_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)

    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o644)
    try:
        with os.fdopen(fd, "r+", encoding="utf-8") as f:
            if not _try_lock(f):
                _fallback_append(entry, path)
                return
            f.seek(0)
            try:
                data = json.load(f)
                if not isinstance(data, list):
                    data = []
            except (json.JSONDecodeError, ValueError):
                data = []
            data.append(entry)
            f.seek(0)
            f.truncate()
            json.dump(data, f, indent=2, sort_keys=True)
            f.write("\n")
            if fcntl is not None:
                try:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                except OSError:
                    pass
    except OSError as e:
        sys.stderr.write("pending_store: log append failed: {}\n".format(e))
        _fallback_append(entry, path)


def _fallback_append(entry, primary_path):
    side = "{}.{}.tmp".format(primary_path, os.getpid())
    try:
        with open(side, "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(entry, sort_keys=True) + "\n")
        sys.stderr.write(
            "pending_store: could not lock {}; wrote entry to {} "
            "(merge manually)\n".format(primary_path, side)
        )
    except OSError as e:
        sys.stderr.write(
            "pending_store: failed to write fallback log {}: {}\n".format(side, e)
        )


# ---------------------------------------------------------------------------
# Convenience
# ---------------------------------------------------------------------------


def now_iso_utc():
    """ISO-8601 Z-suffixed timestamp, suitable for created_at fields."""
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
