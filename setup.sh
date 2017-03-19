#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: set sw=4 ts=4 sts=4 et fileencoding=utf-8 :

import os
import sys
import platform
import fileinput
import re
from distutils.spawn import find_executable

# Global variables
# ------------------------------------------------------------------------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
TARGET_DIR = os.environ['HOME']

# Utils
# ------------------------------------------------------------------------------
# Symbolically link source to target
def link(source, target):
    if os.path.islink(target):
        print 'unlink {}'.format(target)
        os.unlink(target)

    print 'link {} to {}'.format(source, target)
    os.symlink(source, target)

# Check whether `name` is on PATH and marked as executable.
def is_tool(name):
    return find_executable(name) is not None

def append_to_next_line_after(name, pattern, value = ""):
    file = fileinput.input(name, inplace = True)
    for line in file:
        replacement = line + ('\n' if '\n' not in line else '') + value
        line = re.sub(pattern, replacement, line)
        sys.stdout.write(line)
    file.close()

# Setup functions
# ------------------------------------------------------------------------------
# Link this dotfiles path to $HOME/.dotfiles
def dotfiles_link():
    link(BASE_DIR, TARGET_DIR + '/.dotfiles')

# Link dot.* to ~/.*
def bash_link():
    files_only_for = {
      'dot.bash_profile': ['Darwin'], # dot.bash_profile is only for OS X
    }

    files = filter(lambda f: f.startswith('dot.'), os.listdir(BASE_DIR))

    for f in files:
        if f in files_only_for and platform.system() not in files_only_for[f]:
            print 'skip link {}'.format(f)
            continue

        target = os.path.join(TARGET_DIR, f[3:]) # Get name after dot
        src = os.path.join(BASE_DIR, f)
        link(src, target)

# Include git/config from ~/.giconfig
def git_init():
    if not is_tool('git'):
        print 'Please install git first!'
        return

    cfg = TARGET_DIR + '/.gitconfig'

    if not os.path.isfile(cfg):
        print 'No {} exist! Abort!'.format(cfg)
        return

    path = BASE_DIR + '/git/config'

    with open(cfg, 'r+a') as f:
        content = f.read()
        if '[include]' not in content:
            f.write('[include]')
        elif path in content:
            print '{} is already included!'.format(path)
            f.close()
            return
        f.close()

    print 'Include {} from {}'.format(path, cfg)
    append_to_next_line_after(cfg, '\[include\]', '\tpath = ' + path)

def main(argv):
    dotfiles_link()
    bash_link()
    git_init()

if __name__ == '__main__':
    try:
        main(sys.argv)
    except KeyboardInterrupt:
        print 'abort'
