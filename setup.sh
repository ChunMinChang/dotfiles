#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: set sw=4 ts=4 sts=4 et fileencoding=utf-8 :

import os
import sys
import platform

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
TARGET_DIR = os.environ['HOME']

FILES = filter(lambda f: f.startswith('dot.'), os.listdir(BASE_DIR))

SKIP_EXCEPTION = {
  'dot.bash_profile': ['Darwin'], # dot.bash_profile is only for OS X
}

def link(source, target):
    if os.path.islink(target):
        print 'unlink {}'.format(target)
        os.unlink(target)

    print 'link {} to {}'.format(source, target)
    os.symlink(source, target)

# Link this dotfiles path to $HOME/.dotfiles
def dotfiles_link():
    link(BASE_DIR, TARGET_DIR + '/.dotfiles')

def bash_link():
    for f in FILES:
        if f in SKIP_EXCEPTION and platform.system() not in SKIP_EXCEPTION[f]:
            print 'skip link {}'.format(f)
            continue

        target = os.path.join(TARGET_DIR, f[3:]) # Get name after dot
        src = os.path.join(BASE_DIR, f)
        link(src, target)

def main(argv):
    dotfiles_link()
    bash_link()

if __name__ == '__main__':
    try:
        main(sys.argv)
    except KeyboardInterrupt:
        print 'abort'
