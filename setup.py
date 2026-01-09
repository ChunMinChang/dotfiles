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
        'DOTFILES_GIT_CINNABAR_PRIMARY': os.path.join(HOME_DIR, '.mozbuild', 'git-cinnabar'),
        'DOTFILES_GIT_CINNABAR_FALLBACK': os.path.join(HOME_DIR, 'Work', 'git-cinnabar'),
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


# Symbolically link source to target
def link(source, target):
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

    if os.path.islink(target):
        print_verbose('Target is a symlink, unlinking')
        print('unlink {}'.format(target))
        os.unlink(target)
    else:
        print_verbose('Target is not a symlink or does not exist')

    print('link {} to {}'.format(source, target))
    os.symlink(source, target)
    print_verbose('Symlink created successfully')
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


def append_nonexistent_lines_to_file(file, lines):
    """
    Append lines to a file if they don't already exist.

    Uses line-by-line comparison (not substring matching) to avoid false positives.
    Ensures file ends with newline before appending.
    Validates file is writable before attempting operations.

    Args:
        file: Path to the file to modify
        lines: List of lines to append (without trailing newlines)

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
            with open(file, 'a') as f:
                # Add newline to last line if needed
                if needs_newline:
                    f.write('\n')

                for line in lines_to_append:
                    f.write(line + '\n')
                    print('{} is appended into {}'.format(line, file))

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


# Setup functions
# ------------------------------------------------------------------------------

# Link this dotfiles path to $HOME/.dotfiles
def dotfiles_link():
    print_installing_title('dotfile path')
    print_verbose('dotfiles_link() starting')
    result = link(BASE_DIR, os.path.join(HOME_DIR, '.dotfiles'))
    print_verbose('dotfiles_link() returning: {}'.format(result))
    return result

# Link dot.* to ~/.*
def bash_link():
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
                    target, [bash_load_command(src)])
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
            result = link(src, target)
            if not result:
                errors.append('Failed to link {}'.format(f))

    # Return True only if no errors (skipped files are user choice, not errors)
    success = len(errors) == 0
    print_verbose('bash_link() completed: errors={}, skipped={}'.format(len(errors), len(skipped)))
    print_verbose('bash_link() returning: {}'.format(success))
    return success

# Include git/config from ~/.giconfig
def git_init():
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

    subprocess.call(['git', 'config', '--global', 'include.path', path])

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

def mozilla_init(mozilla_arg):
    """
    Initialize Mozilla development tools.

    Args:
        mozilla_arg: Value from --mozilla argument (None, [], or list of tools)

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
        result = funcs[k]()
        if not result:
            all_succeeded = False

    return all_succeeded


def gecko_init():
    print_installing_title('gecko alias and machrc')
    config = get_config()
    machrc = config['DOTFILES_MACHRC_PATH']
    if os.path.isfile(machrc):
        print_fail(''.join(['{} exists! Abort!\n'.format(machrc),
                            'Apply default settings for now.']))
    else:
        path = os.path.join(BASE_DIR, 'mozilla', 'gecko', 'machrc')
        if not link(path, machrc):
            return False

    bashrc = os.path.join(BASE_DIR, 'dot.bashrc')
    if not os.path.isfile(bashrc):
        print_fail('{} does not exist! Abort!'.format(bashrc))
        return False

    path = os.path.join(BASE_DIR, 'mozilla', 'gecko', 'alias.sh')
    result = append_nonexistent_lines_to_file(bashrc, [bash_load_command(path)])
    return result


def hg_init():
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
    result = append_nonexistent_lines_to_file(hg_config, ['%include ' + path])
    return result


def tools_init():
    print_installing_title('tools settings')

    bashrc = os.path.join(BASE_DIR, 'dot.bashrc')
    if not os.path.isfile(bashrc):
        print_fail('{} does not exist! Abort!'.format(bashrc))
        return False

    path = os.path.join(BASE_DIR, 'mozilla', 'gecko', 'tools.sh')
    result = append_nonexistent_lines_to_file(bashrc, [bash_load_command(path)])
    return result


def rust_init():
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

    result = append_nonexistent_lines_to_file(bashrc, [bash_load_command(cargo_env)])
    return result


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
  python3 setup.py -v                 # Verbose mode (show detailed operations)
  python3 setup.py --mozilla          # Install all Mozilla tools
  python3 setup.py --mozilla gecko hg # Install specific Mozilla tools
  python3 setup.py -v --mozilla       # Verbose + Mozilla tools
        '''
    )
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Show detailed operations for debugging')
    parser.add_argument('--mozilla', nargs='*',
                        help='Install Mozilla toolkit for gecko development (gecko, hg, tools, rust)')
    args = parser.parse_args(argv[1:])

    # Set global verbose flag
    VERBOSE = args.verbose

    print_verbose('Arguments parsed: verbose={}, mozilla={}'.format(args.verbose, args.mozilla))
    print_verbose('BASE_DIR: {}'.format(BASE_DIR))
    print_verbose('HOME_DIR: {}'.format(HOME_DIR))

    results = {
        'dotfiles': dotfiles_link(),
        'bash': bash_link(),
        'git': git_init(),
        'mozilla': mozilla_init(args.mozilla)
    }

    show_setup_summary(results)

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
            return 1
    else:
        # Setup failed, skip verification
        return 1


if __name__ == '__main__':
    try:
        exit_code = main(sys.argv)
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print('abort')
        sys.exit(130)  # Standard exit code for SIGINT
