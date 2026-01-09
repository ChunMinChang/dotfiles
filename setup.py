import argparse
import fileinput
import os
import platform
import re
import subprocess
import sys

# Global variables
# ------------------------------------------------------------------------------

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
HOME_DIR = os.environ['HOME']
VERBOSE = False  # Set to True with -v/--verbose flag
DRY_RUN = False  # Set to True with --dry-run flag

# Configuration paths loaded from config.sh
CONFIG = None  # Lazy-loaded config dictionary

# Note: Python print functions kept separate from shell utils.sh
# (Python can't source bash scripts - different language ecosystems)
# Shell scripts use Print* functions from utils.sh
class colors:
    HEADER = '\033[94m'   # Blue
    HINT = '\033[46m'     # Background Cyan
    OK = '\033[92m'       # Green
    WARNING = '\033[93m'  # Yellow
    FAIL = '\033[91m'     # Red
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

# Utils
# ------------------------------------------------------------------------------

def load_config():
    """Load configuration from config.sh.

    Returns a dictionary with all DOTFILES_* configuration variables.
    Falls back to default hardcoded values if config.sh cannot be loaded.
    """
    config_path = os.path.join(BASE_DIR, 'config.sh')

    # Default fallback values (same as previous hardcoded values)
    defaults = {
        'DOTFILES_MOZBUILD_DIR': os.path.join(HOME_DIR, '.mozbuild'),
        'DOTFILES_LOCAL_BIN_DIR': os.path.join(HOME_DIR, '.local', 'bin'),
        'DOTFILES_WORK_BIN_DIR': os.path.join(HOME_DIR, 'Work', 'bin'),
        'DOTFILES_CARGO_DIR': os.path.join(HOME_DIR, '.cargo'),
        'DOTFILES_TRASH_DIR_LINUX': os.path.join(HOME_DIR, '.local', 'share', 'Trash', 'files'),
        'DOTFILES_TRASH_DIR_DARWIN': os.path.join(HOME_DIR, '.Trash'),
        'DOTFILES_MACHRC_PATH': os.path.join(HOME_DIR, '.mozbuild', 'machrc'),
        'DOTFILES_CARGO_ENV_PATH': os.path.join(HOME_DIR, '.cargo', 'env'),
    }

    # Try to load from config.sh
    if not os.path.exists(config_path):
        print_verbose('config.sh not found, using default values')
        return defaults

    try:
        # Source config.sh and export all DOTFILES_* variables
        cmd = f'source "{config_path}" && env | grep "^DOTFILES_"'
        result = subprocess.run(
            ['bash', '-c', cmd],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            print_verbose('Failed to source config.sh, using defaults')
            return defaults

        # Parse the output to extract config values
        config = defaults.copy()
        for line in result.stdout.strip().split('\n'):
            if '=' in line:
                key, value = line.split('=', 1)
                config[key] = value

        print_verbose('Config loaded from config.sh')
        return config

    except (subprocess.TimeoutExpired, Exception) as e:
        print_verbose('Error loading config.sh: {}'.format(e))
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
        self.changes.append({
            'type': 'symlink',
            'target': target,
            'source': source,
            'old_target': old_target
        })
        print_verbose('ChangeTracker: Recorded symlink {} -> {}'.format(target, source))

    def record_lines_appended(self, file_path, lines):
        """Record that lines were appended to a file.

        Args:
            file_path: Path to file that was modified
            lines: List of lines that were appended
        """
        self.changes.append({
            'type': 'append',
            'file': file_path,
            'lines': lines
        })
        print_verbose('ChangeTracker: Recorded {} line(s) appended to {}'.format(
            len(lines), file_path))

    def record_git_config(self, key, value):
        """Record that a git config was set.

        Args:
            key: Git config key that was set
            value: Value that was set
        """
        self.changes.append({
            'type': 'git_config',
            'key': key,
            'value': value
        })
        print_verbose('ChangeTracker: Recorded git config {} = {}'.format(key, value))

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
        print('No changes to rollback.')
        return True

    print_title('Rolling Back Changes')
    print('Undoing {} change(s)...'.format(tracker.get_change_count()))

    errors = []
    # Process changes in reverse order (undo most recent first)
    for change in reversed(tracker.changes):
        try:
            if change['type'] == 'symlink':
                target = change['target']
                old_target = change.get('old_target')

                if os.path.islink(target):
                    print('Removing symlink: {}'.format(target))
                    os.unlink(target)

                    # If we replaced an existing symlink, restore it
                    if old_target:
                        print('Restoring previous symlink: {} -> {}'.format(target, old_target))
                        os.symlink(old_target, target)
                elif os.path.exists(target):
                    print_warning('Not removing {} (not a symlink)'.format(target))
                else:
                    print_verbose('Symlink {} already removed'.format(target))

            elif change['type'] == 'append':
                file_path = change['file']
                lines = change['lines']

                if not os.path.exists(file_path):
                    print_verbose('File {} does not exist, skipping'.format(file_path))
                    continue

                print('Removing {} line(s) from {}'.format(len(lines), file_path))

                # Read all lines
                with open(file_path, 'r') as f:
                    all_lines = f.readlines()

                # Remove the appended lines
                lines_to_remove = set(line.rstrip('\n') for line in lines)
                filtered_lines = [
                    line for line in all_lines
                    if line.rstrip('\n') not in lines_to_remove
                ]

                # Write back filtered content
                with open(file_path, 'w') as f:
                    f.writelines(filtered_lines)

            elif change['type'] == 'git_config':
                key = change['key']
                print('Removing git config: {}'.format(key))

                # Remove the git config setting
                result = subprocess.run(
                    ['git', 'config', '--global', '--unset', key],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                if result.returncode != 0:
                    # Non-zero could mean already unset, which is fine
                    print_verbose('git config unset returned {}'.format(result.returncode))

        except Exception as e:
            error_msg = 'Error rolling back {}: {}'.format(change['type'], e)
            print_error(error_msg)
            errors.append(error_msg)

    if errors:
        print_error('Rollback completed with {} error(s)'.format(len(errors)))
        return False
    else:
        print_ok('Rollback completed successfully')
        return True


# Symbolically link source to target
def link(source, target, tracker=None):
    print_verbose('link() called: source={}, target={}'.format(source, target))

    # Validate source exists before creating symlink
    print_verbose('Checking if source exists: {}'.format(source))
    if not os.path.exists(source):
        print_error('Cannot create symlink: source does not exist')
        print_error('Source: {}'.format(source))
        print_verbose('link() returning: False (source does not exist)')
        return False

    print_verbose('Source exists: True')
    print_verbose('Checking if target is a symlink: {}'.format(target))

    old_target = None
    if os.path.islink(target):
        print_verbose('Target is a symlink, unlinking')
        # Record what the old symlink pointed to
        old_target = os.readlink(target)

        if DRY_RUN:
            print_dry_run('Would unlink {}'.format(target))
        else:
            print('unlink {}'.format(target))
            os.unlink(target)
    else:
        print_verbose('Target is not a symlink or does not exist')

    if DRY_RUN:
        print_dry_run('Would link {} to {}'.format(source, target))
    else:
        print('link {} to {}'.format(source, target))
        os.symlink(source, target)
        print_verbose('Symlink created successfully')

    # Record the change if tracker provided (even in dry-run for preview)
    if tracker and not DRY_RUN:
        tracker.record_symlink_created(target, source, old_target)

    print_verbose('link() returning: True')
    return True

# Check if `name` exists
def is_tool(name):
    cmd = "where" if platform.system() == "Windows" else "which"
    try:
        r = subprocess.check_output([cmd, name], stderr=subprocess.DEVNULL)
        print('{} is found in {}'.format(name, r.decode("utf-8")))
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
        print_warning('Error checking for {}: {}'.format(name, str(e)))
        return False


def append_to_next_line_after(name, pattern, value=''):
    file = fileinput.input(name, inplace=True)
    for line in file:
        replacement = line + ('\n' if '\n' not in line else '') + value
        line = re.sub(pattern, replacement, line)
        sys.stdout.write(line)
    file.close()


def bash_export_command(path):
    return ''.join(['export PATH=', path, ':$PATH'])


def bash_load_command(path):
    return ''.join(['[ -r ', path, ' ] && . ', path])


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
        print_error('File does not exist: {}'.format(file))
        return False

    # Validate file is writable
    if not os.access(file, os.W_OK):
        print_error('File is not writable: {}'.format(file))
        return False

    try:
        # Read existing lines
        with open(file, 'r') as f:
            existing_lines = [line.rstrip('\n') for line in f]

        # Check if file ends with newline
        needs_newline = False
        if existing_lines and len(existing_lines) > 0:
            with open(file, 'rb') as f:
                f.seek(-1, os.SEEK_END)
                last_char = f.read(1)
                needs_newline = (last_char != b'\n')

        # Determine which lines to append
        lines_to_append = []
        for line in lines:
            if line in existing_lines:
                print_warning('{} is already in {}'.format(line, file))
            else:
                lines_to_append.append(line)

        # Append new lines
        if lines_to_append:
            if DRY_RUN:
                if needs_newline:
                    print_dry_run('Would add newline at end of {}'.format(file))
                for line in lines_to_append:
                    print_dry_run('Would append into {}: {}'.format(file, line))
            else:
                with open(file, 'a') as f:
                    # Add newline to last line if needed
                    if needs_newline:
                        f.write('\n')

                    for line in lines_to_append:
                        f.write(line + '\n')
                        print('{} is appended into {}'.format(line, file))

                # Record the change if tracker provided
                if tracker:
                    tracker.record_lines_appended(file, lines_to_append)

        return True

    except IOError as e:
        print_error('Failed to modify {}: {}'.format(file, str(e)))
        return False
    except Exception as e:
        print_error('Unexpected error modifying {}: {}'.format(file, str(e)))
        return False



def print_installing_title(name, bold=False):
    print(colors.HEADER + ''.join(['\n', name,
                                   ('\n==============================' if bold
                                    else '\n--------------------')]) + colors.END)

# Python print functions (see note at line 15 for why separate from shell)
def print_hint(message):
    print(colors.HINT + message + colors.END + '\n')


def print_warning(message):
    print(colors.WARNING + 'WARNING: ' + message + colors.END + '\n')


def print_fail(message):
    print(colors.FAIL + 'ERROR: ' + message + colors.END + '\n')


# Alias for consistency
def print_error(message):
    print_fail(message)


def print_verbose(message):
    """Print verbose debugging information (only when VERBOSE=True)"""
    if VERBOSE:
        print(colors.HEADER + '[VERBOSE] ' + colors.END + message)


def print_dry_run(message):
    """Print dry-run action (only when DRY_RUN=True)"""
    if DRY_RUN:
        print(colors.HINT + '[DRY-RUN] ' + colors.END + message)


def print_title(message):
    """Print a section title"""
    print('\n' + colors.HEADER + '=' * 50 + colors.END)
    print(colors.HEADER + message + colors.END)
    print(colors.HEADER + '=' * 50 + colors.END)


# Setup functions
# ------------------------------------------------------------------------------

# Link this dotfiles path to $HOME/.dotfiles
def dotfiles_link(tracker=None):
    print_installing_title('dotfile path')
    print_verbose('dotfiles_link() starting')
    result = link(BASE_DIR, os.path.join(HOME_DIR, '.dotfiles'), tracker)
    print_verbose('dotfiles_link() returning: {}'.format(result))
    return result

# Link dot.* to ~/.*
def bash_link(tracker=None):
    print_installing_title('bash startup scripts')
    print_verbose('bash_link() starting')
    print_verbose('Platform: {}'.format(platform.system()))

    platform_files = {
        'Darwin': [
            'dot.bashrc',
            'dot.zshrc',
            'dot.settings_darwin'
        ],
        'Linux': [
            'dot.bashrc',
            'dot.settings_linux'
        ],
    }

    if platform.system() == 'Darwin':
        v, _, _ = platform.mac_ver()
        version_parts = v.split('.')[:2]
        try:
            major = int(version_parts[0]) if version_parts else 0
            minor = int(version_parts[1]) if len(version_parts) > 1 else 0
        except (ValueError, IndexError):
            # If version parsing fails, assume modern macOS (use zshrc)
            major, minor = 11, 0

        platform_files[platform.system()].append(
            'dot.zshrc' if (major, minor) >= (10, 15) else 'dot.bash_profile')

    #files = filter(lambda f: f.startswith('dot.'), os.listdir(BASE_DIR))
    files = platform_files[platform.system()]
    print_verbose('Files to process: {}'.format(files))
    errors = []
    skipped = []

    for f in files:
        print_verbose('Processing file: {}'.format(f))
        target = os.path.join(HOME_DIR, f[3:])  # Get name after dot
        src = os.path.join(BASE_DIR, f)
        if os.path.isfile(target):
            # Check if source exists before comparing
            if not os.path.exists(src):
                print_error('Source file does not exist: {}'.format(src))
                print_error('Repository may be incomplete or corrupted')
                errors.append('Source file missing: {}'.format(f))
                continue

            if os.path.samefile(src, target):
                print_warning('{} is already linked!'.format(target))
                continue
            print_warning('{} already exists!'.format(target))
            if f == 'dot.bashrc' or f == 'dot.zshrc':
                print('Append a command to load {} in {}'.format(src, target))
                result = append_nonexistent_lines_to_file(
                    target, [bash_load_command(src)], tracker)
                if not result:
                    errors.append('Failed to append to {}'.format(target))
            else:
                # File exists but isn't bashrc/zshrc - provide guidance
                print('Options:')
                print('  1. Remove {} and re-run setup'.format(target))
                print('  2. Manually replace with symlink: ln -sf {} {}'.format(src, target))
                print('  3. Keep existing file (skip)')
                skipped.append(f)
        else:
            result = link(src, target, tracker)
            if not result:
                errors.append('Failed to link {}'.format(f))

    # Return True only if no errors (skipped files are user choice, not errors)
    success = len(errors) == 0
    print_verbose('bash_link() completed: errors={}, skipped={}'.format(len(errors), len(skipped)))
    print_verbose('bash_link() returning: {}'.format(success))
    return success

# Include git/config from ~/.giconfig
def git_init(tracker=None):
    print_installing_title('git settings')
    if not is_tool('git'):
        print_fail('Please install git first!')
        return False

    git_config = os.path.join(HOME_DIR, '.gitconfig')
    if not os.path.isfile(git_config):
        print_warning(
            '{} does not exist! Create a new one with default settings!'.format(git_config))
        # Set global user name and email
        subprocess.call(['git', 'config', '--global',
                        'user.name', 'Chun-Min Chang'])
        subprocess.call(['git', 'config', '--global',
                        'user.email', 'chun.m.chang@gmail.com'])

    # Include git config here in global gitconfig file
    path = os.path.join(BASE_DIR, 'git', 'config')
    if not os.path.exists(path):
        print_error('Git config file not found: {}'.format(path))
        print_error('Cannot configure git include.path')
        return False

    if DRY_RUN:
        print_dry_run('Would run: git config --global include.path {}'.format(path))
    else:
        subprocess.call(['git', 'config', '--global', 'include.path', path])

        # Record the git config change
        if tracker:
            tracker.record_git_config('include.path', path)

    # Show the current file if it exists:
    if os.path.exists(git_config):
        with open(git_config, 'r') as f:
            content = f.read()
            print_hint('{}:'.format(git_config))
            print(content)
            f.close()
    else:
        print_warning('Git config file not found: {}'.format(git_config))
        print_warning('Git configuration may not be complete')

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
    print_installing_title('mozilla settings', True)

    if mozilla_arg is None:
        print_warning('Skip installing mozilla toolkit')
        print_verbose('mozilla_arg is None, skipping Mozilla tools')
        return None  # None = skipped, not failure

    print_verbose('mozilla_arg: {}'.format(mozilla_arg))

    funcs = {
        'gecko': gecko_init,
        'hg': hg_init,
        'tools': tools_init,
        'rust': rust_init,
    }

    # Select which Mozilla tools to install
    if mozilla_arg:
        # User specified tools: filter to valid options only
        options = [k for k in mozilla_arg if k in funcs]
        print_verbose('Selected Mozilla tools: {}'.format(options))
    else:
        # No tools specified: install all
        options = list(funcs.keys())
        print_verbose('No tools specified, installing all: {}'.format(options))

    all_succeeded = True
    for k in options:
        result = funcs[k](tracker)
        if not result:
            all_succeeded = False

    return all_succeeded


def gecko_init(tracker=None):
    print_installing_title('gecko alias and machrc')
    config = get_config()
    machrc = config['DOTFILES_MACHRC_PATH']
    if os.path.isfile(machrc):
        print_fail(''.join(['{} exists! Abort!\n'.format(machrc),
                            'Apply default settings for now.']))
    else:
        path = os.path.join(BASE_DIR, 'mozilla', 'gecko', 'machrc')
        if not link(path, machrc, tracker):
            return False

    bashrc = os.path.join(BASE_DIR, 'dot.bashrc')
    if not os.path.isfile(bashrc):
        print_fail('{} does not exist! Abort!'.format(bashrc))
        return False

    path = os.path.join(BASE_DIR, 'mozilla', 'gecko', 'alias.sh')
    result = append_nonexistent_lines_to_file(bashrc, [bash_load_command(path)], tracker)
    return result


def hg_init(tracker=None):
    print_installing_title('hg settings')
    error_messages = ['\tRun ./mach bootstrap.py under gecko-dev to fix it.']

    if not is_tool('hg'):
        error_messages.insert(0, 'Please install hg(mercurial) first!')
        print_fail(''.join(error_messages))
        return False

    hg_config = os.path.join(HOME_DIR, '.hgrc')
    if not os.path.isfile(hg_config):
        error_messages.insert(0, '{} does not exist! Abort!'.format(hg_config))
        print_fail(''.join(error_messages))
        return False

    path = os.path.join(BASE_DIR, 'mozilla', 'hg', 'config')
    result = append_nonexistent_lines_to_file(hg_config, ['%include ' + path], tracker)
    return result


def tools_init(tracker=None):
    print_installing_title('tools settings')

    bashrc = os.path.join(BASE_DIR, 'dot.bashrc')
    if not os.path.isfile(bashrc):
        print_fail('{} does not exist! Abort!'.format(bashrc))
        return False

    path = os.path.join(BASE_DIR, 'mozilla', 'gecko', 'tools.sh')
    result = append_nonexistent_lines_to_file(bashrc, [bash_load_command(path)], tracker)
    return result


def rust_init(tracker=None):
    print_installing_title('rust settings')
    error_messages = ['\tRun ./mach bootstrap.py under gecko-dev to fix it.']

    bashrc = os.path.join(BASE_DIR, 'dot.bashrc')
    if not os.path.isfile(bashrc):
        print_fail('{} does not exist! Abort!'.format(bashrc))
        return False

    config = get_config()
    cargo_env = config['DOTFILES_CARGO_ENV_PATH']
    if not os.path.isfile(cargo_env):
        error_messages.insert(0, '{} does not exist! Abort!'.format(cargo_env))
        print_fail(''.join(error_messages))
        return False

    result = append_nonexistent_lines_to_file(bashrc, [bash_load_command(cargo_env)], tracker)
    return result


# Development Tools (Pre-commit Hooks)
# ---------------------------------------

def print_tool_prompt(tool_name, benefits, consequences):
    """Display information about a dev tool and prompt user for installation."""
    print('\n' + colors.BOLD + tool_name + colors.END)
    print(colors.OK + 'Benefits:' + colors.END)
    for benefit in benefits:
        print('  • {}'.format(benefit))
    print(colors.WARNING + 'If you skip:' + colors.END)
    for consequence in consequences:
        print('  • {}'.format(consequence))


def is_interactive():
    """Check if running in interactive mode (has TTY)."""
    return sys.stdin.isatty()


def get_user_confirmation(prompt='Install this tool? [y/N]: ', default_non_interactive=False):
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
        action = 'Installing' if default_non_interactive else 'Skipping'
        print(colors.WARNING + f'Non-interactive mode detected: {action} (use default)' + colors.END)
        return default_non_interactive

    # Interactive mode: prompt user
    try:
        response = input(prompt).strip().lower()
        return response in ['y', 'yes']
    except (EOFError, KeyboardInterrupt):
        print()  # New line after Ctrl+C
        return False


def install_shellcheck(tracker=None):
    """Install shellcheck for bash script validation."""
    print_installing_title('shellcheck (bash script linter)')

    # Check if already installed
    if is_tool('shellcheck'):
        print('shellcheck is already installed')
        return True

    # Display info and prompt user
    print_tool_prompt(
        'ShellCheck',
        [
            'Catches common bash scripting errors before they cause issues',
            'Enforces best practices for portability and safety',
            'Detects syntax errors, unquoted variables, and unsafe patterns'
        ],
        [
            'Pre-commit hook will skip bash script validation',
            'Bash errors may only be caught at runtime',
            'You can manually install later with: sudo apt-get install shellcheck (Linux) or brew install shellcheck (macOS)'
        ]
    )

    if not get_user_confirmation():
        print('Skipping shellcheck installation')
        return None  # Skipped

    # Check if sudo is available
    has_sudo = False
    if platform.system() == 'Linux':
        try:
            result = subprocess.run(['sudo', '-n', 'true'],
                                    capture_output=True, timeout=5)
            has_sudo = (result.returncode == 0)
        except:
            has_sudo = False

    # Install based on platform
    try:
        if platform.system() == 'Linux':
            if not has_sudo:
                print_warning('Sudo access required for shellcheck on Linux')
                print('Please install manually: sudo apt-get install shellcheck')
                print('Or configure passwordless sudo for this session')
                return None  # Skipped

            print('Installing shellcheck via apt-get...')
            result = subprocess.run(['sudo', 'apt-get', 'install', '-y', 'shellcheck'],
                                    capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                print(colors.OK + '✓ shellcheck installed successfully' + colors.END)
                return True
            else:
                print_error('Failed to install shellcheck: {}'.format(result.stderr))
                return False

        elif platform.system() == 'Darwin':
            if not is_tool('brew'):
                print_error('Homebrew not found. Please install from https://brew.sh')
                print('Then install shellcheck: brew install shellcheck')
                return False

            print('Installing shellcheck via homebrew...')
            result = subprocess.run(['brew', 'install', 'shellcheck'],
                                    capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                print(colors.OK + '✓ shellcheck installed successfully' + colors.END)
                return True
            else:
                print_error('Failed to install shellcheck: {}'.format(result.stderr))
                return False
        else:
            print_warning('Unsupported platform for automatic shellcheck installation')
            print('Please install manually: https://github.com/koalaman/shellcheck#installing')
            return None  # Skipped

    except subprocess.TimeoutExpired:
        print_error('Installation timed out')
        return False
    except Exception as e:
        print_error('Installation failed: {}'.format(str(e)))
        return False


def install_ruff(tracker=None):
    """Install ruff for Python linting and formatting."""
    print_installing_title('ruff (Python linter/formatter)')

    # Check if already installed
    if is_tool('ruff'):
        print('ruff is already installed')
        return True

    # Display info and prompt user
    print_tool_prompt(
        'Ruff',
        [
            'Fast Python linter (10-100x faster than pylint/flake8)',
            'Catches Python errors, style issues, and code smells',
            'Enforces PEP 8 and other Python best practices'
        ],
        [
            'Pre-commit hook will skip Python validation',
            'Python code issues may only be caught during execution or review',
            'You can manually install later with: pip3 install --user ruff'
        ]
    )

    if not get_user_confirmation():
        print('Skipping ruff installation')
        return None  # Skipped

    # Install via pip
    try:
        if not is_tool('pip3'):
            print_error('pip3 not found. Please install Python 3 and pip first.')
            return False

        print('Installing ruff via pip...')
        result = subprocess.run(['pip3', 'install', '--user', 'ruff'],
                                capture_output=True, text=True, timeout=180)
        if result.returncode == 0:
            print(colors.OK + '✓ ruff installed successfully' + colors.END)
            print_hint('You may need to add ~/.local/bin to your PATH')
            return True
        else:
            print_error('Failed to install ruff: {}'.format(result.stderr))
            return False

    except subprocess.TimeoutExpired:
        print_error('Installation timed out')
        return False
    except Exception as e:
        print_error('Installation failed: {}'.format(str(e)))
        return False


def install_black(tracker=None):
    """Install black for Python code formatting."""
    print_installing_title('black (Python code formatter)')

    # Check if already installed
    if is_tool('black'):
        print('black is already installed')
        return True

    # Display info and prompt user
    print_tool_prompt(
        'Black',
        [
            'Automatically formats Python code to a consistent style',
            'Saves time on code style discussions and manual formatting',
            'Widely adopted by the Python community (e.g., Django, pytest)'
        ],
        [
            'Pre-commit hook will skip Python auto-formatting checks',
            'Code style may be inconsistent across commits',
            'You can manually install later with: pip3 install --user black'
        ]
    )

    if not get_user_confirmation():
        print('Skipping black installation')
        return None  # Skipped

    # Install via pip
    try:
        if not is_tool('pip3'):
            print_error('pip3 not found. Please install Python 3 and pip first.')
            return False

        print('Installing black via pip...')
        result = subprocess.run(['pip3', 'install', '--user', 'black'],
                                capture_output=True, text=True, timeout=180)
        if result.returncode == 0:
            print(colors.OK + '✓ black installed successfully' + colors.END)
            print_hint('You may need to add ~/.local/bin to your PATH')
            return True
        else:
            print_error('Failed to install black: {}'.format(result.stderr))
            return False

    except subprocess.TimeoutExpired:
        print_error('Installation timed out')
        return False
    except Exception as e:
        print_error('Installation failed: {}'.format(str(e)))
        return False


def install_markdownlint(tracker=None):
    """Install markdownlint-cli for markdown validation."""
    print_installing_title('markdownlint (markdown linter)')

    # Check if already installed
    if is_tool('markdownlint'):
        print('markdownlint is already installed')
        return True

    # Display info and prompt user
    print_tool_prompt(
        'Markdownlint',
        [
            'Validates markdown files for syntax and style consistency',
            'Catches broken links, malformed tables, and formatting issues',
            'Ensures documentation is properly formatted'
        ],
        [
            'Pre-commit hook will skip markdown validation',
            'Documentation formatting issues may go unnoticed',
            'You can manually install later with: npm install -g markdownlint-cli',
            'Note: Requires Node.js and npm (heavier dependency)'
        ]
    )

    if not get_user_confirmation():
        print('Skipping markdownlint installation')
        return None  # Skipped

    # Install via npm
    try:
        if not is_tool('npm'):
            print_warning('npm not found. markdownlint requires Node.js and npm.')
            print('Install Node.js from: https://nodejs.org/')
            print('Then install markdownlint: npm install -g markdownlint-cli')
            return None  # Skipped

        print('Installing markdownlint-cli via npm (may take a while)...')
        result = subprocess.run(['npm', 'install', '-g', 'markdownlint-cli'],
                                capture_output=True, text=True, timeout=300)
        if result.returncode == 0:
            print(colors.OK + '✓ markdownlint installed successfully' + colors.END)
            return True
        else:
            print_error('Failed to install markdownlint: {}'.format(result.stderr))
            return False

    except subprocess.TimeoutExpired:
        print_error('Installation timed out')
        return False
    except Exception as e:
        print_error('Installation failed: {}'.format(str(e)))
        return False


def setup_precommit_hooks(tracker=None):
    """Create project-local pre-commit hook with validation checks."""
    print_installing_title('pre-commit hooks')

    # Check if we're in a git repository
    git_dir = os.path.join(BASE_DIR, '.git')
    if not os.path.isdir(git_dir):
        print_error('Not in a git repository. Cannot install hooks.')
        return False

    hooks_dir = os.path.join(git_dir, 'hooks')
    precommit_hook = os.path.join(hooks_dir, 'pre-commit')

    # Create hooks directory if it doesn't exist
    if not os.path.exists(hooks_dir):
        print('Creating hooks directory: {}'.format(hooks_dir))
        os.makedirs(hooks_dir, exist_ok=True)

    # Create pre-commit hook script
    hook_content = '''#!/bin/bash
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
'''

    try:
        # Check if hook already exists
        if os.path.exists(precommit_hook):
            if DRY_RUN:
                print_dry_run('Pre-commit hook already exists: {}'.format(precommit_hook))
                print_dry_run('Would prompt to replace existing hook')
                return True
            else:
                print_warning('Pre-commit hook already exists: {}'.format(precommit_hook))
                if not get_user_confirmation('Replace existing hook? [y/N]: ', default_non_interactive=False):
                    print('Keeping existing hook')
                    return True  # Not an error

        # Write hook script
        if DRY_RUN:
            print_dry_run('Would create pre-commit hook: {}'.format(precommit_hook))
            print_dry_run('Would make hook executable (chmod 755)')
            print_hint('Hook would be project-local (only for this dotfiles repo)')
            print_hint('Hook would warn about issues but allow commits to proceed')
        else:
            print('Creating pre-commit hook: {}'.format(precommit_hook))
            with open(precommit_hook, 'w') as f:
                f.write(hook_content)

            # Make executable
            os.chmod(precommit_hook, 0o755)

            print(colors.OK + '✓ Pre-commit hook installed successfully' + colors.END)
            print_hint('Hook is project-local (only for this dotfiles repo)')
            print_hint('It will warn about issues but allow commits to proceed')

        return True

    except IOError as e:
        print_error('Failed to create pre-commit hook: {}'.format(str(e)))
        return False
    except Exception as e:
        print_error('Unexpected error: {}'.format(str(e)))
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
    print_installing_title('development tools', True)

    # If dev_tools_arg is None and not explicitly invoked, ask user (skip in dry-run)
    if dev_tools_arg is None:
        if DRY_RUN:
            print_dry_run('Would prompt user to set up development tools')
            print_dry_run('Skipping dev-tools in dry-run mode')
            return None

        print('\nDevelopment tools include linters and formatters for bash, Python, and markdown.')
        print('These tools help catch errors early via pre-commit hooks.')
        print('')
        print(colors.OK + 'Benefits:' + colors.END)
        print('  • Catch syntax errors before they reach the repository')
        print('  • Enforce consistent code style across all files')
        print('  • Reduce code review time by automating basic checks')
        print('  • Find bugs early (e.g., unquoted variables, unused imports)')
        print('')

        if not get_user_confirmation('Would you like to set up development tools? [y/N]: ', default_non_interactive=False):
            print_warning('Skipping development tools setup')
            return None  # None = skipped, not failure

        # User said yes, proceed with all tools
        dev_tools_arg = []  # Empty list means install all

    # In dry-run mode, just show what would be done
    if DRY_RUN and dev_tools_arg is not None:
        print_dry_run('Would install development tools')
        if dev_tools_arg:
            print_dry_run('Specified tools: {}'.format(', '.join(dev_tools_arg)))
        else:
            print_dry_run('Would install all tools: shellcheck, ruff, black, markdownlint')
        print_dry_run('Would set up pre-commit hooks')
        return True

    print_verbose('dev_tools_arg: {}'.format(dev_tools_arg))

    # Define available tools
    tools = {
        'shellcheck': install_shellcheck,
        'ruff': install_ruff,
        'black': install_black,
        'markdownlint': install_markdownlint,
    }

    # Select which tools to install
    if dev_tools_arg:
        # User specified specific tools
        options = [k for k in dev_tools_arg if k in tools]
        print_verbose('Selected tools: {}'.format(options))
    else:
        # No tools specified: ask about all
        options = list(tools.keys())
        print_verbose('No tools specified, asking about all: {}'.format(options))

    # Install each tool
    results = {}
    for tool_name in options:
        result = tools[tool_name](tracker)
        results[tool_name] = result

    # Set up pre-commit hooks
    print('')
    print('Pre-commit hooks will run the installed tools automatically before each commit.')
    hook_result = setup_precommit_hooks(tracker)
    results['pre-commit-hook'] = hook_result

    # Determine overall success
    # None = skipped (ok), False = failed, True = succeeded
    failures = [name for name, result in results.items() if result is False]

    if failures:
        print('')
        print(colors.WARNING + 'Some tools failed to install: {}'.format(', '.join(failures)) + colors.END)
        return False
    else:
        print('')
        print(colors.OK + '✓ Development tools setup complete' + colors.END)
        return True


# Installation Verification
# ------------------------------------------------------------------------------

def verify_symlinks():
    """Verify all symlinks created during setup are valid."""
    symlinks_to_check = [
        (os.path.join(HOME_DIR, '.dotfiles'), BASE_DIR, True),  # Must exist
    ]

    # Add platform-specific symlinks
    if platform.system() == 'Linux':
        symlinks_to_check.append(
            (os.path.join(HOME_DIR, '.settings_linux'),
             os.path.join(BASE_DIR, 'dot.settings_linux'), False)  # Optional
        )
    elif platform.system() == 'Darwin':
        symlinks_to_check.append(
            (os.path.join(HOME_DIR, '.settings_darwin'),
             os.path.join(BASE_DIR, 'dot.settings_darwin'), False)  # Optional
        )

    issues = []
    for target_path, expected_source, required in symlinks_to_check:
        # Check if exists
        if not os.path.lexists(target_path):
            if required:
                issues.append('{} does not exist'.format(target_path))
            continue

        # Check if it's a symlink
        if os.path.islink(target_path):
            # Check if broken (symlink exists but target doesn't)
            if not os.path.exists(target_path):
                actual_source = os.readlink(target_path)
                issues.append('{} is a broken symlink (points to {})'.format(
                    target_path, actual_source))
            # Check if readable
            elif not os.access(target_path, os.R_OK):
                issues.append('{} exists but is not readable'.format(target_path))

    return issues


def verify_file_readability():
    """Verify critical files are readable."""
    files_to_check = [
        (os.path.join(BASE_DIR, 'dot.bashrc'), True),  # Required
        (os.path.join(BASE_DIR, 'utils.sh'), True),  # Required
        (os.path.join(BASE_DIR, 'git', 'utils.sh'), True),  # Required
        (os.path.join(BASE_DIR, 'git', 'config'), True),  # Required
    ]

    # Add platform-specific files
    if platform.system() == 'Linux':
        files_to_check.append(
            (os.path.join(BASE_DIR, 'dot.settings_linux'), False)  # Optional
        )
    elif platform.system() == 'Darwin':
        files_to_check.append(
            (os.path.join(BASE_DIR, 'dot.settings_darwin'), False)  # Optional
        )

    issues = []
    for filepath, required in files_to_check:
        if not os.path.exists(filepath):
            if required:
                issues.append('{} is missing'.format(filepath))
        elif not os.access(filepath, os.R_OK):
            issues.append('{} is not readable'.format(filepath))

    return issues


def verify_bash_syntax():
    """Verify bash files have valid syntax using bash -n."""
    if not is_tool('bash'):
        return []  # Can't check without bash

    bash_files = [
        os.path.join(BASE_DIR, 'dot.bashrc'),
        os.path.join(BASE_DIR, 'utils.sh'),
        os.path.join(BASE_DIR, 'git', 'utils.sh'),
    ]

    # Add platform-specific files
    if platform.system() == 'Linux':
        bash_files.append(os.path.join(BASE_DIR, 'dot.settings_linux'))
    elif platform.system() == 'Darwin':
        bash_files.append(os.path.join(BASE_DIR, 'dot.settings_darwin'))

    issues = []
    for filepath in bash_files:
        if not os.path.exists(filepath):
            continue  # Already reported in readability check

        try:
            # Use bash -n to check syntax without executing
            result = subprocess.run(
                ['bash', '-n', filepath],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0:
                # Clean up error message (remove "bash: " prefix if present)
                error_msg = result.stderr.strip()
                if error_msg.startswith('bash: '):
                    error_msg = error_msg[6:]
                issues.append('{} has syntax errors: {}'.format(
                    os.path.basename(filepath), error_msg))
        except subprocess.TimeoutExpired:
            issues.append('{} syntax check timed out'.format(filepath))
        except Exception as e:
            issues.append('{} syntax check failed: {}'.format(filepath, str(e)))

    return issues


def verify_git_config():
    """Verify git configuration is valid."""
    if not is_tool('git'):
        return []  # Can't check without git

    issues = []

    # Check git config file exists
    git_config_path = os.path.join(BASE_DIR, 'git', 'config')
    if not os.path.exists(git_config_path):
        issues.append('git/config file missing')
        return issues

    # Check if included in global config
    try:
        result = subprocess.run(
            ['git', 'config', '--global', '--get', 'include.path'],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            issues.append('git include.path not configured')
        elif git_config_path not in result.stdout:
            issues.append('git include.path not pointing to {}'.format(git_config_path))
    except subprocess.TimeoutExpired:
        issues.append('git config check timed out')
    except Exception as e:
        issues.append('git config check failed: {}'.format(str(e)))

    return issues


def verify_installation():
    """
    Verify installation completed successfully.

    Returns:
        (bool, list): (success, list of issues)
    """
    print_installing_title('Verifying Installation')

    all_issues = []

    # Phase 1: Symlinks
    print('Checking symlinks...')
    issues = verify_symlinks()
    if issues:
        all_issues.extend(issues)
        for issue in issues:
            print_warning(issue)
    else:
        print(colors.OK + '✓ All symlinks valid' + colors.END)

    # Phase 2: File readability
    print('Checking file readability...')
    issues = verify_file_readability()
    if issues:
        all_issues.extend(issues)
        for issue in issues:
            print_error(issue)
    else:
        print(colors.OK + '✓ All files readable' + colors.END)

    # Phase 3: Bash syntax
    print('Checking bash syntax...')
    issues = verify_bash_syntax()
    if issues:
        all_issues.extend(issues)
        for issue in issues:
            print_error(issue)
    else:
        print(colors.OK + '✓ Bash files syntax valid' + colors.END)

    # Phase 4: Git config
    print('Checking git configuration...')
    issues = verify_git_config()
    if issues:
        all_issues.extend(issues)
        for issue in issues:
            print_warning(issue)
    else:
        print(colors.OK + '✓ Git configuration valid' + colors.END)

    # Summary
    if all_issues:
        print('\n' + colors.FAIL + 'Verification found {} issue(s):'.format(len(all_issues)) + colors.END)
        for issue in all_issues:
            print('  - ' + issue)
        return False, all_issues
    else:
        print('\n' + colors.OK + '✓ Installation verification passed!' + colors.END)
        return True, []


def show_setup_summary(results):
    """Display a summary of setup results and provide guidance."""
    print('\n' + '=' * 50)
    print('Setup Summary')
    print('=' * 50)

    status_symbols = {True: '✓', False: '✗', None: '⊘'}
    status_labels = {True: 'SUCCESS', False: 'FAILED', None: 'SKIPPED'}

    for name, result in results.items():
        symbol = status_symbols.get(result, '?')
        label = status_labels.get(result, 'UNKNOWN')
        print('{} {}: {}'.format(symbol, name.capitalize(), label))

    failures = [name for name, result in results.items() if result is False]
    if failures:
        print('\n' + colors.FAIL + 'Action Required:' + colors.END)
        for name in failures:
            if name == 'git':
                print('  - Install git and re-run setup.py')
            elif name == 'mozilla':
                print('  - Check mozilla tools (hg, cargo, etc.) and re-run setup.py --mozilla')
            elif name == 'dev-tools':
                print('  - Check tool installation errors above and re-run setup.py --dev-tools')
                print('    Or install tools manually and run setup.py --dev-tools again')
            else:
                print('  - Fix {} issues above and re-run setup.py'.format(name))
        print('\n' + colors.FAIL + 'Setup completed with errors. Fix the issues above and re-run.' + colors.END)
    else:
        print('\n' + colors.OK + 'All steps completed successfully!' + colors.END)


def main(argv):
    global VERBOSE

    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='Setup dotfiles configuration for bash, git, and optional Mozilla tools',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python3 setup.py                    # Install dotfiles and git config
  python3 setup.py --dry-run          # Show what would be done (no changes made)
  python3 setup.py -v                 # Verbose mode (show detailed operations)
  python3 setup.py --mozilla          # Install all Mozilla tools
  python3 setup.py --mozilla gecko hg # Install specific Mozilla tools
  python3 setup.py --dev-tools        # Install all dev tools (shellcheck, ruff, black, markdownlint)
  python3 setup.py --dev-tools ruff black # Install specific dev tools
  python3 setup.py --dry-run --mozilla --dev-tools # Preview full setup
        '''
    )
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Show detailed operations for debugging')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be done without making any changes')
    parser.add_argument('--mozilla', nargs='*',
                        help='Install Mozilla toolkit for gecko development (gecko, hg, tools, rust)')
    parser.add_argument('--dev-tools', nargs='*',
                        help='Install development tools (shellcheck, ruff, black, markdownlint) and pre-commit hooks')
    args = parser.parse_args(argv[1:])

    # Set global flags
    global VERBOSE, DRY_RUN
    VERBOSE = args.verbose
    DRY_RUN = args.dry_run

    # Show dry-run banner
    if DRY_RUN:
        print_title('DRY-RUN MODE - No changes will be made')
        print(colors.HINT + 'This will show what would be done without making any actual changes.' + colors.END)
        print('')

    print_verbose('Arguments parsed: verbose={}, dry_run={}, mozilla={}, dev_tools={}'.format(
        args.verbose, args.dry_run, args.mozilla, args.dev_tools))
    print_verbose('BASE_DIR: {}'.format(BASE_DIR))
    print_verbose('HOME_DIR: {}'.format(HOME_DIR))

    # Create change tracker for rollback capability
    tracker = ChangeTracker()
    print_verbose('ChangeTracker created')

    results = {
        'dotfiles': dotfiles_link(tracker),
        'bash': bash_link(tracker),
        'git': git_init(tracker),
        'mozilla': mozilla_init(args.mozilla, tracker),
        'dev-tools': dev_tools_init(args.dev_tools, tracker)
    }

    show_setup_summary(results)

    # In dry-run mode, skip verification and show final message
    if DRY_RUN:
        print('')
        print_title('DRY-RUN COMPLETE')
        print(colors.HINT + 'No changes were made to your system.' + colors.END)
        print(colors.OK + 'To actually apply these changes, run without --dry-run flag.' + colors.END)
        return 0

    # Only verify if setup succeeded
    if all(r is not False for r in results.values()):
        # Setup succeeded, run verification
        verification_passed, issues = verify_installation()

        if verification_passed:
            # Both setup and verification successful
            print_hint('Please run `$ source ~/.bashrc` to turn on the environment settings')
            return 0
        else:
            # Setup succeeded but verification failed
            print_error('Installation verification failed!')
            print_error('Fix the issues above and re-run setup.py')

            # Offer rollback for verification failures
            if tracker.has_changes():
                print_warning('Setup made {} change(s) before verification failed'.format(
                    tracker.get_change_count()))
                if get_user_confirmation('Rollback all changes? [y/N]: ', default_non_interactive=False):
                    rollback_changes(tracker)

            return 1
    else:
        # Setup failed
        # Offer rollback
        if tracker.has_changes():
            print_warning('Setup made {} change(s) before failing'.format(
                tracker.get_change_count()))
            if get_user_confirmation('Rollback all changes? [y/N]: ', default_non_interactive=False):
                rollback_changes(tracker)
            else:
                print('Changes kept. You can re-run setup.py after fixing issues.')

        return 1


if __name__ == '__main__':
    try:
        exit_code = main(sys.argv)
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print('abort')
        sys.exit(130)  # Standard exit code for SIGINT
