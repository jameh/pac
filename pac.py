#!/usr/bin/env python

"""Pac

Python wrapper around Arch Linux pacman which
stores state in git, and allows for gitlike
manipulation of pacman state.
    
Usage:
  pac.py git <gitargs>...
  pac.py man <pacmanargs>...
  pac.py stage
  pac.py commit
  pac.py apply <gitrevno>

"""

import subprocess
import os, sys

PAC_GIT_REPO = os.environ.get("PAC_GIT_REPO")

def snapshot():
    s = subprocess.check_output(["pacman", "-Q"]).decode("utf-8")
    out = {}
    for line in s.strip().split("\n"):
        tokens = line.split()
        # package name: package version
        out[tokens[0]] = tokens[1];
    return out

def deserialize():
    import json
    try:
        with open(os.path.join(PAC_GIT_REPO, 'package_state.json'), 'r') as fp:
            return json.load(fp)
    except FileNotFoundError:
        return {}

def serialize(obj):
    import json
    with open(os.path.join(PAC_GIT_REPO, 'package_state.json'), 'w') as fp:
        json.dump(obj, fp, indent=2)

def get_revision(gitrevno):
    head = git('rev-parse', 'HEAD', check_output=True).strip()
    git('checkout', gitrevno)
    rv = deserialize()
    git('checkout', head)
    return rv


def get_diff(prev, curr):
    removed = {}
    added = {}
    version_changed = {}
    no_change = {}

    for key in set(prev.keys()).union(set(curr.keys())):
        if curr.get(key) is None:
            removed[key] = prev[key]
        elif prev.get(key) is None:
            added[key] = curr[key]
        elif curr.get(key) == prev.get(key):
            no_change[key] = prev[key]
        else:
            version_changed[key] = {"old": prev.get(key), "new": curr.get(key)}
    return added, removed, version_changed, no_change

def git(*args, check_output=False):
    cwd = os.getcwd()
    os.chdir(PAC_GIT_REPO)
    if (check_output):
        rv = subprocess.check_output(["git"] + list(args))
        return rv
    else:
        rv = subprocess.call(["git"] + list(args))
        os.chdir(cwd)
        if (rv != 0):
            exit(rv)

def pacman(*args):
    rv = subprocess.call(["sudo", "pacman"] + list(args))
    if (rv != 0):
        exit(rv)
    serialize(snapshot())
    git('add', 'package_state.json')
    git('commit')


if __name__ == '__main__':

    if PAC_GIT_REPO is None:
        print("Please set environment variable PAC_GIT_REPO")
        exit(1)

    from docopt import docopt
    args = docopt(__doc__, options_first=True)
    if args['git']:
        # forward command to git repo
        git(*args['<gitargs>'])
    elif args['man']:
        pacman(*args['<pacmanargs>'])
    elif args['stage']:
        # write to git repo working directory
        serialize(snapshot())
        git('status')
    elif args['commit']:
        # We add and commit the state file
        git('add', 'package_state.json')
        git('commit')
    elif args['apply']:
        # Check for uncommitted changes
        snap = snapshot()
        added, removed, version_changed, no_change = get_diff(deserialize(), snap)

        if (added != {} or removed != {} or version_changed != {}):
            print("uncommitted changes - not proceeding")
            exit(1)

        added, removed, version_changed, no_change = get_diff(snap, get_revision(args['<gitrevno>']))
        if (version_changed != {}):
            # check pacman cache
            print("we're not time-travellers...yet")
            exit(1)

        pacman_args = ['-S'] + list(added.keys()) + ['-R'] + list(removed.keys())
        pacman(*pacman_args)

    exit(0)
