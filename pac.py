#!/usr/bin/env python

"""Pac

Python wrapper around Arch Linux pacman which
stores state in git, and allows for gitlike
manipulation of pacman state.
    
Usage:
  pac.py man [<pacmanargs>...]
  pac.py add
  pac.py commit
  pac.py apply <gitrevno>
  pac.py [-c] <command> [<args>...]

"""

import subprocess
import os, sys, shutil

PAC_GIT_REPO = os.environ.get("PAC_GIT_REPO")
if PAC_GIT_REPO is None:
    for loc in os.curdir, os.path.expanduser("~/.config/pac"), "/etc/pac", os.environ.get("PAC_CONF"):
        if loc is not None and os.path.isfile(os.path.join(loc, "pac.conf")):
            with open(os.path.join(loc,"pac.conf")) as f:
                for line in f:
                    s = line.strip().split("=")
                    if s[0] == "PAC_GIT_REPO" and len(s) >= 2:
                        PAC_GIT_REPO = s[1]
        if PAC_GIT_REPO is not None:
            break

if PAC_GIT_REPO is None:
    print("Please define PAC_GIT_REPO")
    exit(1)

if os.path.exists(PAC_GIT_REPO) == False:
    os.mkdir(PAC_GIT_REPO)

"""Construct and return package dictionary from current
system pacman installed state
"""
def snapshot():
    packages = pacman_check_output(False, "-Q").decode("utf-8").strip().split("\n")
    explicit = pacman_check_output(False, "-Qe").decode("utf-8").strip().split("\n")
    out = {}
    for line in packages:
        name, version = line.split()
        out[name] = {"version": version, "explicit": ("{} {}".format(name, version) in explicit)};
    return out

"""Construct and return package dictionary from state file
current working directory of the git repository
"""
def deserialize():
    import json
    try:
        with open(os.path.join(PAC_GIT_REPO, 'package_state.json'), 'r') as fp:
            s = json.load(fp)
    except FileNotFoundError:
        return {}
    return s

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
    if git("symbolic-ref", "HEAD", stdout=subprocess.DEVNULL) == 128:
        # get 'current' commit hash
        head = git_check_output("rev-parse", "HEAD").strip()
    else:
        # attached head, get current branch
        head = git_check_output("rev-parse", "--symbolic-full-name", "--abbrev-ref", "HEAD").strip()

    git_check_call('checkout', gitrevno, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    rv = deserialize()
    git_check_call('checkout', head, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return rv

"""Find the package names and versions to
append to the pacman -S command, and those to
append to the pacman -R command.

Return a three-tuple of:
(to install explicitly, to install as deps, to remove)
"""
def get_pacman_args(prev, curr):
    installing_explicit = {}
    installing_implicit = {}
    removing = {}
    for key in prev.keys():
        if curr.get(key) is None:
            # removed package
            removing[key] = prev.get(key)
    for key in curr.keys():
        if prev.get(key) is None or prev.get(key) != curr.get(key):
            # new package, or change version
            if curr[key]["explicit"]:
                installing_explicit[key] = curr.get(key)
            else:
                installing_implicit[key] = curr.get(key)
            
    return installing_explicit, installing_implicit, removing

"""Invoke git in the directory PAC_GIT_REPO with the
given args, kwargs, using the command specified by cmd

cmd should be one of:
 subprocess.call
 subprocess.check_call
 subprocess.check_output

return the value returned by cmd
"""
def _git(cmd, *args, **kwargs):
    args = ["git"] + list(args)
    return cmd(args, **kwargs)

"""Invoke git as a subprocess, return its returncode"""
def git(*args, **kwargs):
    return _git(subprocess.call, *args, **kwargs)

"""Invoke git as a subprocess, return stdout, raise
Exception if non-zero return status"""
def git_check_output(*args, **kwargs):
    return _git(subprocess.check_output, *args, **kwargs)

"""Invoke git as a subprocess, return return code, raise
Exception if non-zero return status"""
def git_check_call(*args, **kwargs):
    return _git(subprocess.check_call, *args, **kwargs)

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

def pacman_check_output(sudo, *args, **kwargs):
    args = [subprocess.check_output, sudo] + list(args)
    return _pacman(*args, **kwargs)

def _call(args, cmd=subprocess.call):
    if (shutil.which(args[0])):
        rv = cmd(args)
    else:
        print("command {} not found".format(args[0]))
        rv = 1
    return rv

if __name__ == '__main__':

    # execute commands in git repo
    os.chdir(PAC_GIT_REPO)

    if (len(sys.argv) == 1 or sys.argv[1] in ['--help', '-help', 'help']):
        print(__doc__, end="")
        rv = 1
    elif sys.argv[1] == 'add':
        serialize(snapshot())
        rv = git('add', 'package_state.json')
    elif sys.argv[1] == 'commit':
        rv = git(*sys.argv[1:])
    elif sys.argv[1] == 'apply':
        # Check for uncommitted changes
        if (git("diff-index", "--quiet", "--cached", "HEAD") != 0):
            print("uncommitted changes - not proceeding")
            exit(1)
        if len(sys.argv) <= 2:
            new_packages = deserialize()
        else:
            new_packages = get_revision(sys.argv[2])

        installing_explicit, installing_implicit, removing = get_pacman_args(snapshot(), new_packages)

        installing_explicit = ["{}={}".format(key, installing_explicit[key]["version"]) for key in installing_explicit.keys()]
        installing_implicit = ["{}={}".format(key, installing_implicit[key]["version"]) for key in installing_implicit.keys()]
        removing = list(removing.keys())

        if installing_explicit == [] and installing_implicit == [] and removing == []:
            print("no changes in packages detected")
            rv = 0
        else:
            cmdline_explicit = ["pacman", "-Sd", "--asexplicit"] + installing_explicit
            cmdline_implicit = ["pacman", "-Sd", "--asdeps"] + installing_implicit
            cmdline_remove = ["pacman", "-Rd"] + removing

            if installing_explicit != []:
                print(" ".join(cmdline_explicit))
            if installing_implicit != []:
                print(" ".join(cmdline_implicit))
            if removing != []:
                print(" ".join(cmdline_remove))

            if (input("Continue? Y/n") in ['y', 'Y', '']):
                rv = (installing_explicit != [] and _call(cmdline_explicit)) or \
                     (installing_implicit != [] and _call(cmdline_implicit)) or \
                     (removing != [] and _call(cmdline_remove))
            else:
                rv = 1
    elif sys.argv[1] == 'man':
        # syntax sugar for pacman + commit
        rv = _call(["pacman"] + sys.argv[2:])
        serialize(snapshot())
        rv = git('add', 'package_state.json')
        rv = git('commit')
    elif sys.argv[1] == '-c':
        # accessibility for 'man' command
        rv = _call(sys.argv[2:])
    else:
        rv = _call(sys.argv[1:])

    exit(rv)
