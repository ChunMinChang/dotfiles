import argparse
import fileinput
import glob
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile

# On Windows the default stdout/stderr encoding is cp1252, which cannot
# encode the unicode glyphs we use in status output (->, check, cross).
# Reconfigure to utf-8 so prints work uniformly across cmd, PowerShell,
# Git Bash, and subprocess-captured runs.
if platform.system() == "Windows":
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, OSError):
            pass


def load_jsonc(path):
    """Load a JSON file that may contain // line comments and trailing commas."""
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    stripped = []
    for line in lines:
        s = line.lstrip()
        if s.startswith("//"):
            continue
        stripped.append(line)
    text = "".join(stripped)
    # Remove trailing commas before } or ]
    text = re.sub(r",\s*([\]}])", r"\1", text)
    return json.loads(text)


# Platform helpers
# ------------------------------------------------------------------------------


def is_windows():
    return platform.system() == "Windows"


def is_macos():
    return platform.system() == "Darwin"


def is_linux():
    return platform.system() == "Linux"


def get_home_dir():
    """Return the current user's home directory across platforms.

    On macOS/Linux this is $HOME. On Windows os.path.expanduser falls
    back to %USERPROFILE% when HOME is unset (cmd / PowerShell). Under
    Git Bash / MSYS2, $HOME is set as a POSIX path; we normalize it to
    Windows native form so os.symlink etc. accept it.
    """
    return normalize_path(os.path.expanduser("~"))


def normalize_path(path):
    """Normalize an MSYS/Cygwin POSIX path to a Windows native path.

    On Windows, paths sourced from bash (config.sh, $HOME under MSYS,
    etc.) come back as ``/c/Users/foo`` — Python's ``os.symlink`` and
    friends interpret that as ``C:\\c\\Users\\foo``, which doesn't
    exist. Convert to ``C:\\Users\\foo``. No-ops on macOS/Linux and
    on already-native Windows paths.
    """
    if not is_windows() or not path:
        return path
    # /cygdrive/c/... -> C:\...
    m = re.match(r"^/cygdrive/([a-zA-Z])(/.*)?$", path)
    if m:
        drive = m.group(1).upper()
        rest = (m.group(2) or "").replace("/", "\\")
        return f"{drive}:{rest}" if rest else f"{drive}:\\"
    # /c/... -> C:\... (MSYS / Git Bash convention)
    m = re.match(r"^/([a-zA-Z])(/.*)?$", path)
    if m:
        drive = m.group(1).upper()
        rest = (m.group(2) or "").replace("/", "\\")
        return f"{drive}:{rest}" if rest else f"{drive}:\\"
    return path


# Global variables
# ------------------------------------------------------------------------------

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
HOME_DIR = get_home_dir()
VERBOSE = False  # Set to True with -v/--verbose flag
DRY_RUN = False  # Set to True with --dry-run flag

# Cached result of can_create_symlinks() so the Dev Mode prompt only
# fires once per setup.py run (e.g. --all).
_SYMLINK_CHECK_DONE = None

# Configuration paths loaded from config.sh
CONFIG = None  # Lazy-loaded config dictionary


# Note: Python print functions kept separate from shell utils.sh
# (Python can't source bash scripts - different language ecosystems)
# Shell scripts use Print* functions from utils.sh
class colors:
    HEADER = "\033[94m"  # Blue
    HINT = "\033[46m"  # Background Cyan
    OK = "\033[92m"  # Green
    WARNING = "\033[93m"  # Yellow
    FAIL = "\033[91m"  # Red
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    END = "\033[0m"


# Utils
# ------------------------------------------------------------------------------


def load_config():
    """Load configuration from config.sh.

    Returns a dictionary with all DOTFILES_* configuration variables.
    Falls back to default hardcoded values if config.sh cannot be loaded.
    """
    config_path = os.path.join(BASE_DIR, "config.sh")

    # Default fallback values (same as previous hardcoded values)
    defaults = {
        "DOTFILES_MOZBUILD_DIR": os.path.join(HOME_DIR, ".mozbuild"),
        "DOTFILES_LOCAL_BIN_DIR": os.path.join(HOME_DIR, ".local", "bin"),
        "DOTFILES_CARGO_DIR": os.path.join(HOME_DIR, ".cargo"),
        "DOTFILES_TRASH_DIR_LINUX": os.path.join(
            HOME_DIR, ".local", "share", "Trash", "files"
        ),
        "DOTFILES_TRASH_DIR_DARWIN": os.path.join(HOME_DIR, ".Trash"),
        "DOTFILES_TRASH_DIR_WINDOWS": os.path.join(HOME_DIR, ".Trash"),
        "DOTFILES_MACHRC_PATH": os.path.join(HOME_DIR, ".mozbuild", "machrc"),
        "DOTFILES_CARGO_ENV_PATH": os.path.join(HOME_DIR, ".cargo", "env"),
    }

    # Try to load from config.sh
    if not os.path.exists(config_path):
        print_verbose("config.sh not found, using default values")
        return defaults

    try:
        # Source config.sh and export all DOTFILES_* variables
        cmd = f'source "{config_path}" && env | grep "^DOTFILES_"'
        result = subprocess.run(
            ["bash", "-c", cmd], capture_output=True, text=True, timeout=5
        )

        if result.returncode != 0:
            print_verbose("Failed to source config.sh, using defaults")
            return defaults

        # Parse the output to extract config values. config.sh is
        # sourced via bash, so under MSYS/Git Bash on Windows the paths
        # come back POSIX-style (/c/Users/...). Normalize so the rest
        # of setup.py can hand them to os.symlink / open / etc.
        config = defaults.copy()
        for line in result.stdout.strip().split("\n"):
            if "=" in line:
                key, value = line.split("=", 1)
                config[key] = normalize_path(value)

        print_verbose("Config loaded from config.sh")
        return config

    except (subprocess.TimeoutExpired, Exception) as e:
        print_verbose("Error loading config.sh: {}".format(e))
        return defaults


def get_config():
    """Get the configuration dictionary (lazy load)."""
    global CONFIG
    if CONFIG is None:
        CONFIG = load_config()
    return CONFIG


# Change Tracking & Rollback
# ------------------------------------------------------------------------------


class ChangeTracker:
    """Tracks all changes made during setup for potential rollback."""

    def __init__(self):
        self.changes = []  # List of change records in chronological order

    def record_symlink_created(self, target, source, old_target=None):
        """Record that a symlink was created.

        Args:
            target: Path where symlink was created
            source: What the symlink points to
            old_target: If replacing existing symlink, what it pointed to before
        """
        self.changes.append(
            {
                "type": "symlink",
                "target": target,
                "source": source,
                "old_target": old_target,
            }
        )
        print_verbose("ChangeTracker: Recorded symlink {} -> {}".format(target, source))

    def record_lines_appended(self, file_path, lines):
        """Record that lines were appended to a file.

        Args:
            file_path: Path to file that was modified
            lines: List of lines that were appended
        """
        self.changes.append({"type": "append", "file": file_path, "lines": lines})
        print_verbose(
            "ChangeTracker: Recorded {} line(s) appended to {}".format(
                len(lines), file_path
            )
        )

    def record_git_config(self, key, value):
        """Record that a git config was set.

        Args:
            key: Git config key that was set
            value: Value that was set
        """
        self.changes.append({"type": "git_config", "key": key, "value": value})
        print_verbose("ChangeTracker: Recorded git config {} = {}".format(key, value))

    def has_changes(self):
        """Return True if any changes have been recorded."""
        return len(self.changes) > 0

    def get_change_count(self):
        """Return the number of changes recorded."""
        return len(self.changes)


def rollback_changes(tracker):
    """Rollback all changes tracked by the ChangeTracker.

    Changes are undone in reverse order (LIFO).

    Args:
        tracker: ChangeTracker instance with recorded changes

    Returns:
        True if rollback succeeded, False if any errors occurred
    """
    if not tracker.has_changes():
        print("No changes to rollback.")
        return True

    print_title("Rolling Back Changes")
    print("Undoing {} change(s)...".format(tracker.get_change_count()))

    errors = []
    # Process changes in reverse order (undo most recent first)
    for change in reversed(tracker.changes):
        try:
            if change["type"] == "symlink":
                target = change["target"]
                old_target = change.get("old_target")

                if os.path.islink(target):
                    print("Removing symlink: {}".format(target))
                    os.unlink(target)

                    # If we replaced an existing symlink, restore it
                    if old_target:
                        print(
                            "Restoring previous symlink: {} -> {}".format(
                                target, old_target
                            )
                        )
                        os.symlink(old_target, target)
                elif os.path.exists(target):
                    print_warning("Not removing {} (not a symlink)".format(target))
                else:
                    print_verbose("Symlink {} already removed".format(target))

            elif change["type"] == "append":
                file_path = change["file"]
                lines = change["lines"]

                if not os.path.exists(file_path):
                    print_verbose("File {} does not exist, skipping".format(file_path))
                    continue

                print("Removing {} line(s) from {}".format(len(lines), file_path))

                # Read all lines
                with open(file_path, "r") as f:
                    all_lines = f.readlines()

                # Remove the appended lines
                lines_to_remove = set(line.rstrip("\n") for line in lines)
                filtered_lines = [
                    line
                    for line in all_lines
                    if line.rstrip("\n") not in lines_to_remove
                ]

                # Write back filtered content. newline="\n" prevents
                # Windows text-mode from rewriting \n -> \r\n, which
                # would silently flip the whole file to CRLF on every
                # rollback.
                with open(file_path, "w", encoding="utf-8", newline="\n") as f:
                    f.writelines(filtered_lines)

            elif change["type"] == "git_config":
                key = change["key"]
                print("Removing git config: {}".format(key))

                # Remove the git config setting
                result = subprocess.run(
                    ["git", "config", "--global", "--unset", key],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

                if result.returncode != 0:
                    # Non-zero could mean already unset, which is fine
                    print_verbose(
                        "git config unset returned {}".format(result.returncode)
                    )

        except Exception as e:
            error_msg = "Error rolling back {}: {}".format(change["type"], e)
            print_error(error_msg)
            errors.append(error_msg)

    if errors:
        print_error("Rollback completed with {} error(s)".format(len(errors)))
        return False
    else:
        print("Rollback completed successfully")
        return True


def can_create_symlinks(probe_dir=None):
    """Probe whether the current process can create symlinks.

    Returns True on macOS/Linux. On Windows, attempts os.symlink in a
    temp directory and returns False on OSError (WinError 1314 when
    Developer Mode is off and the process is unelevated).

    ``probe_dir`` lets callers run the probe on a specific volume
    (e.g. the target firefox repo) instead of the system temp drive,
    since symlink privilege can differ by volume/ACL. When provided
    and writable, the temp probe files are created inside it.
    """
    if not is_windows():
        return True
    parent = probe_dir if probe_dir and os.path.isdir(probe_dir) else None
    try:
        tmpdir = tempfile.mkdtemp(dir=parent)
    except OSError:
        # Fall back to the system temp drive if probe_dir is unwritable.
        tmpdir = tempfile.mkdtemp()
    try:
        target = os.path.join(tmpdir, "t")
        link_path = os.path.join(tmpdir, "l")
        with open(target, "w") as f:
            f.write("")
        try:
            os.symlink(target, link_path)
            return True
        except OSError:
            return False
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def is_windows_elevated():
    """Return True iff this process holds the Windows admin token.

    Used to recognize the case where ``os.symlink`` only succeeds
    because setup.py is running elevated, not because Developer Mode
    is enabled — i.e. the committed branch will fail to re-materialize
    symlinks in any non-elevated shell.
    """
    if not is_windows():
        return False
    try:
        import ctypes

        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def is_windows_dev_mode_enabled():
    """Return True iff Windows Developer Mode is enabled for this user.

    Reads ``HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion
    \\AppModelUnlock\\AllowDevelopmentWithoutDevLicense``. Any
    registry error (missing key, denied access, non-Windows) returns
    False — callers must treat this as a hint, not an authoritative
    capability check (use ``can_create_symlinks()`` for that).
    """
    if not is_windows():
        return False
    try:
        import winreg
    except ImportError:
        return False
    try:
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock",
        ) as key:
            value, _ = winreg.QueryValueEx(key, "AllowDevelopmentWithoutDevLicense")
            return int(value) == 1
    except (OSError, ValueError):
        return False


def ensure_symlink_capability():
    """Block symlink-creating operations on Windows when Dev Mode is off.

    Returns True if symlinks work (now or after the user enabled them),
    False if the user declined. Result is cached so the prompt only
    fires once per setup.py run.
    """
    global _SYMLINK_CHECK_DONE
    if _SYMLINK_CHECK_DONE is not None:
        return _SYMLINK_CHECK_DONE

    if can_create_symlinks():
        _SYMLINK_CHECK_DONE = True
        return True

    print_warning("Symlinks are not available on this Windows install.")
    print_hint(
        "To enable: Settings -> System -> For developers -> "
        "turn on 'Developer Mode'. Alternatively run this script as "
        "Administrator. Symlinks let dotfile changes propagate "
        "without re-running setup."
    )
    while True:
        try:
            response = (
                input("Have you enabled Developer Mode? [y/N/abort]: ").strip().lower()
            )
        except (EOFError, KeyboardInterrupt):
            print()
            _SYMLINK_CHECK_DONE = False
            return False

        if response in ("", "n", "no", "abort"):
            _SYMLINK_CHECK_DONE = False
            return False
        if response in ("y", "yes"):
            if can_create_symlinks():
                _SYMLINK_CHECK_DONE = True
                return True
            print_warning(
                "Still cannot create symlinks. You may need to "
                "restart your terminal after enabling Developer Mode."
            )


# Symbolically link source to target
def link(source, target, tracker=None):
    print_verbose("link() called: source={}, target={}".format(source, target))

    # Validate source exists before creating symlink
    print_verbose("Checking if source exists: {}".format(source))
    if not os.path.exists(source):
        print_error("Cannot create symlink: source does not exist")
        print_error("Source: {}".format(source))
        print_verbose("link() returning: False (source does not exist)")
        return False

    print_verbose("Source exists: True")
    print_verbose("Checking if target is a symlink: {}".format(target))

    old_target = None
    if os.path.islink(target):
        print_verbose("Target is a symlink, unlinking")
        # Record what the old symlink pointed to
        old_target = os.readlink(target)

        if DRY_RUN:
            print_dry_run("Would unlink {}".format(target))
        else:
            print("unlink {}".format(target))
            os.unlink(target)
    else:
        print_verbose("Target is not a symlink or does not exist")

    if DRY_RUN:
        print_dry_run("Would link {} to {}".format(source, target))
    else:
        print("link {} to {}".format(source, target))
        os.symlink(source, target)
        print_verbose("Symlink created successfully")

    # Record the change if tracker provided (even in dry-run for preview)
    if tracker and not DRY_RUN:
        tracker.record_symlink_created(target, source, old_target)

    print_verbose("link() returning: True")
    return True


# Check if `name` exists
def is_tool(name):
    cmd = "where" if is_windows() else "which"
    try:
        r = subprocess.check_output([cmd, name], stderr=subprocess.DEVNULL)
        print("{} is found in {}".format(name, r.decode("utf-8")))
        return True
    except subprocess.CalledProcessError:
        # Command not found (expected when tool is not installed)
        return False
    except FileNotFoundError:
        # which/where command itself not found
        print_warning('Command finder "{}" is not available on this system'.format(cmd))
        return False
    except Exception as e:
        # Unexpected error - log it for debugging
        print_warning("Error checking for {}: {}".format(name, str(e)))
        return False


def _node_major_version():
    """Return Node.js major version as int, or None if node is unavailable."""
    try:
        out = subprocess.check_output(
            ["node", "--version"], stderr=subprocess.DEVNULL, text=True
        ).strip()
        # Output like "v18.19.1"
        return int(out.lstrip("v").split(".")[0])
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
        return None


def _augment_path_for_windows_tools():
    """Prepend pip3 --user and npm -g bin dirs to this process's PATH.

    Mirrors what dot.settings_windows adds at shell startup, so that
    `where`/`which` from inside setup.py finds freshly-installed
    tools even when the parent shell hasn't sourced the updated
    dotfiles config yet (typical on re-runs from the same terminal
    session). Keep the directory list in sync with the PATH block in
    dot.settings_windows.

    Idempotent and a no-op on macOS/Linux.
    """
    if not is_windows():
        return
    home = get_home_dir()
    dirs_to_add = []
    # pip3 --user: ~/AppData/Roaming/Python/PythonXX/Scripts
    for scripts_dir in glob.glob(
        os.path.join(home, "AppData", "Roaming", "Python", "Python*", "Scripts")
    ):
        if os.path.isdir(scripts_dir):
            dirs_to_add.append(scripts_dir)
    # npm -g: ~/AppData/Roaming/npm
    npm_dir = os.path.join(home, "AppData", "Roaming", "npm")
    if os.path.isdir(npm_dir):
        dirs_to_add.append(npm_dir)

    existing = os.environ.get("PATH", "")
    existing_parts = existing.split(os.pathsep) if existing else []
    new_parts = [d for d in dirs_to_add if d not in existing_parts]
    if new_parts:
        os.environ["PATH"] = os.pathsep.join(new_parts + existing_parts)


_augment_path_for_windows_tools()


def append_to_next_line_after(name, pattern, value=""):
    file = fileinput.input(name, inplace=True)
    for line in file:
        replacement = line + ("\n" if "\n" not in line else "") + value
        line = re.sub(pattern, replacement, line)
        sys.stdout.write(line)
    file.close()


def _bashify_path(path):
    """Convert a Windows-native path to a form bash can parse safely.

    Bash on Windows (Git Bash / MSYS) accepts forward-slash paths and
    treats backslashes as escape characters even inside ``[ -r ... ]``
    tests when the argument is unquoted. So C:\\Users\\foo\\bar gets
    chewed to C:Usersfoobar and the test fails. Convert to forward
    slashes (and we'll wrap the result in double quotes at the call
    site for good measure).
    """
    if is_windows():
        return path.replace("\\", "/")
    return path


def bash_export_command(path):
    return f'export PATH="{_bashify_path(path)}:$PATH"'


def bash_load_command(path):
    p = _bashify_path(path)
    return f'[ -r "{p}" ] && . "{p}"'


def append_nonexistent_lines_to_file(file, lines, tracker=None):
    """
    Append lines to a file if they don't already exist.

    Uses line-by-line comparison (not substring matching) to avoid false positives.
    Ensures file ends with newline before appending.
    Validates file is writable before attempting operations.

    Args:
        file: Path to the file to modify
        lines: List of lines to append (without trailing newlines)
        tracker: Optional ChangeTracker to record changes

    Returns:
        True if all operations successful, False otherwise
    """
    # Validate file exists
    if not os.path.exists(file):
        print_error("File does not exist: {}".format(file))
        return False

    # Validate file is writable
    if not os.access(file, os.W_OK):
        print_error("File is not writable: {}".format(file))
        return False

    try:
        # Read existing lines
        with open(file, "r") as f:
            existing_lines = [line.rstrip("\n") for line in f]

        # Check if file ends with newline
        needs_newline = False
        if existing_lines and len(existing_lines) > 0:
            with open(file, "rb") as f:
                f.seek(-1, os.SEEK_END)
                last_char = f.read(1)
                needs_newline = last_char != b"\n"

        # Determine which lines to append
        lines_to_append = []
        for line in lines:
            if line in existing_lines:
                print_warning("{} is already in {}".format(line, file))
            else:
                lines_to_append.append(line)

        # Append new lines
        if lines_to_append:
            if DRY_RUN:
                if needs_newline:
                    print_dry_run("Would add newline at end of {}".format(file))
                for line in lines_to_append:
                    print_dry_run("Would append into {}: {}".format(file, line))
            else:
                with open(file, "a") as f:
                    # Add newline to last line if needed
                    if needs_newline:
                        f.write("\n")

                    for line in lines_to_append:
                        f.write(line + "\n")
                        print("{} is appended into {}".format(line, file))

                # Record the change if tracker provided
                if tracker:
                    tracker.record_lines_appended(file, lines_to_append)

        return True

    except IOError as e:
        print_error("Failed to modify {}: {}".format(file, str(e)))
        return False
    except Exception as e:
        print_error("Unexpected error modifying {}: {}".format(file, str(e)))
        return False


DOTFILES_GITIGNORE_HEADER = "# Added by dotfiles setup (Claude Code settings)"


def _split_gitignore_sections(lines):
    """
    Partition .gitignore lines into (before_header, header_line, our_entries, after).

    ``our_entries`` is the contiguous block of non-empty lines that follow the
    dotfiles header (stops at the first blank line or next ``#`` comment).
    If the header is absent, everything goes in ``before_header`` and the
    remaining slots are empty.
    """
    before = []
    header = None
    ours = []
    after = []

    i = 0
    # Phase 1: before the header
    while i < len(lines):
        if lines[i].rstrip("\n") == DOTFILES_GITIGNORE_HEADER:
            header = lines[i]
            i += 1
            break
        before.append(lines[i])
        i += 1
    else:
        return before, header, ours, after

    # Phase 2: our entries — contiguous non-blank, non-comment lines
    while i < len(lines):
        stripped = lines[i].strip()
        if not stripped or stripped.startswith("#"):
            break
        ours.append(lines[i])
        i += 1

    # Phase 3: everything else
    after = lines[i:]
    return before, header, ours, after


