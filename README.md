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
pac pacman -Syu
pac -c pacman -Syu
(cd $PAC_GIT_REPO; pacman -Syu)
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
[master 681d535] Got rid of slim
 1 file changed, 2794 insertions(+), 2798 deletions(-)
 rewrite package_state.json (67%)
$ sudo pac apply HEAD~1
pacman -Rd slim
Continue? Y/n
checking dependencies...

Packages (1): slim-1.3.6-5

Total Removed Size:   0.44 MiB

:: Do you want to remove these packages? [Y/n]
(1/1) removing slim                                          [################################] 100%

```



[1]: http://docopt.org/