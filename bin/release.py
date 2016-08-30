# -*- coding: utf-8 -*-
"""
    release
    ~~~~~~~

    Helper script that performs a release.  Does pretty much everything
    automatically for us.

    :copyright: (c) 2014 by the J5.
    :license: BSD, see LICENSE for more details.

    :copyright: (c) 2014 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
import pkg_resources
import sys
import os
import re
from datetime import datetime, date
from subprocess import Popen, PIPE

_date_clean_re = re.compile(r'(\d+)(st|nd|rd|th)')


def parse_changelog():
    with open('CHANGES') as f:
        lineiter = iter(f)
        for line in lineiter:
            match = re.search('^Version\s+(.*)', line.strip())

            if match is None:
                continue

            version = match.group(1).strip()
            if lineiter.next().count('-') != len(match.group(0)):
                continue

            while True:
                change_info = lineiter.next().strip()
                if change_info:
                    break

            match = re.search(r'released on (.*)', change_info)
            if match is None:
                continue

            datestr = match.groups()[0]
            return version, parse_date(datestr)


def parse_date(string):
    string = _date_clean_re.sub(r'\1', string)
    return datetime.strptime(string, '%B %d %Y')


def bump_version(version):
    try:
        parts = map(int, version.split('.'))
    except ValueError:
        fail('Current version is not numeric')
    parts[-1] += 1
    return '.'.join(map(str, parts))


def set_filename_version(filename, version_number, pattern):
    changed = []

    def inject_version(match):
        before, old, after = match.groups()
        changed.append(True)
        return before + version_number + after
    with open(filename) as f:
        contents = re.sub(r"^(\s*%s\s*=\s*')(.+?)(')(?sm)" % pattern,
                          inject_version, f.read())

    if not changed:
        fail('Could not find %s in %s', pattern, filename)

    with open(filename, 'w') as f:
        f.write(contents)


def set_init_version(version):
    info('Setting __init__.py version to %s', version)
    set_filename_version('zask/__init__.py', version, '__version__')


def set_setup_version(version):
    info('Setting setup.py version to %s', version)
    set_filename_version('setup.py', version, 'version')


def build_and_upload():
    Popen([sys.executable, 'setup.py', 'sdist', 'upload', '-r', 'pypi']).wait()


def fail(message, *args):
    print >> sys.stderr, 'Error:', message % args
    sys.exit(1)


def info(message, *args):
    print >> sys.stderr, message % args


def get_git_tags():
    return set(Popen(['git', 'tag'], stdout=PIPE).communicate()[
               0].splitlines())


def git_is_clean():
    return Popen(['git', 'diff', '--quiet']).wait() == 0


def make_git_commit(message, *args):
    message = message % args
    Popen(['git', 'commit', '-am', message]).wait()


def make_git_tag(tag):
    info('Tagging "%s"', tag)
    Popen(['git', 'tag', tag]).wait()


def main():
    os.chdir(os.path.join(os.path.dirname(__file__), '..'))

    version, release_date = parse_changelog()
    dev_version = bump_version(version) + '-dev'

    info('Releasing %s, release date %s',
         version, release_date.strftime('%d/%m/%Y'))
    tags = get_git_tags()

    if version in tags:
        fail('Version "%s" is already tagged', version)

    if release_date.date() != date.today():
        fail('Release date is not today (%s != %s)',
             release_date.date(), date.today())

    if not git_is_clean():
        fail('You have uncommitted changes in git')

    set_init_version(version)
    make_git_commit('Bump version number to %s', version)
    make_git_tag(version)
    build_and_upload()
    set_init_version(dev_version)


if __name__ == '__main__':
    main()
