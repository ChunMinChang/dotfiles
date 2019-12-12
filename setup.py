import argparse
import distutils.spawn
import fileinput
import os
import platform
import re
import sys

# Global variables
# ------------------------------------------------------------------------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
HOME_DIR = os.environ['HOME']

# TODO: Use Print{Error, Hint, Warning} instead
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
    if os.path.islink(target):
        print('unlink {}'.format(target))
        os.unlink(target)

    print('link {} to {}'.format(source, target))
    os.symlink(source, target)

# Check whether `name` is on PATH and marked as executable.
def is_tool(name):
    return distutils.spawn.find_executable(name) is not None

def append_to_next_line_after(name, pattern, value = ''):
    file = fileinput.input(name, inplace = True)
    for line in file:
        replacement = line + ('\n' if '\n' not in line else '') + value
        line = re.sub(pattern, replacement, line)
        sys.stdout.write(line)
    file.close()

def bash_export_command(path):
    return ''.join(['export PATH=', path,':$PATH'])

def bash_load_command(path):
    return ''.join(['[ -r ', path, ' ] && . ', path])

def append_nonexistent_lines_to_file(file, lines):
    with open(file, 'a+') as f:
        content = f.read()
        for l in lines:
            if l in content:
                print('{} is already in {}'.format(l, file))
                continue
            f.write(l + '\n')
            print('{} is appended into {}'.format(l, file))
        f.close()

def add_nonexistent_line_under_topic(file, topic, line):
    with open(file, 'a+') as f:
        content = f.read()
        if '[' + topic + ']' not in content:
            f.write('[' + topic + ']\n')
        elif line in content:
            f.close()
            return False
        f.close()

    append_to_next_line_after(file, '\[' + topic + '\]', line)
    return True

def print_installing_title(name, bold=False):
    print(colors.HEADER + ''.join(['\n', name,
        ('\n==============================' if bold
         else '\n--------------------')]) + colors.END)

# TODO: Use Print{Error, Hint, Warning} instead
def print_hint(message):
    print(colors.HINT + message + colors.END)

def print_warning(message):
    print(colors.WARNING + 'WARNING: ' + message + colors.END)

def print_fail(message):
    print(colors.FAIL + 'ERROR: ' + message + colors.END)

# Setup functions
# ------------------------------------------------------------------------------
# Link this dotfiles path to $HOME/.dotfiles
def dotfiles_link():
    print_installing_title('dotfile path')
    link(BASE_DIR, HOME_DIR + '/.dotfiles')

# Link dot.* to ~/.*
def bash_link():
    print_installing_title('bash startup scripts')
    platform_files = {
        'Darwin': [
            'dot.bashrc',
            'dot.zshrc',
            'dot.bashrc_darwin'
        ],
        'Linux': [
            'dot.bashrc',
            'dot.bashrc_linux'
        ],
    }

    #files = filter(lambda f: f.startswith('dot.'), os.listdir(BASE_DIR))
    files = platform_files[platform.system()];
    for f in files:
        target = os.path.join(HOME_DIR, f[3:]) # Get name after dot
        src = os.path.join(BASE_DIR, f)
        if os.path.isfile(target):
            if os.path.samefile(src, target):
                print_warning('{} is already linked!'.format(target));
                continue
            print_warning('{} already exists!'.format(target));
            if f is 'dot.bashrc':
                print('Append a command to load {} in {}'.format(src, target))
                append_nonexistent_lines_to_file(target, [bash_load_command(src)])
        else:
            link(src, target)

# Include git/config from ~/.giconfig
def git_init():
    print_installing_title('git settings')
    if not is_tool('git'):
        print_fail('Please install git first!')
        return

    git_config = HOME_DIR + '/.gitconfig'
    if not os.path.isfile(git_config):
        print_warning('{} does not exist! Create a new one!'.format(git_config))
        with open(git_config, 'w'): pass

    path = BASE_DIR + '/git/config'

    if add_nonexistent_line_under_topic(git_config, 'include', '\tpath = ' + path):
        print('{} is included in {}'.format(path, git_config))
    else:
        print_hint('{} is already included!'.format(path))

# mozilla stuff
# ---------------------------------------
def mozilla_init():
    print_installing_title('mozilla settings', True)
    parser = argparse.ArgumentParser()
    parser.add_argument('--mozilla', nargs = '*',
                        help = 'Installing the toolkit for developing gecko')
    args = parser.parse_args()

    if args.mozilla is None:
        print_warning('Skip installing mozilla toolkit')
        return

    funcs = {
      'gecko': gecko_init,
      'hg': hg_init,
      'tools': tools_init,
      'rust': rust_init,
    }

    options = (set(funcs.keys()).intersection(set(args.mozilla)) if args.mozilla
               else funcs.keys())
    for k in options:
        funcs[k]()

def gecko_init():
    print_installing_title('gecko alias and machrc')
    machrc = HOME_DIR + '/.mozbuild/machrc'
    if os.path.isfile(machrc):
        print_fail(''.join(['{} exists! Abort!'.format(machrc),
                            '\tApply default settings for now.\n']))
    else:
        path = BASE_DIR + '/mozilla/gecko/machrc'
        link(path, machrc)

    bashrc = HOME_DIR + '/.bashrc'
    if not os.path.isfile(bashrc):
        print_fail('{} does not exist! Abort!'.format(bashrc))
        return

    path = BASE_DIR + '/mozilla/gecko/alias.sh'
    append_nonexistent_lines_to_file(bashrc, [bash_load_command(path)])

def hg_init():
    print_installing_title('hg settings')
    error_messages = ['\tRun ./mach bootstrap.py under gecko-dev to fix it.\n']

    if not is_tool('hg'):
        error_messages.insert(0, 'Please install hg(mercurial) first!\n');
        print_fail(''.join(error_messages))
        return

    hg_config = HOME_DIR + '/.hgrc'
    if not os.path.isfile(hg_config):
        error_messages.insert(0, '{} does not exist! Abort!\n'.format(hg_config));
        print_fail(''.join(error_messages))
        return

    path = BASE_DIR + '/mozilla/hg/config'
    append_nonexistent_lines_to_file(hg_config, ['%include ' + path])

def tools_init():
    print_installing_title('tools settings')

    bashrc = HOME_DIR + '/.bashrc'
    if not os.path.isfile(bashrc):
        print_fail('{} does not exist! Abort!'.format(bashrc))
        return

    path = BASE_DIR + '/mozilla/gecko/tools.sh'
    append_nonexistent_lines_to_file(bashrc, [bash_load_command(path)])

def rust_init():
    print_installing_title('rust settings')
    error_messages = ['\tRun ./mach bootstrap.py under gecko-dev to fix it.\n']

    bashrc = HOME_DIR + '/.bashrc'
    if not os.path.isfile(bashrc):
        print_fail('{} does not exist! Abort!'.format(bashrc))
        return

    cargo_env = HOME_DIR + '/.cargo/env'
    if not os.path.isfile(cargo_env):
        error_messages.insert(0, '{} does not exist! Abort!'.format(cargo_env));
        print_fail(''.join(error_messages))
        return

    append_nonexistent_lines_to_file(bashrc, [bash_load_command(cargo_env)])

def main(argv):
    dotfiles_link()
    bash_link()
    git_init()

    # Install by --mozilla
    mozilla_init()

if __name__ == '__main__':
    try:
        main(sys.argv)
    except KeyboardInterrupt:
        print('abort')
