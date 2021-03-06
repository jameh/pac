# Pac

This is a wrapper around both git and Arch Linux's pacman to track and manipulate the state of packages installed on the system.

## Requirements

Currently, only Python 3 is supported. You also need git and pacman installed to your PATH.

## Installation

```
$ mkdir -p ~/code
$ cd ~/code
$ git clone https://github.com/jameh/pac.git
$ mkdir -p ~/.config/pac/git_repo
# mkdir -p /etc/pac/git_repo
# echo "PAC_GIT_REPO=/home/jamie/.config/pac/git_repo" > /etc/pac/pac.conf
# ln -s /home/jamie/code/pac/pac.py /usr/local/bin/pac
# chmod +x /usr/local/bin/pac
```

## Usage
pac will execute any commands you want in the `PAC_GIT_REPO` directory.
The following are equivalent:

```
pac man -Syu # syntax sugar
(pac pacman -Syu; git add package_list.json; git commit)
(pac -c pacman -Syu; cd $PAC_GIT_REPO; git add package_list.json; git commit)
(cd $PAC_GIT_REPO; pacman -Syu; git add package_list.json; git commit)
```

You can also perform any other commands in your PATH:

```
pac ls
pac git status
```

Finally, we have the pac-specific commands: `add`, `commit`, `apply`:

### `add`

This will save your system state in JSON format to `$PAC_GIT_REPO/package_state.json` and `git add` the changes.

```
pac add
```

### `commit`

This is simply a shortcut to `git commit`. The following are equivalent:

```
pac commit
pac git commit
(cd $PAC_GIT_REPO; git commit)
```

### `apply [<gitrevno>]`

This will temporarily checkout the git commit hash or branch name `gitrevno`, 
read the state from the `package_state.json` file, perform a diff on the current
system state and the committed state, and prompt for confirmation to pacman
commandlines which will restore the committed state to the system.
If `gitrevno` is omitted, it simply looks at HEAD for the new state.

```
pac apply HEAD~1
```

## Full Example

This is an example of uninstalling and reinstalling slim.

```
$ sudo pac man -S slim
...
$ pac git init
/home/jamie/.config/pac/git_repo
Initialized empty Git repository in /home/jamie/.config/pac/git_repo/.git/
$ pac add
$ pac commit -m 'Initial commit'
[master (root-commit) bee32c6] Initial commit
 1 file changed, 2798 insertions(+)
 create mode 100644 package_state.json
$ sudo pac man -R slim
...
$ pac add
$ pac commit -m 'Got rid of slim'
[master a276098] Got rid of slim
 1 file changed, 1553 insertions(+), 1557 deletions(-)
$ sudo pac apply HEAD~1
pacman -Sd --asexplicit slim=1.3.6-5
Continue? Y/n 
resolving dependencies...
looking for inter-conflicts...

Packages (1): slim-1.3.6-5

Total Installed Size:   0.44 MiB

:: Proceed with installation? [Y/n] 
(1/1) checking keys in keyring                               [################################] 100%
(1/1) checking package integrity                             [################################] 100%
(1/1) loading package files                                  [################################] 100%
(1/1) checking for file conflicts                            [################################] 100%
(1/1) checking available disk space                          [################################] 100%
(1/1) installing slim                                        [################################] 100%
```



[1]: http://docopt.org/