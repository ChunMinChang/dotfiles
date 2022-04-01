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

# Check if `name` exists
def is_tool(name):
    cmd = "where" if platform.system() == "Windows" else "which"
    try:
        r = subprocess.check_output([cmd, name])
        print('{} is found in {}'.format(name, r.decode("utf-8")))
        return True
    except:
        return False

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
    with open(file, 'r+') as f:
        content = f.read()
        for l in lines:
            if l in content:
                print_warning('{} is already in {}'.format(l, file))
                continue
            f.write(l + '\n')
            print('{} is appended into {}'.format(l, file))

        # Show the current file
        f.seek(0)
        content = f.read()
        print_hint('{}:'.format(file))
        print(content)
        f.close()

def print_installing_title(name, bold=False):
    print(colors.HEADER + ''.join(['\n', name,
        ('\n==============================' if bold
         else '\n--------------------')]) + colors.END)

# TODO: Use Print{Error, Hint, Warning} instead
def print_hint(message):
    print(colors.HINT + message + colors.END + '\n')

def print_warning(message):
    print(colors.WARNING + 'WARNING: ' + message + colors.END + '\n')

def print_fail(message):
    print(colors.FAIL + 'ERROR: ' + message + colors.END + '\n')

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
            'dot.settings_darwin'
        ],
        'Linux': [
            'dot.bashrc',
            'dot.settings_linux'
        ],
    }

    if any(platform.mac_ver()):
        v, _, _ = platform.mac_ver()
        v = float('.'.join(v.split('.')[:2]))
        platform_files[platform.system()].append(
            'dot.zshrc' if v >= 10.15 else 'dot.bash_profile')

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
            if f == 'dot.bashrc':
                print('Append a command to load {} in {}'.format(src, target))
                append_nonexistent_lines_to_file(target, [bash_load_command(src)])
            else:
                print_warning('Do nothing.')
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
        print_warning('{} does not exist! Create a new one with default settings!'.format(git_config))
        # Set global user name and email
        subprocess.call(['git', 'config', '--global', 'user.name', 'Chun-Min Chang'])
        subprocess.call(['git', 'config', '--global', 'user.email', 'chun.m.chang@gmail.com'])

    # Include git config here in global gitconfig file
    path = BASE_DIR + '/git/config'
    subprocess.call(['git', 'config', '--global', 'include.path', path])

    # Show the current file:
    with open(git_config, 'r') as f:
        content = f.read()
        print_hint('{}:'.format(git_config))
        print(content)
        f.close()

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
        print_fail(''.join(['{} exists! Abort!\n'.format(machrc),
                            'Apply default settings for now.']))
    else:
        path = BASE_DIR + '/mozilla/gecko/machrc'
        link(path, machrc)

    bashrc = BASE_DIR + '/dot.bashrc'
    if not os.path.isfile(bashrc):
        print_fail('{} does not exist! Abort!'.format(bashrc))
        return

    path = BASE_DIR + '/mozilla/gecko/alias.sh'
    append_nonexistent_lines_to_file(bashrc, [bash_load_command(path)])

def hg_init():
    print_installing_title('hg settings')
    error_messages = ['\tRun ./mach bootstrap.py under gecko-dev to fix it.']

    if not is_tool('hg'):
        error_messages.insert(0, 'Please install hg(mercurial) first!');
        print_fail(''.join(error_messages))
        return

    hg_config = HOME_DIR + '/.hgrc'
    if not os.path.isfile(hg_config):
        error_messages.insert(0, '{} does not exist! Abort!'.format(hg_config));
        print_fail(''.join(error_messages))
        return

    path = BASE_DIR + '/mozilla/hg/config'
    append_nonexistent_lines_to_file(hg_config, ['%include ' + path])

def tools_init():
    print_installing_title('tools settings')

    bashrc = BASE_DIR + '/dot.bashrc'
    if not os.path.isfile(bashrc):
        print_fail('{} does not exist! Abort!'.format(bashrc))
        return

    path = BASE_DIR + '/mozilla/gecko/tools.sh'
    append_nonexistent_lines_to_file(bashrc, [bash_load_command(path)])

def rust_init():
    print_installing_title('rust settings')
    error_messages = ['\tRun ./mach bootstrap.py under gecko-dev to fix it.']

    bashrc = BASE_DIR + '/dot.bashrc'
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

    print_hint('Please run `$ source ~/.bachrc` turn on the environment settings')

if __name__ == '__main__':
    try:
        main(sys.argv)
    except KeyboardInterrupt:
        print('abort')
