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

"""Construct and return package dictionary from current
system pacman installed state
"""
def snapshot():
    s = pacman_check_output(False, "-Q").decode("utf-8")
    out = {}
    for line in s.strip().split("\n"):
        tokens = line.split()
        # package name: package version
        out[tokens[0]] = tokens[1];
    return out

"""Construct and return package dictionary from state file
current working directory of the git repository
"""
def deserialize():
    import json
    try:
        with open(os.path.join(PAC_GIT_REPO, 'package_state.json'), 'r') as fp:
            return json.load(fp)
    except FileNotFoundError:
        return {}

"""Serialize package dictionary obj and dump it 
to the state file in git repository
"""
def serialize(obj):
    import json
    with open(os.path.join(PAC_GIT_REPO, 'package_state.json'), 'w') as fp:
        json.dump(obj, fp, indent=2)
    return 0

"""Get the package dictionary for the given git revision"""
def get_revision(gitrevno):
    head = git('rev-parse', 'HEAD', check_output=True).strip()
    git('checkout', gitrevno)
    rv = deserialize()
    git('checkout', head)
    return rv


def get_pacman_args(prev, curr):
    installing = {}
    removing = {}
    for key in prev.keys():
        if curr.get(key) is None:
            # removed package
            removing[key] = prev.get(key)
    for key in curr.keys():
        if prev.get(key) is None or prev.get(key) != curr.get(key):
            # new package, or change version
            installing[key] = curr.get(key)
    return ["-S"] + ["{}={}".format(key, installing[key]) for key in installing.keys()] + \
        ["-R"] + [key for key in removing.keys()]


"""Partition the union of the package dicts prev, curr

Separate into dictionaries for the following categories:
(a) in curr, not in prev
(b) in prev, not in curr
(c) in both, with different versions
(d) in both, with same versions
"""
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

"""Invoke git in the directory PAC_GIT_REPO with the
given args, kwargs, using the command specified by cmd

cmd should be one of:
 subprocess.call
 subprocess.check_call
 subprocess.check_output

return the value returned by cmd
"""
def _git(cmd, *args, **kwargs):
    cwd = os.getcwd()
    os.chdir(PAC_GIT_REPO)
    args = ["git"] + list(args)
    rv = cmd(args, **kwargs)
    os.chdir(cwd)
    return rv

"""Invoke git as a subprocess, return its returncode"""
def git(*args, **kwargs):
    return _git(subprocess.call, *args, **kwargs)

"""Invoke git as a subprocess, return stdout, raise
Exception if non-zero return status"""
def git_check_output(*args, **kwargs):
    return _git(subprocess.check_output, *args, **kwargs)

"""Invoke pacman using the command specified
by cmd, with sudo if sudo is True.

cmd should be one of:
 subprocess.call
 subprocess.check_call
 subprocess.check_output

return the value returned by cmd
"""
def _pacman(cmd, sudo, *args, **kwargs):
    if sudo:
        args = ["sudo", "pacman"] + list(args)
    else:
        args = ["pacman"] + list(args)

    return cmd(args, **kwargs)

"""Invoke pacman as a subprocess, return its
returncode
"""
def pacman(sudo, *args, **kwargs):
    args = [subprocess.call, sudo] + list(args)
    return _pacman(*args, **kwargs)

if __name__ == '__main__':

    if PAC_GIT_REPO is None:
        print("Please set environment variable PAC_GIT_REPO")
        exit(1)

    from docopt import docopt
    args = docopt(__doc__, options_first=True)
    if args['git']:
        # forward command to git repo
        rv = git(*args['<gitargs>'])
    elif args['man']:
        # forward command to pacman
        rv = pacman(False, *args['<pacmanargs>'])
    elif args['stage']:
        # write to git repo working directory
        serialize(snapshot()) 
        rv = git('status')
    elif args['commit']:
        # We add and commit the state file
        rv = git('add', 'package_state.json') and git('commit')
    elif args['apply']:
        # Check for uncommitted changes
        if (git("diff-index", "--quiet", "--cached", "HEAD") != 0):
            print("uncommitted changes - not proceeding")
            exit(1)

        rv = pacman(True, *get_pacman_args())
    else:
        rv = 1
    exit(rv)
