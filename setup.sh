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

def bash_link():
    for f in FILES:
        if f in SKIP_EXCEPTION and platform.system() not in SKIP_EXCEPTION[f]:
            print 'skip link {}'.format(f)
            continue

        link_name = os.path.join(TARGET_DIR, f[3:]) # Get name after dot
        target_name = os.path.join(BASE_DIR, f)

        if os.path.islink(link_name):
            print 'unlink {}'.format(link_name)
            os.unlink(link_name)

        print 'link {} to {}'.format(link_name, target_name)
        os.symlink(target_name, link_name)

def main(argv):
    bash_link()

if __name__ == '__main__':
    try:
        main(sys.argv)
    except KeyboardInterrupt:
        print 'abort'