def _rewrite_our_section(gitignore_path, new_entries):
    """Write ``new_entries`` (sorted, deduped) under the dotfiles header."""
    lines = []
    if os.path.exists(gitignore_path):
        with open(gitignore_path, "r") as f:
            lines = f.readlines()

    before, header, _ours, after = _split_gitignore_sections(lines)

    sorted_entries = sorted(set(new_entries))

    out = []
    out.extend(before)
    if sorted_entries:
        if out and not out[-1].endswith("\n"):
            out[-1] = out[-1] + "\n"
        # Blank line before our section for readability, unless file is empty.
        if out and out[-1].strip():
            out.append("\n")
        out.append(DOTFILES_GITIGNORE_HEADER + "\n")
        for entry in sorted_entries:
            out.append(entry + "\n")
    elif header is not None:
        # Section became empty — drop a trailing blank line we may have left.
        while out and out[-1].strip() == "":
            out.pop()
        if out:
            out.append("\n")

    # Preserve anything that followed our section.
    if after:
        if out and sorted_entries and not out[-1].endswith("\n"):
            out.append("\n")
        out.extend(after)

    # newline="\n" prevents Windows text-mode from rewriting \n ->
    # \r\n, which would flip the whole .gitignore to CRLF on every
    # rewrite — visible as a giant diff in repos like firefox that
    # declare .gitignore as -text in .gitattributes.
    with open(gitignore_path, "w", encoding="utf-8", newline="\n") as f:
        f.writelines(out)


def _read_our_entries(gitignore_path):
    """Return the set of entries currently in our gitignore section."""
    if not os.path.exists(gitignore_path):
        return set()
    with open(gitignore_path, "r") as f:
        _, _, ours, _ = _split_gitignore_sections(f.readlines())
    return {line.strip() for line in ours if line.strip()}


def add_to_gitignore(repo_dir, entries, dry_run=False):
    """
    Add entries to our managed section of .gitignore, keeping it sorted.

    Args:
        repo_dir: Path to the git repository root
        entries: List of gitignore patterns to add
        dry_run: If True, only print what would be done

    Returns:
        List of entries that were added (or would be added in dry-run)
    """
    gitignore_path = os.path.join(repo_dir, ".gitignore")
    added = []

    our_entries_ordered = []
    if os.path.exists(gitignore_path):
        with open(gitignore_path, "r") as f:
            _, _, ours, _ = _split_gitignore_sections(f.readlines())
        our_entries_ordered = [line.strip() for line in ours if line.strip()]
    our_entries = set(our_entries_ordered)

    # Also treat entries that appear outside our section as "already ignored"
    # so we don't duplicate them.
    all_existing = set()
    if os.path.exists(gitignore_path):
        with open(gitignore_path, "r") as f:
            for line in f:
                stripped = line.strip()
                if stripped and not stripped.startswith("#"):
                    all_existing.add(stripped)

    entries_to_add = []
    already_ignored = []
    for entry in entries:
        if entry in our_entries or entry in all_existing:
            already_ignored.append(entry)
        else:
            entries_to_add.append(entry)

    if already_ignored:
        print("Already in .gitignore (no action needed):")
        for entry in already_ignored:
            print(f"  {entry}")

    # Always re-sort our section so entries stay alphabetical even on
    # idempotent re-runs or after branch switches that left the section stale.
    needs_resort = our_entries_ordered != sorted(our_entries_ordered)

    if not entries_to_add and not needs_resort:
        return added

    if dry_run:
        for entry in entries_to_add:
            print(f"  Would add to .gitignore: {entry}")
            added.append(entry)
        if needs_resort and not entries_to_add:
            print("  Would re-sort existing .gitignore section")
        return added

    merged = sorted(our_entries | set(entries_to_add))
    try:
        _rewrite_our_section(gitignore_path, merged)
        for entry in entries_to_add:
            print(f"Added to .gitignore: {entry}")
            added.append(entry)
        if needs_resort and not entries_to_add:
            print("Re-sorted existing .gitignore section")
    except IOError as e:
        print_error(f"Failed to update .gitignore: {e}")

    return added


def remove_from_gitignore(repo_dir, entries, dry_run=False):
    """Remove entries from our managed section of .gitignore (if present)."""
    gitignore_path = os.path.join(repo_dir, ".gitignore")
    if not os.path.exists(gitignore_path):
        return []

    our_entries = _read_our_entries(gitignore_path)
    entries_set = set(entries)
    to_remove = our_entries & entries_set
    if not to_remove:
        return []

    if dry_run:
        for entry in sorted(to_remove):
            print(f"  Would remove from .gitignore: {entry}")
        return sorted(to_remove)

    remaining = sorted(our_entries - to_remove)
    _rewrite_our_section(gitignore_path, remaining)
    for entry in sorted(to_remove):
        print(f"Removed from .gitignore: {entry}")
    return sorted(to_remove)


def print_installing_title(name, bold=False):
    print(
        colors.HEADER
        + "".join(
            [
                "\n",
                name,
                (
                    "\n=============================="
                    if bold
                    else "\n--------------------"
                ),
            ]
        )
        + colors.END
    )


# Python print functions (see note at line 15 for why separate from shell)
def print_hint(message):
    print(colors.HINT + message + colors.END + "\n")


def print_warning(message):
    print(colors.WARNING + "WARNING: " + message + colors.END + "\n")


def print_fail(message):
    print(colors.FAIL + "ERROR: " + message + colors.END + "\n")


# Alias for consistency
def print_error(message):
    print_fail(message)


def print_verbose(message):
    """Print verbose debugging information (only when VERBOSE=True)"""
    if VERBOSE:
        print(colors.HEADER + "[VERBOSE] " + colors.END + message)


def print_dry_run(message):
    """Print dry-run action (only when DRY_RUN=True)"""
    if DRY_RUN:
        print(colors.HINT + "[DRY-RUN]" + colors.END + " " + message)


def print_title(message):
    """Print a section title"""
    print("\n" + colors.HEADER + "=" * 50 + colors.END)
    print(colors.HEADER + message + colors.END)
    print(colors.HEADER + "=" * 50 + colors.END)


# Setup functions
# ------------------------------------------------------------------------------


# Link this dotfiles path to $HOME/.dotfiles
def dotfiles_link(tracker=None):
    print_installing_title("dotfile path")
    print_verbose("dotfiles_link() starting")
    if not ensure_symlink_capability():
        print_error("Symlink creation unavailable; skipping dotfile path link")
        return False
    result = link(BASE_DIR, os.path.join(HOME_DIR, ".dotfiles"), tracker)
    print_verbose("dotfiles_link() returning: {}".format(result))
    return result


