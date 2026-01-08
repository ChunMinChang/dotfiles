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

# Symbolically link source to target
def link(source, target):
    # Validate source exists before creating symlink
    if not os.path.exists(source):
        print_error('Cannot create symlink: source does not exist')
        print_error('Source: {}'.format(source))
        return False

    if os.path.islink(target):
        print('unlink {}'.format(target))
        os.unlink(target)

    print('link {} to {}'.format(source, target))
    os.symlink(source, target)
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

# Setup functions
# ------------------------------------------------------------------------------

# Link this dotfiles path to $HOME/.dotfiles
def dotfiles_link():
    print_installing_title('dotfile path')
    result = link(BASE_DIR, os.path.join(HOME_DIR, '.dotfiles'))
    return result

# Link dot.* to ~/.*
def bash_link():
    print_installing_title('bash startup scripts')
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
    errors = []
    skipped = []

    for f in files:
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
    return len(errors) == 0

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

def mozilla_init():
    print_installing_title('mozilla settings', True)
    parser = argparse.ArgumentParser()
    parser.add_argument('--mozilla', nargs='*',
                        help='Installing the toolkit for developing gecko')
    args = parser.parse_args()

    if args.mozilla is None:
        print_warning('Skip installing mozilla toolkit')
        return None  # None = skipped, not failure

    funcs = {
        'gecko': gecko_init,
        'hg': hg_init,
        'tools': tools_init,
        'rust': rust_init,
    }

    options = (set(funcs.keys()).intersection(set(args.mozilla)) if args.mozilla
               else funcs.keys())

    all_succeeded = True
    for k in options:
        result = funcs[k]()
        if not result:
            all_succeeded = False

    return all_succeeded


def gecko_init():
    print_installing_title('gecko alias and machrc')
    machrc = os.path.join(HOME_DIR, '.mozbuild', 'machrc')
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

    cargo_env = os.path.join(HOME_DIR, '.cargo', 'env')
    if not os.path.isfile(cargo_env):
        error_messages.insert(0, '{} does not exist! Abort!'.format(cargo_env))
        print_fail(''.join(error_messages))
        return False

    result = append_nonexistent_lines_to_file(bashrc, [bash_load_command(cargo_env)])
    return result


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
    results = {
        'dotfiles': dotfiles_link(),
        'bash': bash_link(),
        'git': git_init(),
        'mozilla': mozilla_init()
    }

    show_setup_summary(results)

    # Return proper exit code
    if all(r is not False for r in results.values()):
        # Success if all True or None (skipped)
        print_hint('Please run `$ source ~/.bashrc` to turn on the environment settings')
        return 0
    else:
        # Failure if any False
        return 1


if __name__ == '__main__':
    try:
        exit_code = main(sys.argv)
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print('abort')
        sys.exit(130)  # Standard exit code for SIGINT