# Link dot.* to ~/.*
def _migrate_legacy_bashrc_loaders(bashrc_path):
    """Rewrite old Windows-backslash loader lines to forward-slash form.

    Earlier versions of setup.py wrote loader lines like
        [ -r C:\\Users\\cchang\\dotfiles\\dot.bashrc ] && . C:\\Users\\...
    into ~/.bashrc. Bash on Windows treats backslashes as escape
    characters inside an unquoted [ -r ... ] test, so the path got
    chewed to ``C:Userscchangdotfilesdot.bashrc``, the test was
    always false, and dot.bashrc / aliases / etc. never loaded.

    Detect these legacy lines and rewrite them in place to the new
    quoted forward-slash form. No-op on macOS/Linux.
    """
    if not is_windows() or not os.path.exists(bashrc_path):
        return
    try:
        with open(bashrc_path, "r", encoding="utf-8") as f:
            content = f.read()
    except (IOError, UnicodeDecodeError):
        return

    pattern = re.compile(
        r"\[\s+-r\s+(?P<p1>[A-Za-z]:[^\s\]\"]+)\s+\]\s*&&\s*\.\s+(?P<p2>[A-Za-z]:[^\s\"]+)"
    )

    def fix(match):
        p1 = match.group("p1").replace("\\", "/")
        p2 = match.group("p2").replace("\\", "/")
        if p1 != p2:
            return match.group(0)
        return f'[ -r "{p1}" ] && . "{p1}"'

    new_content, count = pattern.subn(fix, content)
    if count == 0 or new_content == content:
        return
    if DRY_RUN:
        print_dry_run(
            "Would migrate {} legacy loader line(s) in {}".format(count, bashrc_path)
        )
        return
    with open(bashrc_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(new_content)
    print(
        "Migrated {} legacy loader line(s) in {} to forward-slash form".format(
            count, bashrc_path
        )
    )


def bash_link(tracker=None):
    print_installing_title("bash startup scripts")
    print_verbose("bash_link() starting")
    print_verbose("Platform: {}".format(platform.system()))

    if not ensure_symlink_capability():
        print_error("Symlink creation unavailable; skipping bash startup links")
        return False

    # Heal up any legacy backslash-formatted loader lines from older
    # setup.py runs before re-checking what to append, so we don't
    # leave broken duplicates around.
    _migrate_legacy_bashrc_loaders(os.path.join(HOME_DIR, ".bashrc"))

    platform_files = {
        "Darwin": ["dot.bashrc", "dot.zshrc", "dot.settings_darwin"],
        "Linux": ["dot.bashrc", "dot.settings_linux"],
        "Windows": ["dot.bashrc", "dot.settings_windows"],
    }

    if is_macos():
        v, _, _ = platform.mac_ver()
        version_parts = v.split(".")[:2]
        try:
            major = int(version_parts[0]) if version_parts else 0
            minor = int(version_parts[1]) if len(version_parts) > 1 else 0
        except (ValueError, IndexError):
            # If version parsing fails, assume modern macOS (use zshrc)
            major, minor = 11, 0

        platform_files["Darwin"].append(
            "dot.zshrc" if (major, minor) >= (10, 15) else "dot.bash_profile"
        )

    current_platform = platform.system()
    if current_platform not in platform_files:
        print_error("Unsupported platform: {}".format(current_platform))
        return False
    files = platform_files[current_platform]
    print_verbose("Files to process: {}".format(files))
    errors = []
    skipped = []

    for f in files:
        print_verbose("Processing file: {}".format(f))
        target = os.path.join(HOME_DIR, f[3:])  # Get name after dot
        src = os.path.join(BASE_DIR, f)
        if os.path.isfile(target):
            # Check if source exists before comparing
            if not os.path.exists(src):
                print_error("Source file does not exist: {}".format(src))
                print_error("Repository may be incomplete or corrupted")
                errors.append("Source file missing: {}".format(f))
                continue

            if os.path.samefile(src, target):
                print_warning("{} is already linked!".format(target))
                continue
            print_warning("{} already exists!".format(target))
            if f == "dot.bashrc" or f == "dot.zshrc":
                print("Append a command to load {} in {}".format(src, target))
                result = append_nonexistent_lines_to_file(
                    target, [bash_load_command(src)], tracker
                )
                if not result:
                    errors.append("Failed to append to {}".format(target))
            else:
                # File exists but isn't bashrc/zshrc - provide guidance
                print("Options:")
                print("  1. Remove {} and re-run setup".format(target))
                print(
                    "  2. Manually replace with symlink: ln -sf {} {}".format(
                        src, target
                    )
                )
                print("  3. Keep existing file (skip)")
                skipped.append(f)
        else:
            # Special case: bashrc/zshrc should be real files that source templates
            # This allows machine-specific customization (e.g., by mozilla_init)
            if f == "dot.bashrc" or f == "dot.zshrc":
                print("Creating {} with source command to load {}".format(target, src))
                try:
                    if DRY_RUN:
                        print_dry_run(
                            "Would create {} with source command".format(target)
                        )
                    else:
                        with open(target, "w", encoding="utf-8", newline="\n") as tf:
                            tf.write(bash_load_command(src) + "\n")
                        print("{} created".format(target))
                except IOError as e:
                    print_error("Failed to create {}: {}".format(target, str(e)))
                    errors.append("Failed to create {}".format(f))
            else:
                # For all other files (settings_*), create symlinks as usual
                result = link(src, target, tracker)
                if not result:
                    errors.append("Failed to link {}".format(f))

    # Return True only if no errors (skipped files are user choice, not errors)
    success = len(errors) == 0
    print_verbose(
        "bash_link() completed: errors={}, skipped={}".format(len(errors), len(skipped))
    )
    print_verbose("bash_link() returning: {}".format(success))
    return success


# Include git/config from ~/.giconfig
def git_init(tracker=None):
    print_installing_title("git settings")
    if not is_tool("git"):
        print_fail("Please install git first!")
        return False

    git_config = os.path.join(HOME_DIR, ".gitconfig")
    if not os.path.isfile(git_config):
        print_warning(
            "{} does not exist! Create a new one with default settings!".format(
                git_config
            )
        )
        # Set global user name and email
        subprocess.call(["git", "config", "--global", "user.name", "Chun-Min Chang"])
        subprocess.call(
            ["git", "config", "--global", "user.email", "chun.m.chang@gmail.com"]
        )

    # Include git config here in global gitconfig file
    path = os.path.join(BASE_DIR, "git", "config")
    if not os.path.exists(path):
        print_error("Git config file not found: {}".format(path))
        print_error("Cannot configure git include.path")
        return False

    if DRY_RUN:
        print_dry_run("Would run: git config --global include.path {}".format(path))
    else:
        subprocess.call(["git", "config", "--global", "include.path", path])

        # Record the git config change
        if tracker:
            tracker.record_git_config("include.path", path)

    # Show the current file if it exists:
    if os.path.exists(git_config):
        with open(git_config, "r") as f:
            content = f.read()
            print_hint("{}:".format(git_config))
            print(content)
            f.close()
    else:
        print_warning("Git config file not found: {}".format(git_config))
        print_warning("Git configuration may not be complete")

    return True


# mozilla stuff
# ---------------------------------------


def mozilla_init(mozilla_arg, tracker=None):
    """
    Initialize Mozilla development tools.

    Args:
        mozilla_arg: Value from --mozilla argument (None, [], or list of tools)
        tracker: Optional ChangeTracker to record changes

    Returns:
        None if skipped, True if all succeeded, False if any failed
    """
    print_installing_title("mozilla settings", True)

    if mozilla_arg is None:
        print_warning("Skip installing mozilla toolkit")
        print_verbose("mozilla_arg is None, skipping Mozilla tools")
        return None  # None = skipped, not failure

    if not ensure_symlink_capability():
        print_error("Symlink creation unavailable; skipping mozilla toolkit")
        return False

    print_verbose("mozilla_arg: {}".format(mozilla_arg))

    funcs = {
        "firefox": firefox_init,
        "tools": tools_init,
        "rust": rust_init,
        "cli-tools": mozilla_cli_tools_init,
        "pernosco": pernosco_init,
    }

    # Select which Mozilla tools to install
    if mozilla_arg:
        # User specified tools: filter to valid options only
        options = [k for k in mozilla_arg if k in funcs]
        print_verbose("Selected Mozilla tools: {}".format(options))
    else:
        # No tools specified: install all
        options = list(funcs.keys())
        print_verbose("No tools specified, installing all: {}".format(options))

    all_succeeded = True
    for k in options:
        result = funcs[k](tracker)
        # None = skipped (user choice), False = failed
        if result is False:
            all_succeeded = False

    return all_succeeded


def firefox_init(tracker=None):
    print_installing_title("firefox alias and machrc")
    config = get_config()
    machrc = config["DOTFILES_MACHRC_PATH"]
    if os.path.islink(machrc) or not os.path.exists(machrc):
        path = os.path.join(BASE_DIR, "mozilla", "firefox", "machrc")
        if not link(path, machrc, tracker):
            return False
    else:
        # Existing regular file (e.g. created by `./mach bootstrap`).
        # Don't overwrite — it likely has machine-specific settings the
        # user wants to keep (mach_telemetry opt-in, etc.).
        print_warning(
            "{} already exists; keeping it. ".format(machrc)
            + "Remove it manually and re-run --mozilla firefox if you "
            + "want the dotfiles version instead."
        )

    bashrc = os.path.join(HOME_DIR, ".bashrc")
    if not os.path.isfile(bashrc):
        print_fail("{} does not exist! Abort!".format(bashrc))
        return False

    path = os.path.join(BASE_DIR, "mozilla", "firefox", "alias.sh")
    result = append_nonexistent_lines_to_file(
        bashrc, [bash_load_command(path)], tracker
    )
    return result


def tools_init(tracker=None):
    print_installing_title("tools settings")

    bashrc = os.path.join(HOME_DIR, ".bashrc")
    if not os.path.isfile(bashrc):
        print_fail("{} does not exist! Abort!".format(bashrc))
        return False

    path = os.path.join(BASE_DIR, "mozilla", "firefox", "tools.sh")
    result = append_nonexistent_lines_to_file(
        bashrc, [bash_load_command(path)], tracker
    )
    return result


def rust_init(tracker=None):
    print_installing_title("rust settings")

    bashrc = os.path.join(HOME_DIR, ".bashrc")
    if not os.path.isfile(bashrc):
        print_fail("{} does not exist! Abort!".format(bashrc))
        return False

    config = get_config()
    cargo_env = config["DOTFILES_CARGO_ENV_PATH"]
    if not os.path.isfile(cargo_env):
        print_warning(
            "Skipping rust settings: {} does not exist. ".format(cargo_env)
            + "This is normal if cargo was installed without rustup "
            + "(e.g., via mozilla-build bootstrap). Run "
            + "`./mach bootstrap.py` under firefox if you need rustup."
        )
        return None  # Skipped, not failure

    result = append_nonexistent_lines_to_file(
        bashrc, [bash_load_command(cargo_env)], tracker
    )
    return result


def pernosco_init(tracker=None):
    """
    Initialize pernosco-submit script (optional).

    Asks user if they want to install pernosco-submit, and if so:
    - Asks for Mozilla email and secret key
    - Asks where to put the script
    - Creates the script with credentials filled in
    """
    print_installing_title("pernosco-submit (optional)")

    # Check platform - pernosco is Linux only
    if not is_linux():
        print_warning("pernosco-submit is Linux only, skipping")
        return None  # Skipped, not failure

    # Ask user if they want to install
    print("\nPernosco is a time-travel debugging service for Firefox.")
    print("If you don't use Pernosco, you can skip this.")

    if not get_user_confirmation(
        "Install pernosco-submit script? [y/N]: ", default_non_interactive=False
    ):
        print("Skipping pernosco-submit installation")
        return None  # Skipped, not failure

    # Ask for credentials
    print("\nPlease provide your Pernosco credentials:")

    mozilla_email = get_user_input("Mozilla email (e.g., user@mozilla.com): ", "")
    if not mozilla_email or not mozilla_email.endswith("@mozilla.com"):
        print_fail(
            "Email must end with @mozilla.com. Aborting pernosco-submit installation."
        )
        return False

    secret_key = get_user_input(
        "PERNOSCO_USER_SECRET_KEY (from Pernosco dashboard): ", ""
    )
    if not secret_key:
        print_fail("Empty secret key. Aborting pernosco-submit installation.")
        return False

    # Get configuration
    config = get_config()
    local_bin = config["DOTFILES_LOCAL_BIN_DIR"]

    # Ask where to install
    print("\nWhere would you like to install pernosco-submit?")
    print(f"  1. Local bin: {local_bin}")
    print("  2. Custom path")

    choice = get_user_input("Choose [1/2]: ", "1")

    if choice == "1":
        target_dir = local_bin
    elif choice == "2":
        target_dir = get_user_input("Enter custom directory path: ", local_bin)
        target_dir = os.path.expanduser(target_dir)
    else:
        target_dir = local_bin

    # Create directory if needed
    if not os.path.isdir(target_dir):
        if DRY_RUN:
            print_dry_run(f"Would create directory: {target_dir}")
        else:
            try:
                os.makedirs(target_dir, exist_ok=True)
                print(f"Created directory: {target_dir}")
                if tracker:
                    tracker.record_create(target_dir, "directory")
            except OSError as e:
                print_fail(f"Failed to create directory {target_dir}: {e}")
                return False

    # Read template
    template_path = os.path.join(
        BASE_DIR, "mozilla", "firefox", "pernosco-submit_template"
    )
    target_path = os.path.join(target_dir, "pernosco-submit")

    if not os.path.isfile(template_path):
        print_fail(f"Template not found: {template_path}")
        return False

    if os.path.exists(target_path):
        print_warning(f"{target_path} already exists!")
        if not get_user_confirmation(
            "Overwrite? [y/N]: ", default_non_interactive=False
        ):
            print("Skipping - keeping existing file")
            return None

    # Read template and fill in credentials
    try:
        with open(template_path, "r") as f:
            script_content = f.read()
    except IOError as e:
        print_fail(f"Failed to read template: {e}")
        return False

    # Replace placeholders with actual values
    script_content = script_content.replace("<user>@mozilla.com", mozilla_email)
    script_content = script_content.replace(
        "export PERNOSCO_USER_SECRET_KEY=",
        f"export PERNOSCO_USER_SECRET_KEY={secret_key}",
    )

    # Write the script
    if DRY_RUN:
        print_dry_run(f"Would create {target_path} with credentials")
        print_dry_run("Would make script executable")
    else:
        try:
            with open(target_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(script_content)
            os.chmod(target_path, 0o755)
            print(f"Installed: {target_path}")
            if tracker:
                tracker.record_create(target_path, "file")
        except (IOError, OSError) as e:
            print_fail(f"Failed to install pernosco-submit: {e}")
            return False

    # Remind user to set PERNOSCO_BIN path
    print("")
    print_hint(
        "NOTE: Edit the script to set PERNOSCO_BIN to your pernosco-submit binary path:"
    )
    print(f"  {target_path}")

    return True


# Mozilla Rust CLI tools (cargo install)
# ---------------------------------------


def _resolve_msvc_env():
    """Return an env dict with MSVC build tools first on PATH, or None.

    The MSYS coreutils package ships ``/usr/bin/link.exe`` (a POSIX
    hardlink utility), which appears earlier on most Git Bash / mozilla-
    build PATHs than MSVC's ``link.exe`` (or MSVC isn't on PATH at all).
    rustc's *-pc-windows-msvc toolchain invokes ``link.exe`` for the
    final link step and silently picks up the wrong one, producing the
    cryptic ``link: extra operand '...rcgu.o'`` failure mid-cargo-install.

    Two ways to locate MSVC, tried in order:

      1. ``vswhere.exe`` from the Visual Studio Installer — the
         standard route for users who installed VS Build Tools
         themselves. We run ``vcvars64.bat`` in a child cmd and
         capture its environment.

      2. Mozilla-build's bundled overlay at ``~/.mozbuild/vs/``
         (populated by ``./mach bootstrap``). It ships a real
         ``link.exe``/``cl.exe`` under ``VC/Tools/MSVC/<ver>/bin/
         Hostx64/x64/`` plus the Windows SDK under ``Windows
         Kits/10/``, but its ``vcvars64.bat`` can't be used because
         the overlay omits ``vcvarsall.bat``. We construct the
         equivalent PATH/INCLUDE/LIB manually.

    Returns:
        dict suitable for ``subprocess.run(env=...)`` if MSVC was
        located, else None (caller should fall back to inherited env
        and warn the user).
    """
    if not is_windows():
        return None
    return _msvc_env_from_vswhere() or _msvc_env_from_mozbuild()


def _msvc_env_from_vswhere():
    """Locate VS via ``vswhere.exe`` and capture vcvars64.bat env.

    Returns env dict or None if VS isn't installed at the system level.
    """
    program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    vswhere = os.path.join(
        program_files_x86, "Microsoft Visual Studio", "Installer", "vswhere.exe"
    )
    if not os.path.exists(vswhere):
        return None

    try:
        result = subprocess.run(
            [
                vswhere,
                "-latest",
                "-products",
                "*",
                "-requires",
                "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
                "-property",
                "installationPath",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, OSError):
        return None

    install_path = result.stdout.strip()
    if not install_path or not os.path.isdir(install_path):
        return None

    vcvars = os.path.join(install_path, "VC", "Auxiliary", "Build", "vcvars64.bat")
    if not os.path.exists(vcvars):
        return None

    # Source vcvars64.bat in a child cmd, then `set` to dump the env.
    # Redirect vcvars's own stdout to nul so only `set` output reaches us.
    try:
        result = subprocess.run(
            ["cmd", "/c", f'"{vcvars}" >nul && set'],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, OSError):
        return None

    env = {}
    for line in result.stdout.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            env[k] = v

    # Sanity check: the captured PATH should now have a path containing
    # "VC\Tools\MSVC". If not, vcvars didn't actually configure anything.
    path_lc = env.get("PATH", "").lower().replace("/", "\\")
    if "\\vc\\tools\\msvc\\" not in path_lc:
        return None
    return env


def _msvc_env_from_mozbuild():
    """Construct an MSVC build env from mozilla-build's bundled VS overlay.

    Manually replicates what ``vcvars64.bat`` would set: prepends MSVC's
    Hostx64/x64 bin (so its ``link.exe``/``cl.exe`` win over
    /usr/bin/link.exe) and sets INCLUDE/LIB to the MSVC + Windows SDK
    sub-dirs.

    Returns env dict or None if ``~/.mozbuild/vs/`` isn't present or is
    incomplete (no MSVC binaries / no Windows SDK).
    """
    vs_root = os.path.join(HOME_DIR, ".mozbuild", "vs")
    if not os.path.isdir(vs_root):
        return None

    # Pick the highest-versioned MSVC toolchain present.
    msvc_versions_root = os.path.join(vs_root, "VC", "Tools", "MSVC")
    if not os.path.isdir(msvc_versions_root):
        return None
    msvc_versions = sorted(os.listdir(msvc_versions_root))
    if not msvc_versions:
        return None
    msvc_dir = os.path.join(msvc_versions_root, msvc_versions[-1])
    msvc_bin = os.path.join(msvc_dir, "bin", "Hostx64", "x64")
    if not os.path.exists(os.path.join(msvc_bin, "link.exe")):
        return None

    # Pick the highest-versioned Windows SDK present (ucrt + um libs).
    sdk_root = os.path.join(vs_root, "Windows Kits", "10")
    sdk_lib_root = os.path.join(sdk_root, "Lib")
    if not os.path.isdir(sdk_lib_root):
        return None
    sdk_versions = sorted(os.listdir(sdk_lib_root))
    if not sdk_versions:
        return None
    sdk_ver = sdk_versions[-1]
    sdk_lib_x64_root = os.path.join(sdk_lib_root, sdk_ver)
    sdk_inc_root = os.path.join(sdk_root, "Include", sdk_ver)
    sdk_bin_x64 = os.path.join(sdk_root, "bin", sdk_ver, "x64")

    # Sanity-check the lib subtrees we'll point LIB at.
    if not all(
        os.path.isdir(p)
        for p in (
            os.path.join(sdk_lib_x64_root, "ucrt", "x64"),
            os.path.join(sdk_lib_x64_root, "um", "x64"),
        )
    ):
        return None

    env = os.environ.copy()
    path_extras = [msvc_bin]
    if os.path.isdir(sdk_bin_x64):
        path_extras.append(sdk_bin_x64)
    env["PATH"] = os.pathsep.join(path_extras + [env.get("PATH", "")])
    env["INCLUDE"] = os.pathsep.join(
        [
            os.path.join(msvc_dir, "include"),
            os.path.join(sdk_inc_root, "ucrt"),
            os.path.join(sdk_inc_root, "um"),
            os.path.join(sdk_inc_root, "shared"),
        ]
    )
    env["LIB"] = os.pathsep.join(
        [
            os.path.join(msvc_dir, "lib", "x64"),
            os.path.join(sdk_lib_x64_root, "ucrt", "x64"),
            os.path.join(sdk_lib_x64_root, "um", "x64"),
        ]
    )
    return env


# Mapping from transitive Rust sys-crate name to the OS packages required to
# compile it. Membership in this dict is what _probe_cargo_system_deps uses
# to translate a crate's dependency tree into a list of apt/brew packages to
# prompt for. Extend when a new cargo tool surfaces a new sys-crate.
RUST_SYS_DEP_MAP = {
    "openssl-sys": {
        "apt": ["libssl-dev", "pkg-config"],
        "brew": ["openssl@3", "pkg-config"],
    },
    "libdbus-sys": {
        "apt": ["libdbus-1-dev", "pkg-config"],
        "brew": ["dbus", "pkg-config"],
    },
    "aws-lc-sys": {
        "apt": ["cmake", "build-essential"],
        "brew": ["cmake"],
    },
    "ring": {
        "apt": ["clang", "build-essential"],
        "brew": [],
    },
    "libsecret-sys": {
        "apt": ["libsecret-1-dev", "pkg-config"],
        "brew": [],
    },
}


def _apt_pkg_installed(pkg):
    """Return True if apt package is installed, False if not, None if dpkg missing."""
    try:
        result = subprocess.run(["dpkg", "-s", pkg], capture_output=True, timeout=10)
        return result.returncode == 0
    except FileNotFoundError:
        return None
    except (subprocess.TimeoutExpired, Exception):
        return False


def _brew_pkg_installed(pkg):
    """Return True if brew formula is installed, False if not, None if brew missing."""
    try:
        result = subprocess.run(
            ["brew", "list", "--versions", pkg], capture_output=True, timeout=10
        )
        return result.returncode == 0
    except FileNotFoundError:
        return None
    except (subprocess.TimeoutExpired, Exception):
        return False


def _probe_cargo_system_deps(crate_name):
    """Return {'apt': [...], 'brew': [...]} of OS packages required to build crate.

    Runs ``cargo metadata`` against a throwaway Cargo.toml that depends on
    ``crate_name``, walks the transitive dependency tree, and intersects
    with RUST_SYS_DEP_MAP. Returns empty lists on probe failure so the
    caller can still attempt the install rather than block on probe errors.
    """
    empty = {"apt": [], "brew": []}
    if not is_tool("cargo"):
        return empty
    tmpdir = tempfile.mkdtemp(prefix="dotfiles-depprobe-")
    try:
        manifest = (
            "[package]\n"
            'name = "depprobe"\n'
            'version = "0.0.0"\n'
            'edition = "2021"\n'
            "\n"
            "[dependencies]\n"
            f'{crate_name} = "*"\n'
        )
        with open(os.path.join(tmpdir, "Cargo.toml"), "w", encoding="utf-8") as f:
            f.write(manifest)
        os.mkdir(os.path.join(tmpdir, "src"))
        with open(os.path.join(tmpdir, "src", "main.rs"), "w", encoding="utf-8") as f:
            f.write("fn main(){}\n")
        try:
            result = subprocess.run(
                ["cargo", "metadata", "--format-version=1", "--quiet"],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            print_warning(
                f"Could not probe system deps for {crate_name} "
                "(cargo metadata failed); proceeding without dep prompt."
            )
            return empty
        if result.returncode != 0:
            print_warning(
                f"Could not probe system deps for {crate_name} "
                "(cargo metadata returned non-zero); proceeding without dep prompt."
            )
            return empty
        try:
            meta = json.loads(result.stdout)
        except (ValueError, json.JSONDecodeError):
            return empty
        crate_names = {p.get("name", "") for p in meta.get("packages", [])}
        apt_pkgs, brew_pkgs = [], []
        for sys_crate, pkgs in RUST_SYS_DEP_MAP.items():
            if sys_crate not in crate_names:
                continue
            for p in pkgs.get("apt", []):
                if p not in apt_pkgs:
                    apt_pkgs.append(p)
            for p in pkgs.get("brew", []):
                if p not in brew_pkgs:
                    brew_pkgs.append(p)
        return {"apt": apt_pkgs, "brew": brew_pkgs}
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def _probe_npm_node_requirement(npm_pkg):
    """Return the minimum Node major version required by an npm package, or None."""
    if not is_tool("npm"):
        return None
    try:
        result = subprocess.run(
            ["npm", "view", npm_pkg, "engines.node"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None
    if result.returncode != 0:
        return None
    spec = result.stdout.strip()
    if not spec:
        return None
    nums = [int(n) for n in re.findall(r"\d+", spec)]
    if not nums:
        return None
    return min(nums)


def _ensure_system_packages(display_name, apt_pkgs, brew_pkgs):
    """Prompt for and install missing OS packages via apt (Linux) or brew (macOS).

    Returns True if every requested package is installed (or was nothing to
    install), False on install command failure, None if skipped (unsupported
    platform, missing sudo/brew, or user declined).
    """
    if is_linux():
        pkgs = list(apt_pkgs or [])
        platform_name = "apt"
    elif is_macos():
        pkgs = list(brew_pkgs or [])
        platform_name = "brew"
    elif is_windows():
        if apt_pkgs or brew_pkgs:
            print_warning(
                f"Skipping system-package check for {display_name}: "
                "automatic install not supported on Windows."
            )
            return None
        return True
    else:
        return True

    if not pkgs:
        return True

    missing = []
    for pkg in pkgs:
        if platform_name == "apt":
            installed = _apt_pkg_installed(pkg)
        else:
            installed = _brew_pkg_installed(pkg)
        if installed is None:
            print_warning(
                f"Skipping system-package check for {display_name}: "
                f"{'dpkg' if platform_name == 'apt' else 'brew'} not available."
            )
            return None
        if not installed:
            missing.append(pkg)

    if not missing:
        return True

    manual_cmd = (
        f"sudo apt-get install -y {' '.join(missing)}"
        if platform_name == "apt"
        else f"brew install {' '.join(missing)}"
    )

    if platform_name == "brew" and not is_tool("brew"):
        print_warning(
            f"Cannot install system packages for {display_name}: "
            "Homebrew not found. Install from https://brew.sh, then run:\n"
            f"    {manual_cmd}"
        )
        return None

    if not is_interactive():
        print_warning(
            f"Cannot install system packages for {display_name} in non-"
            f"interactive mode. Manual install:\n    {manual_cmd}"
        )
        return None

    print_tool_prompt(
        f"{display_name}: missing system packages",
        [
            f"Required to build {display_name}: {', '.join(missing)}",
        ],
        [
            f"{display_name} install will be skipped",
            f"Manual install: {manual_cmd}",
        ],
    )
    if not get_user_confirmation("Install system packages now? [y/N]: "):
        return None

    if platform_name == "apt":
        print(f"Installing system packages via apt-get: {' '.join(missing)}...")
        print_hint("  (sudo may prompt for your password)")
        cmd = ["sudo", "apt-get", "install", "-y", *missing]
    else:
        print(f"Installing system packages via brew: {' '.join(missing)}...")
        cmd = ["brew", "install", *missing]
    try:
        # Stream output so sudo's password prompt and apt's progress are visible.
        result = subprocess.run(cmd, timeout=600)
    except subprocess.TimeoutExpired:
        print_error(f"System-package install for {display_name} timed out")
        return False
    except FileNotFoundError as e:
        print_error(f"System-package install for {display_name} failed: {e}")
        return False

    if result.returncode == 0:
        print(
            colors.OK + f"✓ System packages installed: {' '.join(missing)}" + colors.END
        )
        return True
    print_error(
        f"Failed to install system packages for {display_name} "
        f"(exit {result.returncode}). See output above for the actual error."
    )
    return False


def _ensure_node_major(display_name, min_major):
    """Prompt to upgrade Node.js to at least min_major if current is older.

    Returns True if Node already meets requirement (or upgrade succeeded),
    False if the install ran but Node is still too old, None if skipped
    (unsupported platform, no sudo/brew, or user declined).
    """
    current = _node_major_version()
    if current is not None and current >= min_major:
        return True
    if current is None:
        print_warning(
            f"Cannot check Node version for {display_name}: node not found. "
            f"Install Node {min_major}+ manually from https://nodejs.org/."
        )
        return None

    if is_macos() and not is_tool("brew"):
        print_warning(
            f"Cannot upgrade Node for {display_name}: Homebrew not found. "
            f"Install from https://brew.sh, then run "
            f"`brew install node@{min_major}`."
        )
        return None
    if is_windows():
        print_warning(
            f"Auto-upgrade of Node not supported on Windows. "
            f"Install Node {min_major}+ from https://nodejs.org/ "
            "and re-run setup."
        )
        return None
    if not (is_linux() or is_macos()):
        return None
    if not is_interactive():
        print_warning(
            f"Cannot upgrade Node for {display_name} in non-interactive mode. "
            f"Install Node {min_major}+ manually and re-run setup."
        )
        return None

    print_tool_prompt(
        f"{display_name}: Node.js >= {min_major} required",
        [
            f"{display_name} requires Node {min_major}+; "
            f"current node is v{current}.x",
        ],
        [
            f"{display_name} install will be skipped",
            "Manual install: see https://nodejs.org/ "
            "or https://github.com/nodesource/distributions",
        ],
    )
    if not get_user_confirmation(f"Upgrade Node to {min_major}.x now? [y/N]: "):
        return None

    try:
        if is_linux():
            print(f"Adding NodeSource repository for Node {min_major}.x...")
            print_hint("  (sudo may prompt for your password)")
            setup_cmd = (
                f"curl -fsSL https://deb.nodesource.com/setup_{min_major}.x "
                "| sudo -E bash -"
            )
            # Stream output so curl progress and sudo password prompt show.
            setup_result = subprocess.run(["bash", "-c", setup_cmd], timeout=180)
            if setup_result.returncode != 0:
                print_error(
                    f"NodeSource setup script failed (exit "
                    f"{setup_result.returncode})."
                )
                return False
            print("Installing nodejs via apt-get...")
            install_result = subprocess.run(
                ["sudo", "apt-get", "install", "-y", "nodejs"], timeout=300
            )
            if install_result.returncode != 0:
                print_error(
                    f"Failed to install nodejs (exit {install_result.returncode}). "
                    "See output above for the actual error."
                )
                return False
        elif is_macos():
            formula = f"node@{min_major}"
            print(f"Installing {formula} via Homebrew...")
            install_result = subprocess.run(
                ["brew", "install", formula],
                capture_output=True,
                text=True,
                timeout=600,
            )
            if install_result.returncode != 0:
                print_error(
                    f"brew install {formula} failed: "
                    f"{install_result.stderr.strip() or install_result.stdout.strip()}"
                )
                return False
            # Best-effort: link the keg so `node` resolves to the new major.
            subprocess.run(
                ["brew", "link", "--overwrite", "--force", formula],
                capture_output=True,
                text=True,
                timeout=60,
            )
    except subprocess.TimeoutExpired:
        print_error(f"Node {min_major} install for {display_name} timed out")
        return False
    except FileNotFoundError as e:
        print_error(f"Node {min_major} install for {display_name} failed: {e}")
        return False

    post = _node_major_version()
    if post is None or post < min_major:
        print_error(
            f"Node upgrade reported success but current node is "
            f"v{post}.x (need {min_major}+)."
        )
        return False
    print(colors.OK + f"✓ Node {post} installed (>= {min_major} required)" + colors.END)
    return True


def _install_cargo_tool(
    display_name,
    binary_name,
    install_args,
    benefits,
    consequences,
    probe_crate=None,
):
    """Install a Rust CLI tool via ``cargo install`` with the standard prompt flow.

    ``install_args`` is the list of arguments after ``cargo install`` — e.g.
    ``["searchfox-cli"]`` for crates.io or ``["--git", "<url>"]`` for a git
    source. ``binary_name`` is the executable that ends up on PATH after
    install (used for the "already installed" early-out).

    Cargo output streams directly to the terminal rather than being captured.
    First-time installs can take 5-15 minutes and produce a lot of compile
    progress; capturing leaves the user staring at a frozen prompt and
    eats the actual error message on failure. No timeout for the same
    reason — the user can Ctrl-C an interactive cargo invocation.

    Returns True on install (or already installed), False on failure, None
    if skipped (cargo missing or user declined). Mirrors the style of
    install_ruff / install_black / install_markdownlint, except for the
    streaming-output departure.
    """
    print_installing_title(display_name)

    if is_tool(binary_name):
        print(f"{binary_name} is already installed")
        return True

    if not is_tool("cargo"):
        print_warning(
            f"Skipping {display_name}: cargo not found on PATH. "
            "Install Rust (re-run --mozilla rust, or via mozilla-build "
            "bootstrap) and re-run this step. Manual install command:\n"
            f"    cargo install {' '.join(install_args)}"
        )
        return None

    if probe_crate:
        deps = _probe_cargo_system_deps(probe_crate)
        deps_ok = _ensure_system_packages(
            display_name, deps.get("apt"), deps.get("brew")
        )
        if deps_ok is False:
            print_warning(f"Skipping {display_name}: system dependency install failed")
            return False
        if deps_ok is None:
            return None

    print_tool_prompt(display_name, benefits, consequences)
    if not get_user_confirmation():
        print(f"Skipping {display_name} installation")
        return None

    # On Windows, load MSVC build env so cargo's link step finds MSVC's
    # link.exe instead of /usr/bin/link.exe (MSYS coreutils' hardlink
    # utility, which silently shadows it on most Git Bash / mozilla-build
    # PATHs).
    env = _resolve_msvc_env()
    if is_windows() and env is None:
        print_warning(
            "Could not auto-locate MSVC build tools (tried vswhere.exe and\n"
            "  ~/.mozbuild/vs/). cargo's link step will likely pick up\n"
            "  /usr/bin/link.exe (MSYS coreutils) instead of MSVC's link.exe\n"
            "  and fail. Either install Visual Studio Build Tools 2022 with\n"
            "  the 'Desktop development with C++' workload, or run\n"
            "  `./mach bootstrap` in a Firefox checkout to populate\n"
            "  ~/.mozbuild/vs/, then re-run this step."
        )

    print(
        f"Installing {display_name} via cargo (downloads + compiles, "
        "may take several minutes; cargo output streams below)..."
    )
    if env is not None:
        print_hint("  Using MSVC build environment loaded via vcvars64.bat.")
    try:
        # Don't capture output — let cargo's progress / error messages stream
        # straight to the user's terminal.
        result = subprocess.run(["cargo", "install"] + install_args, env=env)
    except FileNotFoundError as e:
        print_error(f"Failed to invoke cargo for {display_name}: {e}")
        return False

    if result.returncode == 0:
        print(colors.OK + f"✓ {display_name} installed successfully" + colors.END)
        print_hint(
            "Binary is in ~/.cargo/bin (added to PATH by ~/.cargo/env, "
            "which --mozilla rust sources from .bashrc)."
        )
        return True
    print_error(
        f"Failed to install {display_name} (cargo exit {result.returncode}). "
        "See cargo output above for the actual error."
    )
    return False


def install_searchfox_cli(tracker=None):
    """Install searchfox-cli (Mozilla source code search CLI)."""
    return _install_cargo_tool(
        "searchfox-cli (Mozilla source code search)",
        "searchfox-cli",
        ["searchfox-cli"],
        [
            "Search Firefox source code from the terminal (searchfox.org backend)",
            "Used by skills like /firefox-implementation and /source-links",
        ],
        [
            "Skills relying on searchfox queries fall back to manual web lookups",
            "Manual install: cargo install searchfox-cli",
        ],
    )


def install_treeherder_cli(tracker=None):
    """Install treeherder-cli (Mozilla CI build/test status CLI)."""
    return _install_cargo_tool(
        "treeherder-cli (Mozilla CI status)",
        "treeherder-cli",
        ["--git", "https://github.com/padenot/treeherder-cli"],
        [
            "Query Mozilla Treeherder for try/autoland push results",
            "Used by skills like /try-push and /ci-failure-analysis",
        ],
        [
            "CI/try-push skills fall back to manual treeherder.mozilla.org lookups",
            "Manual install: cargo install --git "
            "https://github.com/padenot/treeherder-cli",
        ],
    )


def install_bmo_to_md(tracker=None):
    """Install bmo-to-md (Bugzilla bug -> Markdown converter for LLMs)."""
    return _install_cargo_tool(
        "bmo-to-md (Bugzilla -> Markdown for LLMs)",
        "bmo-to-md",
        ["--git", "https://github.com/ChunMinChang/bmo-to-md"],
        [
            "Render a BMO ticket as Markdown for easy paste into Claude/LLM context",
            "Used by triage / bug-start workflows that consume bug data",
        ],
        [
            "Manual bug-context curation — slower triage and bug-start sessions",
            "Manual install: cargo install --git "
            "https://github.com/ChunMinChang/bmo-to-md",
        ],
    )


def install_socorro_cli(tracker=None):
    """Install socorro-cli (Mozilla Socorro crash-reporting CLI)."""
    return _install_cargo_tool(
        "socorro-cli (Mozilla Socorro crash stats CLI)",
        "socorro-cli",
        ["socorro-cli"],
        [
            "Query crash-stats.mozilla.org from the terminal "
            "(signature search, crash details, facets)",
            "Used by triage / bugzilla-wrangler skills to quantify crash impact",
        ],
        [
            "Crash-volume enrichment falls back to manual crash-stats web lookups",
            "Manual install: cargo install socorro-cli",
        ],
        probe_crate="socorro-cli",
    )


def install_profiler_cli(tracker=None):
    """Install @firefox-devtools/profiler-cli (Firefox Profiler CLI) via npm."""
    display_name = "profiler-cli (Firefox Profiler CLI)"
    binary_name = "profiler-cli"
    npm_pkg = "@firefox-devtools/profiler-cli@latest"
    manual_cmd = f"npm install -g {npm_pkg}"

    print_installing_title(display_name)

    if not is_tool("npm"):
        if is_tool(binary_name):
            print(f"{binary_name} is already installed")
            return True
        print_warning(
            f"Skipping {display_name}: requires npm (Node.js). "
            "Install from https://nodejs.org/ and re-run setup, or run "
            f"`{manual_cmd}` manually later."
        )
        return None

    # Always verify the Node requirement, even if profiler-cli appears
    # installed: an old binary built against an unsupported Node major
    # may not run. Track whether an upgrade happened so we force a fresh
    # npm install afterward.
    min_major = _probe_npm_node_requirement(npm_pkg)
    node_was_upgraded = False
    if min_major is not None:
        current_before = _node_major_version()
        node_ok = _ensure_node_major(display_name, min_major)
        if node_ok is False:
            print_warning(f"Skipping {display_name}: Node {min_major}+ install failed")
            return False
        if node_ok is None:
            return None
        if current_before is not None and current_before < min_major:
            node_was_upgraded = True

    if is_tool(binary_name) and not node_was_upgraded:
        print(f"{binary_name} is already installed")
        return True

    if node_was_upgraded and is_tool(binary_name):
        print_hint(
            f"Reinstalling {binary_name} after Node upgrade to refresh "
            "native dependencies."
        )

    print_tool_prompt(
        display_name,
        [
            "Extract call trees, flamegraphs, and metrics from "
            "profiler.firefox.com share URLs or local .json.gz profiles",
            "Used by /analyze-profile and media bug-triage skills",
        ],
        [
            "Profile-analysis skills fall back to manual profiler.firefox.com inspection",
            f"Manual install: {manual_cmd}",
        ],
    )
    if not get_user_confirmation():
        print(f"Skipping {display_name} installation")
        return None

    # On Linux/macOS, npm's default global prefix is /usr/local which
    # requires root. Use --prefix=$HOME/.local so the binary lands in
    # ~/.local/bin (auto-added to PATH by dot.bashrc when it exists).
    # On Windows, npm -g defaults to a user-writable AppData path.
    npm_cmd = ["npm", "install", "-g"]
    if not is_windows():
        npm_cmd.extend(["--prefix", os.path.join(get_home_dir(), ".local")])
    npm_cmd.append(npm_pkg)

    print(f"Installing {display_name} via npm (may take a while)...")
    try:
        result = subprocess.run(npm_cmd, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        print_error(f"Failed to install {display_name}: timed out")
        return False
    except FileNotFoundError as e:
        print_error(f"Failed to invoke npm for {display_name}: {e}")
        return False

    if result.returncode == 0:
        print(colors.OK + f"✓ {display_name} installed successfully" + colors.END)
        return True
    print_error(
        f"Failed to install {display_name}: {result.stderr.strip() or result.stdout.strip()}"
    )
    return False


def mozilla_cli_tools_init(tracker=None):
    """Install Mozilla-adjacent CLI tools used by Firefox/Claude workflows.

    Bundle of cargo- and npm-installed tools: searchfox-cli, treeherder-cli,
    bmo-to-md, socorro-cli (cargo), and profiler-cli (npm). Each is
    independently optional and prompts the user before installing.
    Selectable as ``--mozilla cli-tools``; included by default when
    ``--mozilla`` runs without explicit args.

    Returns True if every selected install succeeded or was skipped cleanly,
    False if any returned False (hard failure). Skipped/already-installed
    tools count as success.
    """
    print_installing_title("Mozilla CLI tools (cargo / npm)", True)
    installers = [
        install_searchfox_cli,
        install_treeherder_cli,
        install_bmo_to_md,
        install_socorro_cli,
        install_profiler_cli,
    ]
    all_ok = True
    for fn in installers:
        if fn(tracker) is False:
            all_ok = False
    return all_ok


# Development Tools (Pre-commit Hooks)
# ---------------------------------------


def print_tool_prompt(tool_name, benefits, consequences):
    """Display information about a dev tool and prompt user for installation."""
    print("\n" + colors.BOLD + tool_name + colors.END)
    print(colors.OK + "Benefits:" + colors.END)
    for benefit in benefits:
        print("  • {}".format(benefit))
    print(colors.WARNING + "If you skip:" + colors.END)
    for consequence in consequences:
        print("  • {}".format(consequence))


def is_interactive():
    """Check if running in interactive mode (has TTY)."""
    return sys.stdin.isatty()


def get_user_confirmation(
    prompt="Install this tool? [y/N]: ", default_non_interactive=False
):
    """Get yes/no confirmation from user.

    Args:
        prompt: The prompt message to display
        default_non_interactive: Default value to return in non-interactive mode

    Returns:
        True if user confirms, False otherwise
    """
    # In dry-run mode, don't prompt
    if DRY_RUN:
        return False

    # In non-interactive mode, use default
    if not is_interactive():
        action = "Installing" if default_non_interactive else "Skipping"
        print(
            colors.WARNING
            + f"Non-interactive mode detected: {action} (use default)"
            + colors.END
        )
        return default_non_interactive

    # Interactive mode: prompt user
    try:
        response = input(prompt).strip().lower()
        return response in ["y", "yes"]
    except (EOFError, KeyboardInterrupt):
        print()  # New line after Ctrl+C
        return False


def install_shellcheck(tracker=None):
    """Install shellcheck for bash script validation."""
    print_installing_title("shellcheck (bash script linter)")

    # Check if already installed
    if is_tool("shellcheck"):
        print("shellcheck is already installed")
        return True

    # Pre-check the platform-appropriate prerequisite before prompting
    has_sudo = False
    if is_linux():
        try:
            result = subprocess.run(
                ["sudo", "-n", "true"], capture_output=True, timeout=5
            )
            has_sudo = result.returncode == 0
        except Exception:
            has_sudo = False
        if not has_sudo:
            print_warning(
                "Skipping shellcheck: passwordless sudo not available. "
                "Install manually: sudo apt-get install shellcheck."
            )
            return None  # Skipped
    elif is_macos():
        if not is_tool("brew"):
            print_warning(
                "Skipping shellcheck: Homebrew not found. Install from "
                "https://brew.sh, then run `brew install shellcheck`."
            )
            return None  # Skipped
    elif is_windows():
        print_warning(
            "Skipping shellcheck: auto-install not supported on Windows. "
            "Install via `scoop install shellcheck` or `choco install shellcheck`."
        )
        return None  # Skipped
    else:
        print_warning(
            "Skipping shellcheck: unsupported platform for automatic install. "
            "See https://github.com/koalaman/shellcheck#installing"
        )
        return None  # Skipped

    # Display info and prompt user
    print_tool_prompt(
        "ShellCheck",
        [
            "Catches common bash scripting errors before they cause issues",
            "Enforces best practices for portability and safety",
            "Detects syntax errors, unquoted variables, and unsafe patterns",
        ],
        [
            "Pre-commit hook will skip bash script validation",
            "Bash errors may only be caught at runtime",
            "You can manually install later with: sudo apt-get install shellcheck (Linux) or brew install shellcheck (macOS)",
        ],
    )

    if not get_user_confirmation():
        print("Skipping shellcheck installation")
        return None  # Skipped

    # Install based on platform
    try:
        if is_linux():
            print("Installing shellcheck via apt-get...")
            result = subprocess.run(
                ["sudo", "apt-get", "install", "-y", "shellcheck"],
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode == 0:
                print(colors.OK + "✓ shellcheck installed successfully" + colors.END)
                return True
            else:
                print_error("Failed to install shellcheck: {}".format(result.stderr))
                return False

        elif is_macos():
            print("Installing shellcheck via homebrew...")
            result = subprocess.run(
                ["brew", "install", "shellcheck"],
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode == 0:
                print(colors.OK + "✓ shellcheck installed successfully" + colors.END)
                return True
            else:
                print_error("Failed to install shellcheck: {}".format(result.stderr))
                return False

    except subprocess.TimeoutExpired:
        print_error("Installation timed out")
        return False
    except Exception as e:
        print_error("Installation failed: {}".format(str(e)))
        return False


def install_ruff(tracker=None):
    """Install ruff for Python linting and formatting."""
    print_installing_title("ruff (Python linter/formatter)")

    # Check if already installed
    if is_tool("ruff"):
        print("ruff is already installed")
        return True

    # Pre-check the prerequisite before bothering the user with a prompt
    if not is_tool("pip3"):
        print_warning(
            "Skipping ruff: pip3 not found. Install Python 3 + pip and "
            "re-run setup, or run `pip3 install --user ruff` manually."
        )
        return None  # Skipped

    # Display info and prompt user
    print_tool_prompt(
        "Ruff",
        [
            "Fast Python linter (10-100x faster than pylint/flake8)",
            "Catches Python errors, style issues, and code smells",
            "Enforces PEP 8 and other Python best practices",
        ],
        [
            "Pre-commit hook will skip Python validation",
            "Python code issues may only be caught during execution or review",
            "You can manually install later with: pip3 install --user ruff",
        ],
    )

    if not get_user_confirmation():
        print("Skipping ruff installation")
        return None  # Skipped

    # Install via pip
    try:
        print("Installing ruff via pip...")
        result = subprocess.run(
            ["pip3", "install", "--user", "ruff"],
            capture_output=True,
            text=True,
            timeout=180,
        )
        if result.returncode == 0:
            print(colors.OK + "✓ ruff installed successfully" + colors.END)
            return True
        else:
            print_error("Failed to install ruff: {}".format(result.stderr))
            return False

    except subprocess.TimeoutExpired:
        print_error("Installation timed out")
        return False
    except Exception as e:
        print_error("Installation failed: {}".format(str(e)))
        return False


def install_black(tracker=None):
    """Install black for Python code formatting."""
    print_installing_title("black (Python code formatter)")

    # Check if already installed
    if is_tool("black"):
        print("black is already installed")
        return True

    # Pre-check the prerequisite before bothering the user with a prompt
    if not is_tool("pip3"):
        print_warning(
            "Skipping black: pip3 not found. Install Python 3 + pip and "
            "re-run setup, or run `pip3 install --user black` manually."
        )
        return None  # Skipped

    # Display info and prompt user
    print_tool_prompt(
        "Black",
        [
            "Automatically formats Python code to a consistent style",
            "Saves time on code style discussions and manual formatting",
            "Widely adopted by the Python community (e.g., Django, pytest)",
        ],
        [
            "Pre-commit hook will skip Python auto-formatting checks",
            "Code style may be inconsistent across commits",
            "You can manually install later with: pip3 install --user black",
        ],
    )

    if not get_user_confirmation():
        print("Skipping black installation")
        return None  # Skipped

    # Install via pip
    try:
        print("Installing black via pip...")
        result = subprocess.run(
            ["pip3", "install", "--user", "black"],
            capture_output=True,
            text=True,
            timeout=180,
        )
        if result.returncode == 0:
            print(colors.OK + "✓ black installed successfully" + colors.END)
            return True
        else:
            print_error("Failed to install black: {}".format(result.stderr))
            return False

    except subprocess.TimeoutExpired:
        print_error("Installation timed out")
        return False
    except Exception as e:
        print_error("Installation failed: {}".format(str(e)))
        return False


def install_markdownlint(tracker=None):
    """Install markdownlint-cli for markdown validation."""
    print_installing_title("markdownlint (markdown linter)")

    # Check if already installed
    if is_tool("markdownlint"):
        print("markdownlint is already installed")
        return True

    # Pre-check the prerequisite before bothering the user with a prompt
    if not is_tool("npm"):
        print_warning(
            "Skipping markdownlint: requires npm (Node.js). "
            "Install from https://nodejs.org/ and re-run setup, or run "
            "`npm install -g markdownlint-cli` manually later."
        )
        return None  # Skipped

    # Display info and prompt user
    print_tool_prompt(
        "Markdownlint",
        [
            "Validates markdown files for syntax and style consistency",
            "Catches broken links, malformed tables, and formatting issues",
            "Ensures documentation is properly formatted",
        ],
        [
            "Pre-commit hook will skip markdown validation",
            "Documentation formatting issues may go unnoticed",
            "You can manually install later with: npm install -g markdownlint-cli",
        ],
    )

    if not get_user_confirmation():
        print("Skipping markdownlint installation")
        return None  # Skipped

    # Install via npm. On Linux/macOS, npm's default global prefix is
    # /usr/local which requires root. Use --prefix=$HOME/.local so the
    # binary lands in ~/.local/bin (which dot.bashrc auto-adds to PATH
    # when the dir exists). On Windows, npm -g defaults to a
    # user-writable AppData path, so leave it alone.
    #
    # markdownlint-cli@0.45+ pulls in deps that hard-fail on Node <20
    # (string-width@8 uses the regex `v` flag). Pin to the last
    # Node-18-compatible release on older runtimes.
    pkg = "markdownlint-cli"
    if _node_major_version() and _node_major_version() < 20:
        pkg = "markdownlint-cli@0.44.0"
    npm_cmd = ["npm", "install", "-g"]
    if not is_windows():
        npm_cmd.extend(["--prefix", os.path.join(get_home_dir(), ".local")])
    npm_cmd.append(pkg)
    try:
        print("Installing {} via npm (may take a while)...".format(pkg))
        result = subprocess.run(
            npm_cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode == 0:
            print(colors.OK + "✓ markdownlint installed successfully" + colors.END)
            return True
        else:
            print_error("Failed to install markdownlint: {}".format(result.stderr))
            return False

    except subprocess.TimeoutExpired:
        print_error("Installation timed out")
        return False
    except Exception as e:
        print_error("Installation failed: {}".format(str(e)))
        return False


def setup_precommit_hooks(tracker=None):
    """Create project-local pre-commit hook with validation checks."""
    print_installing_title("pre-commit hooks")

    # Check if we're in a git repository
    git_dir = os.path.join(BASE_DIR, ".git")
    if not os.path.isdir(git_dir):
        print_error("Not in a git repository. Cannot install hooks.")
        return False

    hooks_dir = os.path.join(git_dir, "hooks")
    precommit_hook = os.path.join(hooks_dir, "pre-commit")

    # Create hooks directory if it doesn't exist
    if not os.path.exists(hooks_dir):
        print("Creating hooks directory: {}".format(hooks_dir))
        os.makedirs(hooks_dir, exist_ok=True)

    # Create pre-commit hook script
    hook_content = """#!/bin/bash
# Pre-commit hook for dotfiles repository
# This hook runs validation checks on staged files before allowing commit.
# It warns about issues but allows commits to proceed (non-blocking).

# NOTE: This hook is project-local (only for this dotfiles repo)
# and will not affect hooks in other git repositories.

echo "Running pre-commit validation checks..."

# Track if any checks found issues
has_warnings=false

# Get list of staged files
staged_files=$(git diff --cached --name-only --diff-filter=ACM)

# Check if we have any staged files
if [ -z "$staged_files" ]; then
    echo "No files staged for commit."
    exit 0
fi

# === ShellCheck: Bash script validation ===
if command -v shellcheck >/dev/null 2>&1; then
    echo "→ Running shellcheck on bash scripts..."
    bash_files=$(echo "$staged_files" | grep -E '\\.(sh|bash)$|^dot\\.')
    if [ -n "$bash_files" ]; then
        for file in $bash_files; do
            if [ -f "$file" ]; then
                if ! shellcheck -x "$file"; then
                    echo "  ⚠ Warning: shellcheck found issues in $file"
                    has_warnings=true
                fi
            fi
        done
    else
        echo "  ✓ No bash files to check"
    fi
else
    echo "  ⊘ Skipping shellcheck (not installed)"
fi

# === Ruff: Python linting ===
if command -v ruff >/dev/null 2>&1; then
    echo "→ Running ruff on Python files..."
    python_files=$(echo "$staged_files" | grep '\\.py$')
    if [ -n "$python_files" ]; then
        if ! ruff check $python_files; then
            echo "  ⚠ Warning: ruff found issues in Python files"
            has_warnings=true
        fi
    else
        echo "  ✓ No Python files to check"
    fi
else
    echo "  ⊘ Skipping ruff (not installed)"
fi

# === Black: Python formatting ===
if command -v black >/dev/null 2>&1; then
    echo "→ Checking Python code formatting with black..."
    python_files=$(echo "$staged_files" | grep '\\.py$')
    if [ -n "$python_files" ]; then
        if ! black --check $python_files 2>/dev/null; then
            echo "  ⚠ Warning: black found formatting issues"
            echo "    Run 'black <file>' to auto-format"
            has_warnings=true
        fi
    else
        echo "  ✓ No Python files to check"
    fi
else
    echo "  ⊘ Skipping black (not installed)"
fi

# === Markdownlint: Markdown validation ===
if command -v markdownlint >/dev/null 2>&1; then
    echo "→ Running markdownlint on markdown files..."
    md_files=$(echo "$staged_files" | grep '\\.md$')
    if [ -n "$md_files" ]; then
        if ! markdownlint $md_files 2>/dev/null; then
            echo "  ⚠ Warning: markdownlint found issues in markdown files"
            has_warnings=true
        fi
    else
        echo "  ✓ No markdown files to check"
    fi
else
    echo "  ⊘ Skipping markdownlint (not installed)"
fi

# === Final verdict ===
echo ""
if [ "$has_warnings" = true ]; then
    echo "⚠ Pre-commit validation found issues (see above)"
    echo "  Allowing commit anyway (hooks are non-blocking)"
    echo "  Please review and fix issues in a follow-up commit"
else
    echo "✓ All validation checks passed"
fi

# Always allow commit (non-blocking)
exit 0
"""

    try:
        # Check if hook already exists
        if os.path.exists(precommit_hook):
            if DRY_RUN:
                print_dry_run(
                    "Pre-commit hook already exists: {}".format(precommit_hook)
                )
                print_dry_run("Would prompt to replace existing hook")
                return True
            else:
                print_warning(
                    "Pre-commit hook already exists: {}".format(precommit_hook)
                )
                if not get_user_confirmation(
                    "Replace existing hook? [y/N]: ", default_non_interactive=False
                ):
                    print("Keeping existing hook")
                    return True  # Not an error

        # Write hook script
        if DRY_RUN:
            print_dry_run("Would create pre-commit hook: {}".format(precommit_hook))
            print_dry_run("Would make hook executable (chmod 755)")
            print_hint("Hook would be project-local (only for this dotfiles repo)")
            print_hint("Hook would warn about issues but allow commits to proceed")
        else:
            print("Creating pre-commit hook: {}".format(precommit_hook))
            # Atomic write: write to .tmp then rename, so an interrupted
            # run can never leave a 0-byte hook that git refuses to spawn.
            # encoding=utf-8 because the hook content has unicode glyphs
            # (->, check, cross, skip) that cp1252 can't encode on Windows.
            tmp_hook = precommit_hook + ".tmp"
            with open(tmp_hook, "w", encoding="utf-8", newline="\n") as f:
                f.write(hook_content)
            os.chmod(tmp_hook, 0o755)
            os.replace(tmp_hook, precommit_hook)

            print(colors.OK + "✓ Pre-commit hook installed successfully" + colors.END)
            print_hint("Hook is project-local (only for this dotfiles repo)")
            print_hint("It will warn about issues but allow commits to proceed")

        return True

    except IOError as e:
        print_error("Failed to create pre-commit hook: {}".format(str(e)))
        return False
    except Exception as e:
        print_error("Unexpected error: {}".format(str(e)))
        return False


def dev_tools_init(dev_tools_arg, tracker=None):
    """
    Initialize development tools (linters, formatters, pre-commit hooks).

    Args:
        dev_tools_arg: Value from --dev-tools argument (None, [], or list of tools)
        tracker: Optional ChangeTracker to record changes

    Returns:
        None if skipped, True if all succeeded, False if any failed
    """
    print_installing_title("development tools", True)

    # If dev_tools_arg is None and not explicitly invoked, ask user (skip in dry-run)
    if dev_tools_arg is None:
        if DRY_RUN:
            print_dry_run("Would prompt user to set up development tools")
            print_dry_run("Skipping dev-tools in dry-run mode")
            return None

        print(
            "\nDevelopment tools include linters and formatters for bash, Python, and markdown."
        )
        print("These tools help catch errors early via pre-commit hooks.")
        print("")
        print(colors.OK + "Benefits:" + colors.END)
        print("  • Catch syntax errors before they reach the repository")
        print("  • Enforce consistent code style across all files")
        print("  • Reduce code review time by automating basic checks")
        print("  • Find bugs early (e.g., unquoted variables, unused imports)")
        print("")

        if not get_user_confirmation(
            "Would you like to set up development tools? [y/N]: ",
            default_non_interactive=False,
        ):
            print_warning("Skipping development tools setup")
            return None  # None = skipped, not failure

        # User said yes, proceed with all tools
        dev_tools_arg = []  # Empty list means install all

    # In dry-run mode, just show what would be done
    if DRY_RUN and dev_tools_arg is not None:
        print_dry_run("Would install development tools")
        if dev_tools_arg:
            print_dry_run("Specified tools: {}".format(", ".join(dev_tools_arg)))
        else:
            print_dry_run(
                "Would install all tools: shellcheck, ruff, black, markdownlint"
            )
        print_dry_run("Would set up pre-commit hooks")
        return True

    print_verbose("dev_tools_arg: {}".format(dev_tools_arg))

    # Define available tools
    tools = {
        "shellcheck": install_shellcheck,
        "ruff": install_ruff,
        "black": install_black,
        "markdownlint": install_markdownlint,
    }

    # Select which tools to install
    if dev_tools_arg:
        # User specified specific tools
        options = [k for k in dev_tools_arg if k in tools]
        print_verbose("Selected tools: {}".format(options))
    else:
        # No tools specified: ask about all
        options = list(tools.keys())
        print_verbose("No tools specified, asking about all: {}".format(options))

    # Install each tool
    results = {}
    for tool_name in options:
        result = tools[tool_name](tracker)
        results[tool_name] = result

    # Pre-commit hook is only meaningful when at least one validation
    # tool is available (shellcheck/ruff/black/markdownlint already
    # present, or one we just installed). Otherwise it's a no-op that
    # only echoes "skipping" lines on every commit.
    #
    # `is_tool` alone isn't sufficient on Windows: pip3 --user installs
    # land in %APPDATA%\Python\PythonXX\Scripts\, which isn't on the
    # default Git Bash PATH, so a freshly-installed ruff/black would
    # appear missing. Trust the install_* return values (True == we
    # just put it in place) in addition to the on-PATH check.
    just_installed = any(v is True for v in results.values())
    any_on_path = any(is_tool(t) for t in tools)
    if just_installed or any_on_path:
        # On Windows, warn if the just-installed tools aren't yet on
        # PATH so the user knows the hook will skip them at commit
        # time until they fix it.
        if is_windows() and just_installed and not any_on_path:
            scripts_hint = (
                "%APPDATA%\\Python\\PythonXX\\Scripts (pip3 --user) and/or "
                "%APPDATA%\\npm (npm -g)"
            )
            print_warning(
                "Tools were installed but none are on PATH. "
                f"Add {scripts_hint} to PATH so the pre-commit "
                "hook can find them."
            )
        print("")
        print(
            "Pre-commit hooks will run the installed tools automatically before each commit."
        )
        hook_result = setup_precommit_hooks(tracker)
        # Treat a hook-install hiccup as a warning, not a failure: the
        # hook is project-local to the dotfiles repo and not having it
        # doesn't break anything else, so don't trigger a full rollback
        # over it.
        if hook_result is False:
            print_warning(
                "Pre-commit hook setup failed; continuing without it. "
                "Re-run setup.py --dev-tools later to retry."
            )
            results["pre-commit-hook"] = None
        else:
            results["pre-commit-hook"] = hook_result
    else:
        print_hint("No validation tools installed; skipping pre-commit hook setup.")
        results["pre-commit-hook"] = None

    # Determine overall success
    # None = skipped (ok), False = failed, True = succeeded
    failures = [name for name, result in results.items() if result is False]

    if failures:
        print("")
        print(
            colors.WARNING
            + "Some tools failed to install: {}".format(", ".join(failures))
            + colors.END
        )
        return False
    else:
        print("")
        print(colors.OK + "✓ Development tools setup complete" + colors.END)
        return True


# Installation Verification
# ------------------------------------------------------------------------------


def verify_symlinks():
    """Verify all symlinks created during setup are valid."""
    symlinks_to_check = [
        (os.path.join(HOME_DIR, ".dotfiles"), BASE_DIR, True),  # Must exist
    ]

    # Add platform-specific symlinks
    if is_linux():
        symlinks_to_check.append(
            (
                os.path.join(HOME_DIR, ".settings_linux"),
                os.path.join(BASE_DIR, "dot.settings_linux"),
                False,
            )  # Optional
        )
    elif is_macos():
        symlinks_to_check.append(
            (
                os.path.join(HOME_DIR, ".settings_darwin"),
                os.path.join(BASE_DIR, "dot.settings_darwin"),
                False,
            )  # Optional
        )
    elif is_windows():
        symlinks_to_check.append(
            (
                os.path.join(HOME_DIR, ".settings_windows"),
                os.path.join(BASE_DIR, "dot.settings_windows"),
                False,
            )  # Optional
        )

    issues = []
    for target_path, expected_source, required in symlinks_to_check:
        # Check if exists
        if not os.path.lexists(target_path):
            if required:
                issues.append("{} does not exist".format(target_path))
            continue

        # Check if it's a symlink
        if os.path.islink(target_path):
            # Check if broken (symlink exists but target doesn't)
            if not os.path.exists(target_path):
                actual_source = os.readlink(target_path)
                issues.append(
                    "{} is a broken symlink (points to {})".format(
                        target_path, actual_source
                    )
                )
            # Check if readable
            elif not os.access(target_path, os.R_OK):
                issues.append("{} exists but is not readable".format(target_path))

    return issues


def verify_file_readability():
    """Verify critical files are readable."""
    files_to_check = [
        (os.path.join(BASE_DIR, "dot.bashrc"), True),  # Required
        (os.path.join(BASE_DIR, "utils.sh"), True),  # Required
        (os.path.join(BASE_DIR, "git", "utils.sh"), True),  # Required
        (os.path.join(BASE_DIR, "git", "config"), True),  # Required
    ]

    # Add platform-specific files
    if is_linux():
        files_to_check.append(
            (os.path.join(BASE_DIR, "dot.settings_linux"), False)  # Optional
        )
    elif is_macos():
        files_to_check.append(
            (os.path.join(BASE_DIR, "dot.settings_darwin"), False)  # Optional
        )
    elif is_windows():
        files_to_check.append(
            (os.path.join(BASE_DIR, "dot.settings_windows"), False)  # Optional
        )

    issues = []
    for filepath, required in files_to_check:
        if not os.path.exists(filepath):
            if required:
                issues.append("{} is missing".format(filepath))
        elif not os.access(filepath, os.R_OK):
            issues.append("{} is not readable".format(filepath))

    return issues


def verify_bash_syntax():
    """Verify bash files have valid syntax using bash -n."""
    if not is_tool("bash"):
        return []  # Can't check without bash

    bash_files = [
        os.path.join(BASE_DIR, "dot.bashrc"),
        os.path.join(BASE_DIR, "utils.sh"),
        os.path.join(BASE_DIR, "git", "utils.sh"),
    ]

    # Add platform-specific files
    if is_linux():
        bash_files.append(os.path.join(BASE_DIR, "dot.settings_linux"))
    elif is_macos():
        bash_files.append(os.path.join(BASE_DIR, "dot.settings_darwin"))
    elif is_windows():
        bash_files.append(os.path.join(BASE_DIR, "dot.settings_windows"))

    issues = []
    for filepath in bash_files:
        if not os.path.exists(filepath):
            continue  # Already reported in readability check

        try:
            # Use bash -n to check syntax without executing
            result = subprocess.run(
                ["bash", "-n", filepath], capture_output=True, text=True, timeout=5
            )

            if result.returncode != 0:
                # Clean up error message (remove "bash: " prefix if present)
                error_msg = result.stderr.strip()
                if error_msg.startswith("bash: "):
                    error_msg = error_msg[6:]
                issues.append(
                    "{} has syntax errors: {}".format(
                        os.path.basename(filepath), error_msg
                    )
                )
        except subprocess.TimeoutExpired:
            issues.append("{} syntax check timed out".format(filepath))
        except Exception as e:
            issues.append("{} syntax check failed: {}".format(filepath, str(e)))

    return issues


def verify_git_config():
    """Verify git configuration is valid."""
    if not is_tool("git"):
        return []  # Can't check without git

    issues = []

    # Check git config file exists
    git_config_path = os.path.join(BASE_DIR, "git", "config")
    if not os.path.exists(git_config_path):
        issues.append("git/config file missing")
        return issues

    # Check if included in global config
    try:
        result = subprocess.run(
            ["git", "config", "--global", "--get", "include.path"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            issues.append("git include.path not configured")
        elif git_config_path not in result.stdout:
            issues.append("git include.path not pointing to {}".format(git_config_path))
    except subprocess.TimeoutExpired:
        issues.append("git config check timed out")
    except Exception as e:
        issues.append("git config check failed: {}".format(str(e)))

    return issues


def verify_installation():
    """
    Verify installation completed successfully.

    Returns:
        (bool, list): (success, list of issues)
    """
    print_installing_title("Verifying Installation")

    all_issues = []

    # Phase 1: Symlinks
    print("Checking symlinks...")
    issues = verify_symlinks()
    if issues:
        all_issues.extend(issues)
        for issue in issues:
            print_warning(issue)
    else:
        print(colors.OK + "✓ All symlinks valid" + colors.END)

    # Phase 2: File readability
    print("Checking file readability...")
    issues = verify_file_readability()
    if issues:
        all_issues.extend(issues)
        for issue in issues:
            print_error(issue)
    else:
        print(colors.OK + "✓ All files readable" + colors.END)

    # Phase 3: Bash syntax
    print("Checking bash syntax...")
    issues = verify_bash_syntax()
    if issues:
        all_issues.extend(issues)
        for issue in issues:
            print_error(issue)
    else:
        print(colors.OK + "✓ Bash files syntax valid" + colors.END)

    # Phase 4: Git config
    print("Checking git configuration...")
    issues = verify_git_config()
    if issues:
        all_issues.extend(issues)
        for issue in issues:
            print_warning(issue)
    else:
        print(colors.OK + "✓ Git configuration valid" + colors.END)

    # Summary
    if all_issues:
        print(
            "\n"
            + colors.FAIL
            + "Verification found {} issue(s):".format(len(all_issues))
            + colors.END
        )
        for issue in all_issues:
            print("  - " + issue)
        return False, all_issues
    else:
        print("\n" + colors.OK + "✓ Installation verification passed!" + colors.END)
        return True, []


def show_setup_summary(results):
    """Display a summary of setup results and provide guidance."""
    print("\n" + "=" * 50)
    print("Setup Summary")
    print("=" * 50)

    status_symbols = {True: "✓", False: "✗", None: "⊘"}
    status_labels = {True: "SUCCESS", False: "FAILED", None: "SKIPPED"}

    for name, result in results.items():
        symbol = status_symbols.get(result, "?")
        label = status_labels.get(result, "UNKNOWN")
        print("{} {}: {}".format(symbol, name.capitalize(), label))

    failures = [name for name, result in results.items() if result is False]
    if failures:
        print("\n" + colors.FAIL + "Action Required:" + colors.END)
        for name in failures:
            if name == "git":
                print("  - Install git and re-run setup.py")
            elif name == "mozilla":
                print(
                    "  - Check mozilla tools (cargo, etc.) and re-run setup.py --mozilla"
                )
            elif name == "dev-tools":
                print(
                    "  - Check tool installation errors above and re-run setup.py --dev-tools"
                )
                print(
                    "    Or install tools manually and run setup.py --dev-tools again"
                )
            else:
                print("  - Fix {} issues above and re-run setup.py".format(name))
        print(
            "\n"
            + colors.FAIL
            + "Setup completed with errors. Fix the issues above and re-run."
            + colors.END
        )
    else:
        print("\n" + colors.OK + "All steps completed successfully!" + colors.END)


# ============================================================================
# Claude Code Security Hooks
# ============================================================================


def claude_security_init(tracker, dry_run=False):
    """
    Install Claude Code security hooks (system-wide).
    Merges hooks into ~/.claude.json without overwriting existing hooks.

    The hook command points directly at the in-repo script
    ``<repo>/claude/security-read-blocker.py``. No deployed copy or
    extra ``$HOME`` directory is created. Block events are appended
    to ``~/.claude/security-blocks.log``.
    """
    print_title("Claude Code Security Hooks")

    hook_path = os.path.join(BASE_DIR, "claude", "security-read-blocker.py")
    claude_config = os.path.join(get_home_dir(), ".claude.json")
    legacy_dir = os.path.join(get_home_dir(), ".dotfiles-claude-hooks")
    log_file = os.path.join(get_home_dir(), ".claude", "security-blocks.log")

    if dry_run:
        print(f"\n{colors.HINT}DRY RUN MODE - Would perform these actions:{colors.END}")
        print(f"  1. Use hook script in-place: {hook_path}")

        if os.path.exists(claude_config):
            print(
                f"  2. Backup: {claude_config} -> {claude_config}.backup-claude-security"
            )
            print(f"  3. Merge security hooks into: {claude_config}")
        else:
            print(f"  2. Create: {claude_config} with security hooks")

        if os.path.isdir(legacy_dir):
            print(f"  4. Clean up legacy dir: {legacy_dir}")

        print(f"\n{colors.HINT}Would add to ~/.claude.json:{colors.END}")
        security_hook_config = {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "Read|Bash|Grep|Glob",
                        "hooks": [
                            {"type": "command", "command": str(hook_path), "timeout": 5}
                        ],
                    }
                ]
            }
        }
        print(json.dumps(security_hook_config, indent=2))
        print(f"\n{colors.HINT}Run without --dry-run to apply changes{colors.END}")
        return True

    # 1. Verify the in-repo hook is present.
    if not os.path.exists(hook_path):
        print_error(f"Hook script not found: {hook_path}")
        return False

    # 2. Backup and load ~/.claude.json
    if os.path.exists(claude_config):
        backup = os.path.dirname(claude_config) + "/.claude.json.backup-claude-security"
        shutil.copy(claude_config, backup)
        print_hint(f"Backed up config to: {backup}")

        with open(claude_config, "r", encoding="utf-8") as f:
            config = json.load(f)
    else:
        config = {}
        print_hint("Creating new ~/.claude.json")

    # 3. Merge security hooks (non-destructive). Replace any prior
    # security-read-blocker.py entry (e.g. pointing at the legacy
    # ~/.dotfiles-claude-hooks/ path) so the command field stays
    # pointed at the current in-repo script.
    if "hooks" not in config:
        config["hooks"] = {}
    if "PreToolUse" not in config["hooks"]:
        config["hooks"]["PreToolUse"] = []

    def _entry_is_ours(entry):
        return any(
            "security-read-blocker.py" in str(h.get("command", ""))
            for h in entry.get("hooks", [])
        )

    config["hooks"]["PreToolUse"] = [
        e for e in config["hooks"]["PreToolUse"] if not _entry_is_ours(e)
    ]
    config["hooks"]["PreToolUse"].append(
        {
            "matcher": "Read|Bash|Grep|Glob",
            "hooks": [{"type": "command", "command": str(hook_path), "timeout": 5}],
        }
    )

    # 4. Write back atomically
    temp_file = claude_config + ".tmp"
    with open(temp_file, "w", encoding="utf-8", newline="\n") as f:
        json.dump(config, f, indent=2)
    os.replace(temp_file, claude_config)

    # 5. Migrate away from the legacy ~/.dotfiles-claude-hooks/ directory
    # if a previous install left it behind. Move any existing log file
    # into ~/.claude/ so audit history is preserved.
    if os.path.isdir(legacy_dir):
        legacy_script = os.path.join(legacy_dir, "security-read-blocker.py")
        legacy_log = os.path.join(legacy_dir, "security-blocks.log")
        if os.path.lexists(legacy_script):
            os.unlink(legacy_script)
        if os.path.exists(legacy_log) and not os.path.exists(log_file):
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            shutil.move(legacy_log, log_file)
            print_hint(f"Moved legacy log to {log_file}")
        try:
            os.rmdir(legacy_dir)
            print_hint(f"Removed legacy directory: {legacy_dir}")
        except OSError:
            print_warning(f"Legacy dir {legacy_dir} is non-empty; left in place")

    print("✓ Claude Code security hooks installed")
    print_hint(f"  Hook script: {hook_path}")
    print_hint(f"  Config file: {claude_config}")
    print_hint(f"  Log file:    {log_file} (created on first block)")
    print("")
    print_warning("IMPORTANT: Restart Claude Code for hooks to take effect")

    return True


def claude_security_remove(dry_run=False):
    """Remove Claude Code security hooks from ~/.claude.json."""
    print_title("Remove Claude Security Hooks")

    claude_config = os.path.join(get_home_dir(), ".claude.json")

    if not os.path.exists(claude_config):
        print_warning("No Claude config found at ~/.claude.json")
        return True

    if dry_run:
        print(f"\n{colors.HINT}DRY RUN MODE - Would perform these actions:{colors.END}")
        print(f"  1. Backup: {claude_config} → {claude_config}.backup-before-removal")
        print(f"  2. Remove security hooks from: {claude_config}")
        print(f"\n{colors.HINT}Run without --dry-run to apply changes{colors.END}")
        return True

    # Backup
    backup = os.path.dirname(claude_config) + "/.claude.json.backup-before-removal"
    shutil.copy(claude_config, backup)
    print_hint(f"Backed up config to: {backup}")

    # Load config
    with open(claude_config, "r", encoding="utf-8") as f:
        config = json.load(f)

    # Remove security hooks
    if "hooks" not in config or "PreToolUse" not in config["hooks"]:
        print_hint("No hooks found in config")
        return True

    original_count = len(config["hooks"]["PreToolUse"])

    # Filter out security hooks
    config["hooks"]["PreToolUse"] = [
        hook_entry
        for hook_entry in config["hooks"]["PreToolUse"]
        if not any(
            "security-read-blocker.py" in str(h.get("command", ""))
            for h in hook_entry.get("hooks", [])
        )
    ]

    removed_count = original_count - len(config["hooks"]["PreToolUse"])

    if removed_count > 0:
        # Clean up empty arrays
        if len(config["hooks"]["PreToolUse"]) == 0:
            del config["hooks"]["PreToolUse"]

        if len(config["hooks"]) == 0:
            del config["hooks"]

        # Write back atomically
        temp_file = claude_config + ".tmp"
        with open(temp_file, "w", encoding="utf-8", newline="\n") as f:
            json.dump(config, f, indent=2)

        os.replace(temp_file, claude_config)

        print(f"✓ Removed {removed_count} security hook(s)")
        print_hint("Restart Claude Code for changes to take effect")
    else:
        print_hint("No security hooks found to remove")

    return True


def show_claude_hooks():
    """Show all hooks in ~/.claude.json with source identification."""
    print_title("Current Claude Hooks")

    claude_config = os.path.join(get_home_dir(), ".claude.json")

    if not os.path.exists(claude_config):
        print_warning("No Claude config found at ~/.claude.json")
        return True

    with open(claude_config, "r", encoding="utf-8") as f:
        config = json.load(f)

    if "hooks" not in config or not config["hooks"]:
        print_hint("No hooks configured")
        return True

    print(f"Hooks in {claude_config}:")
    print("=" * 60)

    for event_name, hook_entries in config["hooks"].items():
        print(f"\n{colors.HEADER}{event_name}:{colors.END}")

        for i, entry in enumerate(hook_entries):
            matcher = entry.get("matcher", "N/A")
            print(f"  [{i+1}] Matcher: {colors.OK}{matcher}{colors.END}")

            for j, hook in enumerate(entry.get("hooks", [])):
                command = hook.get("command", "")
                timeout = hook.get("timeout", 60)
                hook_type = hook.get("type", "command")

                # Identify source
                source = "Unknown"
                if "security-read-blocker.py" in command:
                    source = f"{colors.WARNING}DOTFILES (security){colors.END}"
                elif ".dotfiles-claude-hooks" in command:
                    source = f"{colors.WARNING}DOTFILES{colors.END}"

                print(f"      Hook {j+1}:")
                print(f"        Type:    {hook_type}")
                print(f"        Command: {command}")
                print(f"        Timeout: {timeout}s")
                print(f"        Source:  {source}")

    print("\n" + "=" * 60)
    return True


# ============================================================================
# Firefox Claude Settings (Project-local)
# ============================================================================

FIREFOX_CLAUDE_OVERLAY = os.path.join(BASE_DIR, "mozilla", "firefox", "dot.claude")
MEDIA_SKILLS_DIR = os.path.join(BASE_DIR, "mozilla", "firefox", "media-skills")
MEDIA_SKILLS_EXCLUDE = {"Template", "shared", ".git", ".github", "LICENSE", "README.md"}
ALWU_CLAUDE_SKILLS_DIR = os.path.join(
    BASE_DIR, "mozilla", "firefox", "alwu-claude-skills"
)
ALWU_CLAUDE_SKILLS_EXCLUDE = {".git", ".github", ".githooks", "CLAUDE.md", "README.md"}
# Rename skills during install: {"original-name": "installed-name"}
ALWU_CLAUDE_SKILLS_RENAME = {
    "triage": "av-weekly-triage",
    "sec-approval": "sec-approval-draft",
}
# Same shape as the alwu map. media-skills sit at lower priority than personal
# skills, so when a media-skill's SKILL.md `name:` collides with a personal
# skill's `name:` field the media-skill silently loses. The rename
# materializes a copy with the SKILL.md `name:` rewritten so both coexist.
# Self-mapping (key == value) is the common case here: only the SKILL.md
# `name:` needs rewriting; the install directory keeps its source name.
MEDIA_SKILLS_RENAME = {
    # SKILL.md `name: triage` collides with the personal triage skill.
    "media-bug-triage-v2": "media-bug-triage-v2",
}


def get_user_input(prompt, default=""):
    """Get text input from user with optional default."""
    if DRY_RUN:
        return default
    if not is_interactive():
        return default
    try:
        result = input(prompt).strip()
        return result if result else default
    except (EOFError, KeyboardInterrupt):
        print()
        return default


def _is_our_source(link_target):
    """Does this symlink target belong to something setup.py installs?"""
    markers = (
        FIREFOX_CLAUDE_OVERLAY,
        ALWU_CLAUDE_SKILLS_DIR,
        MEDIA_SKILLS_DIR,
        ".dotfiles",
    )
    return any(m in link_target for m in markers)


def _symlink_target_is_empty(path):
    """True when the resolved target of ``path`` exists but has no content."""
    if not os.path.exists(path):
        return False
    try:
        if os.path.isdir(path):
            return not os.listdir(path)
        return os.path.getsize(path) == 0
    except OSError:
        return False


def _rewrite_skill_name(content, new_name):
    """Rewrite the YAML frontmatter ``name:`` field in SKILL.md content.

    Claude Code identifies a skill by the ``name:`` field, not the directory
    name — so renaming the install directory alone is not enough to avoid a
    collision with another skill that declares the same name. This rewrites
    the frontmatter so the rename actually takes effect.

    Returns the original content unchanged if there is no frontmatter to edit.
    """
    if not content.startswith("---\n"):
        return content
    end = content.find("\n---\n", 4)
    if end == -1:
        return content
    frontmatter = content[4:end]
    body = content[end + 5 :]
    lines = frontmatter.splitlines()
    rewritten = False
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith("name:"):
            indent = line[: len(line) - len(stripped)]
            lines[i] = f"{indent}name: {new_name}"
            rewritten = True
            break
    if not rewritten:
        lines.insert(0, f"name: {new_name}")
    return "---\n" + "\n".join(lines) + "\n---\n" + body


def _materialize_renamed_skill(src_dir, dst_dir, install_name):
    """Create ``dst_dir`` for a renamed skill.

    ``SKILL.md`` is materialized as a real file with its ``name:`` field
    rewritten to ``install_name``; all other entries are symlinked from
    ``src_dir``. A pure symlink won't work because Claude reads the skill
    name from the file's frontmatter, not the directory it lives in.
    """
    os.makedirs(dst_dir)
    for entry in sorted(os.listdir(src_dir)):
        src_entry = os.path.join(src_dir, entry)
        dst_entry = os.path.join(dst_dir, entry)
        if (
            entry == "SKILL.md"
            and os.path.isfile(src_entry)
            and not os.path.islink(src_entry)
        ):
            with open(src_entry, encoding="utf-8") as f:
                content = f.read()
            with open(dst_entry, "w", encoding="utf-8") as f:
                f.write(_rewrite_skill_name(content, install_name))
        else:
            os.symlink(src_entry, dst_entry)


def _is_materialized_skill(dst_dir, install_name):
    """True if ``dst_dir`` looks like a setup.py-installed renamed skill.

    Signature: directory name is one of the rename targets (alwu or
    media-skills), contains a SKILL.md regular file, and is itself a real
    directory (not a symlink).
    """
    rename_targets = set(ALWU_CLAUDE_SKILLS_RENAME.values()) | set(
        MEDIA_SKILLS_RENAME.values()
    )
    if install_name not in rename_targets:
        return False
    if not os.path.isdir(dst_dir) or os.path.islink(dst_dir):
        return False
    skill_md = os.path.join(dst_dir, "SKILL.md")
    if not (os.path.isfile(skill_md) and not os.path.islink(skill_md)):
        return False
    return True


def ensure_target_core_symlinks(target_dir, dry_run=False):
    """Ensure ``core.symlinks=true`` in the target git repo.

    Git for Windows ships with system-level ``core.symlinks=false``. When a
    branch tracks symlink-typed entries (mode 120000) — e.g. a private
    ``claude-settings`` branch with the installed ``.claude/skills/*`` symlinks
    committed — a fresh worktree of that branch checks them out as plain text
    files containing the link target string, not as actual symlinks. Claude
    Code then can't follow them and the skills silently disappear in every
    worktree except the one ``setup.py`` ran in.

    Setting ``core.symlinks=true`` in the repo's local config (shared across
    every worktree of the repo, both primary and linked) prevents that. The
    flag changes how *future* checkouts materialize symlink blobs; existing
    pseudo-symlink files in already-checked-out worktrees still need a
    manual ``git checkout -- .claude/`` to re-materialize. No-op if the
    target isn't a git checkout or the value is already true. Local-only —
    never touches global/system git config.
    """
    # ``.git`` is a directory in the primary checkout and a file pointing
    # back to the main repo in linked worktrees (`git worktree add`). Either
    # is fine — both share the same local config we want to update.
    git_marker = os.path.join(target_dir, ".git")
    if not os.path.exists(git_marker):
        return  # Not a git checkout; nothing to configure.

    try:
        result = subprocess.run(
            ["git", "-C", target_dir, "config", "--local", "--get", "core.symlinks"],
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        print_warning(
            "git not found on PATH; skipping core.symlinks check for " f"{target_dir}"
        )
        return

    current = result.stdout.strip().lower() if result.returncode == 0 else ""
    if current == "true":
        return

    label = (
        current or "unset (falls back to system default, typically false on Windows)"
    )
    if dry_run:
        print(
            f"  Would run: git -C {target_dir} config core.symlinks true "
            f"(currently: {label})"
        )
        return

    try:
        subprocess.run(
            ["git", "-C", target_dir, "config", "core.symlinks", "true"],
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print_warning(
            f"Failed to set core.symlinks=true in {target_dir}: {e}\n"
            f"  Run manually: git -C {target_dir} config core.symlinks true"
        )
        return

    print(f"Set core.symlinks=true in {target_dir} (was {label})")
    print_hint(
        "  Without this, worktrees of this repo would check out tracked\n"
        "  symlinks (e.g. .claude/skills/*) as plain text files containing\n"
        "  the link target — Claude Code can't follow those, so skills\n"
        "  disappear in every other worktree.\n"
        "  Existing worktrees with broken pseudo-symlinks can be repaired\n"
        "  by deleting the offending files and running:\n"
        "    git -C <worktree> checkout -- .claude/"
    )


def verify_overlay_commitable(target_dir):
    """Pre-commit checks for ``_commit_overlay``.

    Returns True if the commit may proceed; False on hard blockers.

    On Windows, the commit stores mode-120000 (symlink) entries — same
    as POSIX — so the committed branch must be checkout-able from
    *every* shell on the machine, not just the (possibly elevated)
    install session. The only Windows configuration that guarantees
    this is Developer Mode enabled in the registry; we refuse the
    commit otherwise with a clear message. POSIX has no equivalent
    concept; the function is effectively a no-op there beyond the
    defensive core.symlinks re-check.
    """
    # Defensive: make sure core.symlinks is still true. The install
    # set it earlier; this catches the case where it got unset between
    # install and commit.
    ensure_target_core_symlinks(target_dir)

    if not can_create_symlinks(probe_dir=target_dir):
        print_error(
            f"Cannot create symlinks in {target_dir} right now — the\n"
            "  installed .claude/ symlinks are likely broken. Re-run\n"
            "  setup.py from a shell with symlink privilege (Developer\n"
            "  Mode on, or elevated)."
        )
        return False

    if is_windows() and not is_windows_dev_mode_enabled():
        if is_windows_elevated():
            print_error(
                "Refusing to commit: setup.py is running elevated, so\n"
                "  this process can create symlinks, but Windows Developer\n"
                "  Mode is OFF system-wide. The committed `claude-overlay`\n"
                "  would store symlink entries (mode 120000) that fail to\n"
                "  check out from non-elevated shells. Enable Developer\n"
                "  Mode (Settings -> System -> For developers -> Developer\n"
                "  Mode), restart the shell, and re-run."
            )
        else:
            print_error(
                "Refusing to commit: Windows Developer Mode is OFF\n"
                "  system-wide. The committed `claude-overlay` would store\n"
                "  symlink entries (mode 120000) that cannot be checked\n"
                "  out without symlink privilege. Enable Developer Mode\n"
                "  (Settings -> System -> For developers -> Developer\n"
                "  Mode) and re-run."
            )
        return False

    return True


POST_CHECKOUT_HOOK_MARKER_BEGIN = (
    "# === dotfiles setup.py managed post-checkout (firefox-claude) BEGIN ==="
)
POST_CHECKOUT_HOOK_MARKER_END = (
    "# === dotfiles setup.py managed post-checkout (firefox-claude) END ==="
)
POST_CHECKOUT_HOOK_BODY = """\
# Re-materialize mode-120000 entries under .claude/ that git failed to
# create as symlinks. On Windows, Git for Windows' CreateSymbolicLinkW
# intermittently returns ERROR_ACCESS_DENIED for absolute-path symlink
# blobs even when Developer Mode is on, while MSYS's `ln -s` (which
# this hook uses) succeeds in the same shell. The hook is idempotent
# and a no-op when there's nothing to repair.
[ "$3" = "1" ] || exit 0    # branch checkouts only
_count=0
while IFS= read -r line; do
    case "$line" in "120000 "*) ;; *) continue ;; esac
    blob=$(printf '%s' "$line" | awk '{print $3}')
    path=$(printf '%s' "$line" | cut -f2)
    [ -L "$path" ] && continue
    target=$(git cat-file -p "$blob" 2>/dev/null) || continue
    mkdir -p "$(dirname "$path")"
    [ -e "$path" ] && rm -rf "$path"
    if ln -s "$target" "$path" 2>/dev/null; then
        _count=$((_count + 1))
    fi
done <<EOF
$(git ls-tree -r HEAD -- .claude/ 2>/dev/null)
EOF
if [ "$_count" -gt 0 ]; then
    echo "post-checkout: re-materialized $_count .claude/ symlinks via ln -s" \\
         "(git's own symlink creation failed; this is expected on Windows" \\
         "and the working tree is now correct)."
fi
"""


def _build_post_checkout_managed_block():
    return (
        f"{POST_CHECKOUT_HOOK_MARKER_BEGIN}\n"
        f"{POST_CHECKOUT_HOOK_BODY}"
        f"{POST_CHECKOUT_HOOK_MARKER_END}\n"
    )


def install_post_checkout_hook(target_dir, dry_run=False):
    """Install a Windows-only post-checkout hook that re-materializes
    mode-120000 entries under .claude/ via ``ln -s`` after every branch
    checkout. Works around Git for Windows' CreateSymbolicLinkW
    intermittently failing with Permission denied on absolute-path
    symlink blobs (see the hook body docstring for details).

    No-op on POSIX (git checkout works correctly there) and on
    non-git directories. Idempotent: if a managed block is already
    present (matching the BEGIN/END markers), it's replaced; otherwise
    the block is appended (preserving any pre-existing hook content).
    """
    if not is_windows():
        return
    git_marker = os.path.join(target_dir, ".git")
    if not os.path.exists(git_marker):
        return

    hooks_dir = os.path.join(target_dir, ".git", "hooks")
    hook_path = os.path.join(hooks_dir, "post-checkout")
    managed_block = _build_post_checkout_managed_block()

    existing = ""
    if os.path.isfile(hook_path):
        with open(hook_path, "r", encoding="utf-8", newline="") as f:
            existing = f.read()

    begin = POST_CHECKOUT_HOOK_MARKER_BEGIN
    end = POST_CHECKOUT_HOOK_MARKER_END
    if begin in existing and end in existing:
        # Replace the existing managed block in place.
        before, _, rest = existing.partition(begin)
        _, _, after = rest.partition(end)
        # Drop the trailing newline after the END marker if any, to
        # avoid stacking newlines on repeated installs.
        after = after.lstrip("\n")
        new_content = before + managed_block + (("\n" + after) if after else "")
        action = "Updated managed post-checkout block"
    elif existing.strip():
        # Preserve user content; append our managed block at the end.
        sep = "" if existing.endswith("\n") else "\n"
        new_content = existing + sep + "\n" + managed_block
        action = "Appended managed post-checkout block"
    else:
        new_content = "#!/bin/sh\n\n" + managed_block
        action = "Installed post-checkout hook"

    if dry_run:
        print(f"  Would {action.lower()}: {hook_path}")
        return

    os.makedirs(hooks_dir, exist_ok=True)
    with open(hook_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(new_content)
    try:
        st = os.stat(hook_path)
        os.chmod(hook_path, st.st_mode | 0o755)
    except OSError:
        pass
    print(f"{action}: {hook_path}")


def ensure_submodule_populated(submodule_path, label, dry_run=False):
    """Return True if ``submodule_path`` exists and has content.

    An uninitialized git submodule looks like an empty directory: ``isdir`` is
    True but ``listdir`` is empty. In that case, attempt
    ``git submodule update --init`` so the install can proceed without the
    user noticing skills were silently skipped. On failure, warn with the
    manual command and return False so the caller treats the source as empty.
    """
    if not os.path.isdir(submodule_path):
        return False
    try:
        if os.listdir(submodule_path):
            return True
    except OSError:
        return False

    if dry_run:
        print(
            f"  Note: submodule '{label}' is uninitialized; would run "
            f"'git submodule update --init {submodule_path}' before linking."
        )
        return False

    print_warning(
        f"Submodule '{label}' is uninitialized; running "
        f"'git submodule update --init'..."
    )
    try:
        subprocess.run(
            ["git", "submodule", "update", "--init", submodule_path],
            cwd=BASE_DIR,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print_warning(
            f"Failed to initialize submodule '{label}': {e}\n"
            f"  Run manually: git submodule update --init {submodule_path}"
        )
        return False

    try:
        return bool(os.listdir(submodule_path))
    except OSError:
        return False


def cleanup_stale_skills(target_skills_dir, target_dir, dry_run=False):
    """
    Remove stale skill entries that ``setup.py`` itself installed previously.

    Only these are removed:
      * broken symlinks whose target path is under one of our managed
        sources (dotfiles overlay, alwu-claude-skills, media-skills). Broken
        symlinks that point elsewhere are reported but preserved.
      * empty directories whose ``.claude/skills/<name>/`` entry is tracked
        in our managed section of the target's .gitignore (i.e. we created
        the placeholder).

    Everything else — self-contained skill directories the user populated,
    symlinks to external sources, broken symlinks to paths outside our
    managed tree — is left alone and reported so the user knows what's
    there and where it came from.

    The matching ``.claude/skills/<name>/`` entry in .gitignore is removed
    for anything we do clean up.
    """
    if not os.path.isdir(target_skills_dir):
        return []

    managed_entries = _read_our_entries(os.path.join(target_dir, ".gitignore"))

    stale_names = []
    external = []  # (label, path) tuples — informational only
    for name in sorted(os.listdir(target_skills_dir)):
        path = os.path.join(target_skills_dir, name)
        entry = f".claude/skills/{name}/"

        if os.path.islink(path):
            link_target = os.readlink(path)
            broken = not os.path.exists(path)
            ours = _is_our_source(link_target)
            if broken and ours:
                if dry_run:
                    print(f"  Would remove broken symlink: {path}")
                else:
                    os.unlink(path)
                    print(f"Removed broken symlink: {path}")
                stale_names.append(name)
            elif broken:
                external.append((f"broken symlink -> {link_target}", path))
            elif not ours:
                empty_note = (
                    " (target is empty)" if _symlink_target_is_empty(path) else ""
                )
                external.append(
                    (f"external symlink -> {link_target}{empty_note}", path)
                )
            elif _symlink_target_is_empty(path):
                # Managed symlink with an empty source — flag but don't touch;
                # the source may be a submodule that isn't initialised yet.
                external.append((f"managed symlink -> {link_target} (empty)", path))
            # Live, populated symlinks into our managed sources: nothing to do.
        elif os.path.isdir(path):
            if not os.listdir(path) and entry in managed_entries:
                if dry_run:
                    print(f"  Would remove empty directory: {path}")
                else:
                    os.rmdir(path)
                    print(f"Removed empty directory: {path}")
                stale_names.append(name)
            elif _is_materialized_skill(path, name):
                # Managed: a renamed skill (alwu or media) materialized at
                # install time.
                pass
            else:
                # Self-contained skill (populated, or empty but not ours).
                external.append(("self-contained skill", path))

    if external:
        print_hint(
            "Skills not managed by setup.py (left as-is — install them elsewhere):"
        )
        for label, path in external:
            print_hint(f"  {path}  [{label}]")

    if stale_names:
        entries = [f".claude/skills/{n}/" for n in stale_names]
        remove_from_gitignore(target_dir, entries, dry_run=dry_run)

    return stale_names


def _commit_overlay(target_dir, include_claude_local, new_branch=None):
    """Stage and commit installed overlay in ``target_dir``.

    Uses ``git add -f`` to bypass our managed .gitignore entries (the
    symlinks are gitignored on purpose, but to share them via worktrees
    they need to be tracked on whatever branch the worktrees are based on).

    If ``new_branch`` is a non-empty string, ``git checkout -b <new_branch>``
    is run first so the commit lands on a fresh branch off the current
    HEAD; otherwise the commit lands on the current branch.

    Stages ``.claude/`` + ``.gitignore`` unconditionally and
    ``CLAUDE.local.md`` only when ``include_claude_local`` is True (the
    caller checks for its existence). Honors pre-commit hooks — on hook
    failure, prints stderr and returns False so the user can resolve.

    Returns True on a successful commit (or no-op when nothing changed),
    False on any error.
    """
    git_marker = os.path.join(target_dir, ".git")
    if not os.path.exists(git_marker):
        print_hint(f"  {target_dir} is not a git checkout; skipping commit")
        return False

    def _git(*args):
        return subprocess.run(["git", "-C", target_dir, *args], capture_output=True)

    for key in ("user.email", "user.name"):
        result = _git("config", "--get", key)
        if result.returncode != 0 or not result.stdout.strip():
            print_warning(
                f"git {key} not configured in {target_dir}; skipping commit. "
                f"Set it and re-run --install-firefox-claude."
            )
            return False

    if not verify_overlay_commitable(target_dir):
        return False

    if new_branch:
        exists = (
            _git("rev-parse", "--verify", f"refs/heads/{new_branch}").returncode == 0
        )
        if exists:
            if not get_user_confirmation(
                f"Branch '{new_branch}' already exists. "
                "Replace it with the new commit? [y/N]: ",
                default_non_interactive=False,
            ):
                print_hint("  Cancelled — commit not created.")
                return False
            # -B re-creates / resets the branch ref; safe here because
            # we're about to switch the primary worktree to it.
            checkout = _git("checkout", "-B", new_branch)
            action = "Reset to new commit on"
        else:
            checkout = _git("checkout", "-b", new_branch)
            action = "Switched to new branch"
        if checkout.returncode != 0:
            print_warning(
                f"git checkout {'-B' if exists else '-b'} '{new_branch}' failed: "
                f"{checkout.stderr.decode().strip()}"
            )
            return False
        print(f"{action} '{new_branch}'")

    paths = [".claude/", ".gitignore"]
    if include_claude_local:
        paths.append("CLAUDE.local.md")

    add = _git("add", "-f", *paths)
    if add.returncode != 0:
        print_warning(f"git add failed: {add.stderr.decode().strip()}")
        return False

    diff = _git("diff", "--cached", "--quiet")
    if diff.returncode == 0:
        print_hint("  Nothing to commit; overlay already tracked on this branch")
        return True

    commit = _git("commit", "-m", "Install Claude overlay")
    if commit.returncode != 0:
        stderr = commit.stderr.decode().strip()
        stdout = commit.stdout.decode().strip()
        msg = stderr or stdout or "(no output)"
        print_warning(f"git commit failed (pre-commit hook?): {msg}")
        return False

    rev = _git("rev-parse", "HEAD")
    sha = rev.stdout.decode().strip()[:12] if rev.returncode == 0 else "?"
    branch_result = _git("rev-parse", "--abbrev-ref", "HEAD")
    branch_name = (
        branch_result.stdout.decode().strip()
        if branch_result.returncode == 0
        else "HEAD"
    )
    print(f"Committed overlay on '{branch_name}' ({sha})")
    return True


def install_firefox_claude(target_dir=None, dry_run=False):
    """
    Install Firefox-specific Claude settings (hooks, skills) to a target project.
    Uses symlinks for easy management across multiple repos.

    Leaves the install (symlinks + .gitignore update) as uncommitted
    changes in the target. To make worktrees inherit the overlay, you
    can commit the symlinks to a side branch yourself and base worktrees
    on it — git materializes the tracked ``120000`` entries as real
    symlinks because ``core.symlinks=true`` is set by this install.
    """
    print_title("Install Firefox Claude Settings")

    if not dry_run and not ensure_symlink_capability():
        print_error(
            "Symlink creation unavailable; cannot install Firefox Claude settings"
        )
        return False

    # Verify overlay exists
    if not os.path.isdir(FIREFOX_CLAUDE_OVERLAY):
        print_error(f"Firefox Claude overlay not found: {FIREFOX_CLAUDE_OVERLAY}")
        return False

    # Ask for target directory if not provided
    if not target_dir:
        target_dir = get_user_input("Enter Firefox project path: ")
        if not target_dir:
            print_error("No target directory provided.")
            return False

    # Expand and validate target
    target_dir = os.path.expanduser(target_dir)
    if not os.path.isdir(target_dir):
        print_error(f"Target directory does not exist: {target_dir}")
        return False

    # Check for mach to confirm it's a Firefox repo
    mach_path = os.path.join(target_dir, "mach")
    if not os.path.exists(mach_path):
        print_warning(f'No "mach" found in {target_dir}')
        if not get_user_confirmation("Continue anyway? [y/N]: "):
            print("Aborted.")
            return False

    # Make sure git checks out tracked symlinks as real symlinks in this repo
    # (and in any worktrees of it). Skipped silently if already true.
    ensure_target_core_symlinks(target_dir, dry_run=dry_run)

    # Windows-only: install the post-checkout hook that re-materializes
    # mode-120000 entries under .claude/ via `ln -s` after every branch
    # checkout. Compensates for Git for Windows' CreateSymbolicLinkW
    # intermittently failing on absolute-path symlink blobs.
    install_post_checkout_hook(target_dir, dry_run=dry_run)

    # Windows-only: detect the "stuck" state where the user is currently
    # on `claude-overlay` but `.claude/` entries are deleted in the
    # working tree (the original symptom of `git checkout claude-overlay`
    # failing to materialize symlinks). Auto-switch to master/main so
    # the install lands on a clean base.
    if is_windows() and not dry_run:
        head_check = subprocess.run(
            ["git", "-C", target_dir, "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
        )
        if head_check.stdout.strip() == "claude-overlay":
            status = subprocess.run(
                [
                    "git",
                    "-C",
                    target_dir,
                    "status",
                    "--porcelain",
                    "--",
                    ".claude/",
                ],
                capture_output=True,
                text=True,
            )
            stuck = any(
                line.startswith(" D ") or line.startswith("D  ")
                for line in status.stdout.splitlines()
            )
            if stuck:
                print("")
                print_warning(
                    "Detected stuck claude-overlay state (tracked .claude/\n"
                    "  entries deleted in working tree). Switching to a base\n"
                    "  branch before installing."
                )
                for candidate in ("master", "main"):
                    verify = subprocess.run(
                        [
                            "git",
                            "-C",
                            target_dir,
                            "rev-parse",
                            "--verify",
                            candidate,
                        ],
                        capture_output=True,
                    )
                    if verify.returncode == 0:
                        co = subprocess.run(
                            ["git", "-C", target_dir, "checkout", candidate],
                            capture_output=True,
                            text=True,
                        )
                        if co.returncode == 0:
                            print(
                                f"Switched to '{candidate}' "
                                "(reproduce claude-overlay via the commit prompt)"
                            )
                            break
                else:
                    print_warning(
                        "Cannot find master or main to switch to. Switch\n"
                        "  manually and re-run setup.py."
                    )
                    return False

    target_claude_dir = os.path.join(target_dir, ".claude")
    target_hooks_dir = os.path.join(target_claude_dir, "hooks")
    target_skills_dir = os.path.join(target_claude_dir, "skills")
    target_agents_dir = os.path.join(target_claude_dir, "agents")
    target_settings = os.path.join(target_claude_dir, "settings.local.json")

    # Check for existing settings
    existing_settings = os.path.exists(target_settings)
    merge_mode = None

    if existing_settings and not dry_run:
        print_warning(f"Existing settings found: {target_settings}")
        print("Options:")
        print("  [m] Merge - Keep existing settings and add new hooks/skills")
        print("  [o] Override - Replace with dotfiles settings (creates symlink)")
        print("  [c] Cancel - Abort installation")
        choice = get_user_input("Choose [m/o/c]: ", "c").lower()
        if choice == "c":
            print("Aborted.")
            return False
        merge_mode = choice == "m"
        if merge_mode:
            print_warning("Merge creates a local file, not a symlink.")
            print_warning(
                "Future updates to dotfiles settings will NOT auto-propagate."
            )
            print_warning("To get updates, re-run with override mode or manually edit.")

    if dry_run:
        print(f"\n{colors.HINT}DRY RUN MODE - Would perform these actions:{colors.END}")
        print(f"  Target: {target_dir}")
        print(f"  1. Create directory: {target_hooks_dir}")
        print(f"  2. Create directory: {target_skills_dir}")
        print(f"  3. Create directory: {target_agents_dir}")

        # Track items to add to .gitignore (only our additions, not entire .claude/)
        gitignore_entries = []

        # List hooks to symlink
        step = 4
        source_hooks = os.path.join(FIREFOX_CLAUDE_OVERLAY, "hooks")
        if os.path.isdir(source_hooks):
            for hook in os.listdir(source_hooks):
                src = os.path.join(source_hooks, hook)
                dst = os.path.join(target_hooks_dir, hook)
                print(f"  {step}. Symlink: {dst} -> {src}")
                gitignore_entries.append(f".claude/hooks/{hook}")
                step += 1

        # List agents to symlink
        source_agents = os.path.join(FIREFOX_CLAUDE_OVERLAY, "agents")
        if os.path.isdir(source_agents):
            for agent in os.listdir(source_agents):
                src = os.path.join(source_agents, agent)
                dst = os.path.join(target_agents_dir, agent)
                print(f"  {step}. Symlink: {dst} -> {src}")
                gitignore_entries.append(f".claude/agents/{agent}")
                step += 1

        # List skills to symlink (personal)
        source_skills = os.path.join(FIREFOX_CLAUDE_OVERLAY, "skills")
        personal_skill_names = set()
        if os.path.isdir(source_skills):
            for skill in os.listdir(source_skills):
                src = os.path.join(source_skills, skill)
                dst = os.path.join(target_skills_dir, skill)
                print(f"  {step}. Symlink: {dst} -> {src}")
                gitignore_entries.append(f".claude/skills/{skill}/")
                personal_skill_names.add(skill)
                step += 1

        # Show renamed alwu-claude-skills cleanup — only flag symlinks that
        # actually point at a alwu-claude-skills source, to avoid false positives
        # for names that are re-used by personal or media skills.
        for old_name, new_name in ALWU_CLAUDE_SKILLS_RENAME.items():
            old_path = os.path.join(target_skills_dir, old_name)
            if os.path.islink(old_path) and ALWU_CLAUDE_SKILLS_DIR in os.readlink(
                old_path
            ):
                print(
                    f"  {step}. Remove stale (alwu-claude-skills): {old_name} (renamed to {new_name})"
                )
                remove_from_gitignore(
                    target_dir, [f".claude/skills/{old_name}/"], dry_run=True
                )
                step += 1

        # List alwu-claude-skills to symlink (personal, higher priority than media-skills)
        alwu_claude_skill_names = set()
        if ensure_submodule_populated(
            ALWU_CLAUDE_SKILLS_DIR, "alwu-claude-skills", dry_run=True
        ):
            for skill in sorted(os.listdir(ALWU_CLAUDE_SKILLS_DIR)):
                if skill in ALWU_CLAUDE_SKILLS_EXCLUDE:
                    continue
                if not os.path.isdir(os.path.join(ALWU_CLAUDE_SKILLS_DIR, skill)):
                    continue
                install_name = ALWU_CLAUDE_SKILLS_RENAME.get(skill, skill)
                if install_name in personal_skill_names:
                    print(f"  {step}. SKIP (conflict with personal): {install_name}")
                    step += 1
                    continue
                src = os.path.join(ALWU_CLAUDE_SKILLS_DIR, skill)
                dst = os.path.join(target_skills_dir, install_name)
                if skill != install_name:
                    print(
                        f"  {step}. Materialize (alwu-claude-skills): {dst} from "
                        f"{src} [{skill} -> {install_name}, SKILL.md `name:` rewritten]"
                    )
                else:
                    print(f"  {step}. Symlink (alwu-claude-skills): {dst} -> {src}")
                gitignore_entries.append(f".claude/skills/{install_name}/")
                alwu_claude_skill_names.add(install_name)
                step += 1

        # List media-skills to symlink (team-wide)
        if ensure_submodule_populated(MEDIA_SKILLS_DIR, "media-skills", dry_run=True):
            for skill in sorted(os.listdir(MEDIA_SKILLS_DIR)):
                if skill in MEDIA_SKILLS_EXCLUDE:
                    continue
                if not os.path.isdir(os.path.join(MEDIA_SKILLS_DIR, skill)):
                    continue
                install_name = MEDIA_SKILLS_RENAME.get(skill, skill)
                if (
                    install_name in personal_skill_names
                    or install_name in alwu_claude_skill_names
                ):
                    print(
                        f"  {step}. SKIP (conflict with personal/alwu-claude-skills): {install_name}"
                    )
                    step += 1
                    continue
                src = os.path.join(MEDIA_SKILLS_DIR, skill)
                dst = os.path.join(target_skills_dir, install_name)
                if skill in MEDIA_SKILLS_RENAME:
                    print(
                        f"  {step}. Materialize (media-skills): {dst} from "
                        f"{src} [{skill} -> {install_name}, SKILL.md `name:` rewritten]"
                    )
                else:
                    print(f"  {step}. Symlink (media-skills): {dst} -> {src}")
                gitignore_entries.append(f".claude/skills/{install_name}/")
                step += 1

        # Auto-clean stale skill symlinks / empty dirs
        if os.path.isdir(target_skills_dir):
            print(f"  {step}. Check for stale skills to clean up:")
            cleanup_stale_skills(target_skills_dir, target_dir, dry_run=True)
            step += 1

        # Settings
        src_settings = os.path.join(FIREFOX_CLAUDE_OVERLAY, "settings.local.json")
        if existing_settings:
            print(f"  {step}. Existing settings found: {target_settings}")
            print(
                "       (You will be prompted to merge or override when running without --dry-run)"
            )
        else:
            print(f"  {step}. Symlink: {target_settings} -> {src_settings}")
            gitignore_entries.append(".claude/settings.local.json")
        step += 1

        # .gitignore update for added items only
        if gitignore_entries:
            stale_hook_entries = [
                entry + "/"
                for entry in gitignore_entries
                if entry.startswith(".claude/hooks/")
            ]
            if stale_hook_entries:
                print(
                    f"  {step}. Drop stale trailing-slash hook entries from .gitignore:"
                )
                remove_from_gitignore(target_dir, stale_hook_entries, dry_run=True)
                step += 1
            print(f"  {step}. Check/update .gitignore:")
            add_to_gitignore(target_dir, gitignore_entries, dry_run=True)
            step += 1

        print(f"\n{colors.HINT}Run without --dry-run to apply changes{colors.END}")
        return True

    # Create directories
    os.makedirs(target_hooks_dir, exist_ok=True)
    os.makedirs(target_skills_dir, exist_ok=True)
    os.makedirs(target_agents_dir, exist_ok=True)
    print(f"Created: {target_hooks_dir}")
    print(f"Created: {target_skills_dir}")
    print(f"Created: {target_agents_dir}")

    # Track items to add to .gitignore (only our additions, not entire .claude/)
    gitignore_entries = []

    # Symlink hooks
    source_hooks = os.path.join(FIREFOX_CLAUDE_OVERLAY, "hooks")
    if os.path.isdir(source_hooks):
        for hook in os.listdir(source_hooks):
            src = os.path.join(source_hooks, hook)
            dst = os.path.join(target_hooks_dir, hook)

            if os.path.islink(dst):
                os.unlink(dst)
            elif os.path.exists(dst):
                print_warning(f"Skipping existing file: {dst}")
                continue

            os.symlink(src, dst)
            print(f"Linked: {hook}")
            gitignore_entries.append(f".claude/hooks/{hook}")

    # Symlink agents
    source_agents = os.path.join(FIREFOX_CLAUDE_OVERLAY, "agents")
    if os.path.isdir(source_agents):
        for agent in os.listdir(source_agents):
            src = os.path.join(source_agents, agent)
            dst = os.path.join(target_agents_dir, agent)

            if os.path.islink(dst):
                os.unlink(dst)
            elif os.path.exists(dst):
                print_warning(f"Skipping existing file: {dst}")
                continue

            os.symlink(src, dst)
            print(f"Linked: {agent}")
            gitignore_entries.append(f".claude/agents/{agent}")

    # Symlink skills (personal)
    source_skills = os.path.join(FIREFOX_CLAUDE_OVERLAY, "skills")
    personal_skill_names = set()
    if os.path.isdir(source_skills):
        for skill in os.listdir(source_skills):
            src = os.path.join(source_skills, skill)
            dst = os.path.join(target_skills_dir, skill)

            if os.path.islink(dst):
                os.unlink(dst)
            elif os.path.exists(dst):
                print_warning(f"Skipping existing directory: {dst}")
                continue

            os.symlink(src, dst)
            print(f"Linked: {skill}")
            gitignore_entries.append(f".claude/skills/{skill}/")
            personal_skill_names.add(skill)

    # Clean up stale symlinks and gitignore entries from renamed alwu-claude-skills
    stale_gitignore = []
    for old_name in ALWU_CLAUDE_SKILLS_RENAME:
        old_path = os.path.join(target_skills_dir, old_name)
        if os.path.islink(old_path):
            link_target = os.readlink(old_path)
            if ALWU_CLAUDE_SKILLS_DIR in link_target:
                os.unlink(old_path)
                stale_gitignore.append(f".claude/skills/{old_name}/")
                print(f"Removed stale (alwu-claude-skills): {old_name}")
    if stale_gitignore:
        remove_from_gitignore(target_dir, stale_gitignore)

    # Symlink alwu-claude-skills (personal, higher priority than media-skills)
    alwu_claude_skill_names = set()
    if ensure_submodule_populated(ALWU_CLAUDE_SKILLS_DIR, "alwu-claude-skills"):
        for skill in sorted(os.listdir(ALWU_CLAUDE_SKILLS_DIR)):
            if skill in ALWU_CLAUDE_SKILLS_EXCLUDE:
                continue
            src = os.path.join(ALWU_CLAUDE_SKILLS_DIR, skill)
            if not os.path.isdir(src):
                continue
            install_name = ALWU_CLAUDE_SKILLS_RENAME.get(skill, skill)
            if install_name in personal_skill_names:
                print_warning(
                    f"Skipping alwu-claude-skill '{install_name}' (conflicts with personal skill)"
                )
                continue
            dst = os.path.join(target_skills_dir, install_name)
            needs_materialize = skill != install_name

            if os.path.islink(dst):
                os.unlink(dst)
            elif os.path.isdir(dst):
                if needs_materialize and _is_materialized_skill(dst, install_name):
                    shutil.rmtree(dst)
                else:
                    print_warning(f"Skipping existing directory: {dst}")
                    continue
            elif os.path.exists(dst):
                print_warning(f"Skipping existing file: {dst}")
                continue

            if needs_materialize:
                _materialize_renamed_skill(src, dst, install_name)
                print(
                    f"Installed (alwu-claude-skills): {skill} as {install_name} "
                    f"(SKILL.md `name:` rewritten)"
                )
            else:
                os.symlink(src, dst)
                print(f"Linked (alwu-claude-skills): {skill}")
            gitignore_entries.append(f".claude/skills/{install_name}/")
            alwu_claude_skill_names.add(install_name)

    # Symlink media-skills (team-wide)
    if ensure_submodule_populated(MEDIA_SKILLS_DIR, "media-skills"):
        for skill in sorted(os.listdir(MEDIA_SKILLS_DIR)):
            if skill in MEDIA_SKILLS_EXCLUDE:
                continue
            src = os.path.join(MEDIA_SKILLS_DIR, skill)
            if not os.path.isdir(src):
                continue
            install_name = MEDIA_SKILLS_RENAME.get(skill, skill)
            if (
                install_name in personal_skill_names
                or install_name in alwu_claude_skill_names
            ):
                print_warning(
                    f"Skipping media-skill '{install_name}' (conflicts with personal/alwu-claude-skill)"
                )
                continue
            dst = os.path.join(target_skills_dir, install_name)
            # MEDIA_SKILLS_RENAME entries always need materialization: even when
            # the install dir name is unchanged, the SKILL.md `name:` field is
            # rewritten so it stops colliding with the personal skill.
            needs_materialize = skill in MEDIA_SKILLS_RENAME

            if os.path.islink(dst):
                os.unlink(dst)
            elif os.path.isdir(dst):
                if needs_materialize and _is_materialized_skill(dst, install_name):
                    shutil.rmtree(dst)
                else:
                    print_warning(f"Skipping existing directory: {dst}")
                    continue
            elif os.path.exists(dst):
                print_warning(f"Skipping existing file: {dst}")
                continue

            if needs_materialize:
                _materialize_renamed_skill(src, dst, install_name)
                print(
                    f"Installed (media-skills): {skill} as {install_name} "
                    f"(SKILL.md `name:` rewritten)"
                )
            else:
                os.symlink(src, dst)
                print(f"Linked (media-skills): {skill}")
            gitignore_entries.append(f".claude/skills/{install_name}/")

    # Auto-clean stale skills (broken symlinks, empty dirs) left over from
    # previous installs — e.g. skills that were renamed, deleted, or moved
    # between source buckets.
    cleanup_stale_skills(target_skills_dir, target_dir)

    # Handle settings.local.json
    src_settings = os.path.join(FIREFOX_CLAUDE_OVERLAY, "settings.local.json")

    if merge_mode and existing_settings:
        # Merge settings
        print("Merging settings...")
        existing = load_jsonc(target_settings)
        new_settings = load_jsonc(src_settings)

        # Merge permissions
        if "permissions" in new_settings:
            if "permissions" not in existing:
                existing["permissions"] = {}
            if "allow" in new_settings["permissions"]:
                existing_allow = set(existing.get("permissions", {}).get("allow", []))
                new_allow = set(new_settings["permissions"]["allow"])
                existing["permissions"]["allow"] = sorted(existing_allow | new_allow)

        # Merge hooks
        if "hooks" in new_settings:
            if "hooks" not in existing:
                existing["hooks"] = {}
            for event, hooks in new_settings["hooks"].items():
                if event not in existing["hooks"]:
                    existing["hooks"][event] = []
                for new_entry in hooks:
                    new_matcher = new_entry.get("matcher", "")
                    # Find existing entry with the same matcher
                    matched_entry = None
                    for existing_entry in existing["hooks"][event]:
                        if existing_entry.get("matcher", "") == new_matcher:
                            matched_entry = existing_entry
                            break
                    if matched_entry is not None:
                        # Merge individual hooks into the existing entry
                        existing_cmds = {
                            h.get("command", "") for h in matched_entry.get("hooks", [])
                        }
                        for hook in new_entry.get("hooks", []):
                            if hook.get("command", "") not in existing_cmds:
                                matched_entry["hooks"].append(hook)
                    else:
                        existing["hooks"][event].append(new_entry)

        # Merge MCP servers
        for key in ["enableAllProjectMcpServers", "enabledMcpjsonServers"]:
            if key in new_settings:
                existing[key] = new_settings[key]

        # Write merged settings
        with open(target_settings, "w", encoding="utf-8", newline="\n") as f:
            json.dump(existing, f, indent=2)
        print(f"Merged settings: {target_settings}")

    else:
        # Symlink settings
        if os.path.islink(target_settings):
            os.unlink(target_settings)
        elif os.path.exists(target_settings):
            backup = target_settings + ".backup"
            shutil.move(target_settings, backup)
            print_hint(f"Backed up existing settings to: {backup}")

        os.symlink(src_settings, target_settings)
        print("Linked: settings.local.json")
        gitignore_entries.append(".claude/settings.local.json")

    # Migrate older managed entries: hooks were briefly added with a
    # trailing slash (directory-only pattern that doesn't match symlinks)
    # — that left the hook symlinks unignored on Mozilla branches. We're
    # back to the conventional no-slash shape, which correctly gitignores
    # the symlinks. Drop any leftover trailing-slash variants so the new
    # no-slash entries take effect.
    stale_hook_entries = [
        entry + "/" for entry in gitignore_entries if entry.startswith(".claude/hooks/")
    ]
    if stale_hook_entries:
        remove_from_gitignore(target_dir, stale_hook_entries)

    # Add our items to .gitignore (only what we added, not entire .claude/)
    if gitignore_entries:
        add_to_gitignore(target_dir, gitignore_entries)

    # Offer to set up tech-docs index reference in CLAUDE.local.md
    print("")
    target_claude_local = os.path.join(target_dir, "CLAUDE.local.md")
    print("Tech-docs index file for Claude to consult on demand (e.g. INDEX.md).")
    print("Press Enter to skip.")
    index_path = get_user_input("Path to index file: ", "")
    index_path = index_path.strip()

    if index_path:
        index_path = os.path.expanduser(index_path)
        if not os.path.isfile(index_path):
            print_warning(f"File not found: {index_path}")
            print_hint("You can set this up manually later.")
        else:
            # Check if CLAUDE.local.md already references this file
            existing_content = ""
            if os.path.isfile(target_claude_local):
                with open(target_claude_local, "r") as f:
                    existing_content = f.read()

            if index_path in existing_content:
                print_hint("CLAUDE.local.md already references this index file.")
            else:
                ref_line = (
                    "For technical reference documents, read the index at "
                    f"{index_path} and then read the relevant document as needed."
                )
                with open(target_claude_local, "a") as f:
                    f.write(ref_line + "\n")
                print(f"Updated: {target_claude_local}")

    # Offer to commit the install outputs so worktrees created from
    # this commit (or branches off it) inherit the overlay automatically.
    # The symlinks and (when present) CLAUDE.local.md are gitignored, so
    # `git add -f` is required — this prompt is the one place where
    # setup.py asks for it.
    print("")
    has_claude_local = os.path.isfile(target_claude_local)
    committed = False
    commit_prompt = (
        "Commit the installed overlay now?\n"
        "  - Stages with: git add -f .claude/ .gitignore"
        + (" CLAUDE.local.md" if has_claude_local else "")
        + "\n"
        "  - Commits as:  git commit -m 'Install Claude overlay'\n"
        "  - Worktrees created from this commit will inherit the overlay.\n"
        "Commit now? [y/N]: "
    )
    if get_user_confirmation(commit_prompt, default_non_interactive=False):
        new_branch = None
        if get_user_confirmation(
            "Commit on a new branch (so the current branch stays clean)? " "[y/N]: ",
            default_non_interactive=False,
        ):
            default_name = "claude-overlay"
            entered = get_user_input(
                f"New branch name [{default_name}]: ", default_name
            ).strip()
            new_branch = entered or default_name
        committed = _commit_overlay(target_dir, has_claude_local, new_branch)

    print("")
    print(colors.OK + "✓ Firefox Claude settings installed" + colors.END)
    print_hint(f"  Target: {target_dir}")
    print_hint(f"  Hooks and skills are symlinked from: {FIREFOX_CLAUDE_OVERLAY}")
    if gitignore_entries:
        print_hint(f"  Added {len(gitignore_entries)} entries to .gitignore")
    if committed:
        if is_windows():
            print_hint(
                "  Overlay committed as mode-120000 symlink blobs (same\n"
                "  as POSIX). The .git/hooks/post-checkout hook installed\n"
                "  earlier will re-materialize any symlinks that Git for\n"
                "  Windows fails to create on `git checkout` (you may see\n"
                "  'Permission denied' lines from git followed by a\n"
                "  'post-checkout: re-materialized N .claude/ symlinks'\n"
                "  summary — that's expected; the working tree ends up\n"
                "  correct and git status is clean).\n"
                "  Keep Windows Developer Mode enabled so symlinks remain\n"
                "  createable by `ln -s` (which the hook uses)."
            )
        else:
            print_hint(
                "  Overlay committed on current branch. Worktrees created\n"
                "  from this commit (or branches off it) will inherit the\n"
                "  hooks/skills automatically (core.symlinks=true is set)."
            )
    else:
        manual_files = ".claude/ .gitignore" + (
            " CLAUDE.local.md" if has_claude_local else ""
        )
        print_hint(
            "  Changes left uncommitted. To share the overlay with worktrees:\n"
            "    1. Switch to (or create) a side branch for personal config.\n"
            f"    2. git add -f {manual_files}\n"
            "    3. git commit -m 'Install Claude overlay'\n"
            "    4. git worktree add ../<name> <that-side-branch>"
        )
    print("")
    print_warning("IMPORTANT: Restart Claude Code for changes to take effect")

    return True


def uninstall_firefox_claude(target_dir=None, dry_run=False):
    """
    Remove Firefox-specific Claude settings from a target project.
    Only removes symlinks that point to our overlay.
    """
    print_title("Uninstall Firefox Claude Settings")

    # Ask for target directory if not provided
    if not target_dir:
        target_dir = get_user_input("Enter Firefox project path: ")
        if not target_dir:
            print_error("No target directory provided.")
            return False

    target_dir = os.path.expanduser(target_dir)
    target_claude_dir = os.path.join(target_dir, ".claude")

    if not os.path.isdir(target_claude_dir):
        print_warning(f"No .claude directory found: {target_claude_dir}")
        return True

    target_hooks_dir = os.path.join(target_claude_dir, "hooks")
    target_skills_dir = os.path.join(target_claude_dir, "skills")
    target_agents_dir = os.path.join(target_claude_dir, "agents")
    target_settings = os.path.join(target_claude_dir, "settings.local.json")

    removed = []

    if dry_run:
        print(f"\n{colors.HINT}DRY RUN MODE - Would perform these actions:{colors.END}")
        print(f"  Target: {target_dir}")

    # Remove hook symlinks
    if os.path.isdir(target_hooks_dir):
        for hook in os.listdir(target_hooks_dir):
            hook_path = os.path.join(target_hooks_dir, hook)
            if os.path.islink(hook_path):
                link_target = os.readlink(hook_path)
                if FIREFOX_CLAUDE_OVERLAY in link_target or ".dotfiles" in link_target:
                    if dry_run:
                        print(f"  Would remove symlink: {hook_path}")
                    else:
                        os.unlink(hook_path)
                        print(f"Removed: {hook_path}")
                    removed.append(hook_path)

    # Remove agent symlinks
    if os.path.isdir(target_agents_dir):
        for agent in os.listdir(target_agents_dir):
            agent_path = os.path.join(target_agents_dir, agent)
            if os.path.islink(agent_path):
                link_target = os.readlink(agent_path)
                if FIREFOX_CLAUDE_OVERLAY in link_target or ".dotfiles" in link_target:
                    if dry_run:
                        print(f"  Would remove symlink: {agent_path}")
                    else:
                        os.unlink(agent_path)
                        print(f"Removed: {agent_path}")
                    removed.append(agent_path)

    # Remove skill symlinks (personal and media-skills) and materialized
    # renamed alwu-skill directories.
    if os.path.isdir(target_skills_dir):
        for skill in os.listdir(target_skills_dir):
            skill_path = os.path.join(target_skills_dir, skill)
            if os.path.islink(skill_path):
                link_target = os.readlink(skill_path)
                if (
                    FIREFOX_CLAUDE_OVERLAY in link_target
                    or ALWU_CLAUDE_SKILLS_DIR in link_target
                    or MEDIA_SKILLS_DIR in link_target
                    or ".dotfiles" in link_target
                ):
                    if dry_run:
                        print(f"  Would remove symlink: {skill_path}")
                    else:
                        os.unlink(skill_path)
                        print(f"Removed: {skill_path}")
                    removed.append(skill_path)
            elif _is_materialized_skill(skill_path, skill):
                if dry_run:
                    print(f"  Would remove materialized dir: {skill_path}")
                else:
                    shutil.rmtree(skill_path)
                    print(f"Removed: {skill_path}")
                removed.append(skill_path)

    # Remove settings symlink
    if os.path.islink(target_settings):
        link_target = os.readlink(target_settings)
        if FIREFOX_CLAUDE_OVERLAY in link_target or ".dotfiles" in link_target:
            if dry_run:
                print(f"  Would remove symlink: {target_settings}")
            else:
                os.unlink(target_settings)
                print(f"Removed: {target_settings}")
            removed.append(target_settings)

            # Restore backup if exists
            backup = target_settings + ".backup"
            if os.path.exists(backup):
                if dry_run:
                    print(f"  Would restore backup: {backup}")
                else:
                    shutil.move(backup, target_settings)
                    print(f"Restored: {target_settings}")

    # Clean up empty directories
    for dir_path in [target_hooks_dir, target_skills_dir, target_agents_dir]:
        if os.path.isdir(dir_path) and not os.listdir(dir_path):
            if dry_run:
                print(f"  Would remove empty directory: {dir_path}")
            else:
                os.rmdir(dir_path)
                print(f"Removed empty directory: {dir_path}")

    if dry_run:
        print(f"\n{colors.HINT}Run without --dry-run to apply changes{colors.END}")
        return True

    if removed:
        print("")
        print(colors.OK + f"✓ Removed {len(removed)} item(s)" + colors.END)
    else:
        print_hint("No dotfiles symlinks found to remove")

    return True


def show_claude_security_log():
    """Show blocked access log from security hooks."""
    print_title("Claude Security Blocks Log")

    log_file = os.path.join(get_home_dir(), ".claude", "security-blocks.log")
    legacy_log = os.path.join(
        get_home_dir(), ".dotfiles-claude-hooks", "security-blocks.log"
    )

    # Fall back to the legacy location if the new file doesn't exist yet
    # but a pre-migration log is still around.
    if not os.path.exists(log_file) and os.path.exists(legacy_log):
        log_file = legacy_log

    if not os.path.exists(log_file):
        print_hint(f"No log file found at: {log_file}")
        print_hint("This means no access has been blocked yet")
        return True

    try:
        with open(log_file, "r") as f:
            lines = f.readlines()

        if not lines:
            print_hint("Log file is empty - no blocks recorded")
            return True

        print(f"Blocked access attempts: {len(lines)}")
        print("=" * 60)

        # Show last 20 entries
        for line in lines[-20:]:
            try:
                entry = json.loads(line)
                timestamp = entry.get("timestamp", "Unknown")
                tool = entry.get("tool_name", "Unknown")
                file_path = entry.get("file_path", "Unknown")
                reason = entry.get("reason", "Unknown")

                print(f"\n{colors.WARNING}Blocked:{colors.END} {timestamp}")
                print(f"  Tool:   {tool}")
                print(f"  File:   {file_path}")
                print(f"  Reason: {reason}")
            except json.JSONDecodeError:
                continue

        if len(lines) > 20:
            print(
                f"\n{colors.HINT}... showing last 20 of {len(lines)} entries{colors.END}"
            )

        print("\n" + "=" * 60)
        print(f"Full log: {log_file}")

    except Exception as e:
        print_error(f"Error reading log file: {e}")
        return False

    return True


def claude_session_sync_init(tracker, dry_run=False):
    """Install claude-session-sync tool."""
    print_title("Claude Session Sync")

    if not dry_run and not ensure_symlink_capability():
        print_error("Symlink creation unavailable; skipping claude-session-sync")
        return False

    source_script = os.path.join(BASE_DIR, "claude", "session_sync.py")
    dest_bin = os.path.join(
        get_config()["DOTFILES_LOCAL_BIN_DIR"], "claude-session-sync"
    )
    template_file = os.path.join(BASE_DIR, "claude", "CLAUDE.md.template")
    claude_md = os.path.join(get_home_dir(), ".claude", "CLAUDE.md")

    if dry_run:
        print(f"\n{colors.HINT}DRY RUN MODE - Would perform these actions:{colors.END}")
        print(f"  1. Make executable: {source_script}")
        print(f"  2. Symlink: {dest_bin} -> {source_script}")
        print(f"  3. Append template to: {claude_md}")
        return True

    # 1. chmod +x
    os.chmod(source_script, 0o755)

    # 2. Symlink
    link(source_script, dest_bin, tracker)

    # 3. Append CLAUDE.md.template to ~/.claude/CLAUDE.md
    marker = "## Session Transcript Sync"
    if os.path.exists(claude_md):
        with open(claude_md) as f:
            if marker in f.read():
                print_hint("Session sync instructions already in CLAUDE.md")
                return True

    with open(template_file) as f:
        template_content = f.read()

    os.makedirs(os.path.dirname(claude_md), exist_ok=True)
    with open(claude_md, "a") as f:
        f.write("\n" + template_content)

    tracker.record_lines_appended(claude_md, template_content.splitlines())
    print("✓ Claude session sync installed")
    return True


def main(argv):
    global VERBOSE

    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Setup dotfiles configuration for bash, git, and optional Mozilla tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 setup.py                    # Install dotfiles and git config
  python3 setup.py --dry-run          # Show what would be done (no changes made)
  python3 setup.py -v                 # Verbose mode (show detailed operations)
  python3 setup.py --mozilla          # Install all Mozilla tools
  python3 setup.py --mozilla firefox tools # Install specific Mozilla tools
  python3 setup.py --dev-tools        # Install all dev tools (shellcheck, ruff, black, markdownlint)
  python3 setup.py --dev-tools ruff black # Install specific dev tools
  python3 setup.py --dry-run --mozilla --dev-tools # Preview full setup
  python3 setup.py --claude-security  # Install Claude Code security hooks
  python3 setup.py --claude-session-sync  # Install claude-session-sync transcript export tool
  python3 setup.py --all              # Install everything (dotfiles + git + mozilla + dev-tools + claude-security + claude-session-sync)
  python3 setup.py --show-claude-hooks # Show installed hooks
  python3 setup.py --remove-claude-security # Remove security hooks
  python3 setup.py --install-firefox-claude # Install Firefox Claude settings (prompts for path)
  python3 setup.py --install-firefox-claude /path/to/firefox # Install to specific path
  python3 setup.py --uninstall-firefox-claude # Remove Firefox Claude settings
        """,
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show detailed operations for debugging",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making any changes",
    )
    parser.add_argument(
        "--mozilla",
        nargs="*",
        help="Install Mozilla toolkit for firefox development (firefox, tools, rust, pernosco)",
    )
    parser.add_argument(
        "--dev-tools",
        nargs="*",
        help="Install development tools (shellcheck, ruff, black, markdownlint) and pre-commit hooks",
    )
    parser.add_argument(
        "--claude-security",
        action="store_true",
        help="Install Claude Code security hooks (system-wide, blocks access to credentials)",
    )
    parser.add_argument(
        "--claude-session-sync",
        action="store_true",
        help="Install claude-session-sync transcript export tool",
    )
    parser.add_argument(
        "--remove-claude-security",
        action="store_true",
        help="Remove Claude Code security hooks",
    )
    parser.add_argument(
        "--show-claude-hooks",
        action="store_true",
        help="Show all installed Claude Code hooks",
    )
    parser.add_argument(
        "--show-claude-security-log",
        action="store_true",
        help="Show log of blocked access attempts",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Install all components (dotfiles + git + mozilla + dev-tools + claude-security + claude-session-sync)",
    )
    parser.add_argument(
        "--install-firefox-claude",
        nargs="?",
        const="",
        metavar="PATH",
        help="Install Firefox Claude settings (hooks, skills) to a project. Prompts for path if not provided.",
    )
    parser.add_argument(
        "--uninstall-firefox-claude",
        nargs="?",
        const="",
        metavar="PATH",
        help="Remove Firefox Claude settings from a project. Prompts for path if not provided.",
    )
    args = parser.parse_args(argv[1:])

    # Set global flags
    global VERBOSE, DRY_RUN
    VERBOSE = args.verbose
    DRY_RUN = args.dry_run

    # Show dry-run banner
    if DRY_RUN:
        print_title("DRY-RUN MODE - No changes will be made")
        print(
            colors.HINT
            + "This will show what would be done without making any actual changes."
            + colors.END
        )
        print("")

    print_verbose(
        "Arguments parsed: verbose={}, dry_run={}, mozilla={}, dev_tools={}".format(
            args.verbose, args.dry_run, args.mozilla, args.dev_tools
        )
    )
    print_verbose("BASE_DIR: {}".format(BASE_DIR))
    print_verbose("HOME_DIR: {}".format(HOME_DIR))

    # Handle show commands (don't need tracker)
    if args.show_claude_hooks:
        return 0 if show_claude_hooks() else 1

    if args.show_claude_security_log:
        return 0 if show_claude_security_log() else 1

    # Handle removal command (don't need tracker)
    if args.remove_claude_security:
        return 0 if claude_security_remove(DRY_RUN) else 1

    # Handle Firefox Claude install/uninstall (standalone commands)
    if args.install_firefox_claude is not None:
        target = args.install_firefox_claude if args.install_firefox_claude else None
        return 0 if install_firefox_claude(target, DRY_RUN) else 1

    if args.uninstall_firefox_claude is not None:
        target = (
            args.uninstall_firefox_claude if args.uninstall_firefox_claude else None
        )
        return 0 if uninstall_firefox_claude(target, DRY_RUN) else 1

    # Handle --all flag
    if args.all:
        args.mozilla = args.mozilla or []
        args.dev_tools = args.dev_tools or []
        args.claude_security = True
        args.claude_session_sync = True

    # Create change tracker for rollback capability
    tracker = ChangeTracker()
    print_verbose("ChangeTracker created")

    results = {
        "dotfiles": dotfiles_link(tracker),
        "bash": bash_link(tracker),
        "git": git_init(tracker),
        "mozilla": mozilla_init(args.mozilla, tracker),
        "dev-tools": dev_tools_init(args.dev_tools, tracker),
        "claude-security": (
            claude_security_init(tracker, DRY_RUN) if args.claude_security else None
        ),
        "claude-session-sync": (
            claude_session_sync_init(tracker, DRY_RUN)
            if args.claude_session_sync
            else None
        ),
    }

    show_setup_summary(results)

    # In dry-run mode, skip verification and show final message
    if DRY_RUN:
        print("")
        print_title("DRY-RUN COMPLETE")
        print(colors.HINT + "No changes were made to your system." + colors.END)
        print(
            colors.OK
            + "To actually apply these changes, run without --dry-run flag."
            + colors.END
        )
        return 0

    # Only verify if setup succeeded
    if all(r is not False for r in results.values()):
        # Setup succeeded, run verification
        verification_passed, issues = verify_installation()

        if verification_passed:
            # Both setup and verification successful
            print_hint(
                "Please run `$ source ~/.bashrc` to turn on the environment settings"
            )
            return 0
        else:
            # Setup succeeded but verification failed
            print_error("Installation verification failed!")
            print_error("Fix the issues above and re-run setup.py")

            # Offer rollback for verification failures
            if tracker.has_changes():
                print_warning(
                    "Setup made {} change(s) before verification failed".format(
                        tracker.get_change_count()
                    )
                )
                if get_user_confirmation(
                    "Rollback all changes? [y/N]: ", default_non_interactive=False
                ):
                    rollback_changes(tracker)

            return 1
    else:
        # Setup failed
        # Offer rollback
        if tracker.has_changes():
            print_warning(
                "Setup made {} change(s) before failing".format(
                    tracker.get_change_count()
                )
            )
            if get_user_confirmation(
                "Rollback all changes? [y/N]: ", default_non_interactive=False
            ):
                rollback_changes(tracker)
            else:
                print("Changes kept. You can re-run setup.py after fixing issues.")

        return 1


if __name__ == "__main__":
    try:
        exit_code = main(sys.argv)
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("abort")
        sys.exit(130)  # Standard exit code for SIGINT
