[![License](https://img.shields.io/github/license/guardutils/filedust?style=flat)](LICENCE)
[![Language](https://img.shields.io/github/languages/top/guardutils/filedust.svg)](https://github.com/guardutils/filedust/)
![GitHub Release](https://img.shields.io/github/v/release/guardutils/filedust?display_name=release&logo=github)
![PyPI - Version](https://img.shields.io/pypi/v/filedust?logo=pypi)
[![PyPI downloads](https://img.shields.io/pypi/dm/filedust.svg)](https://pypi.org/project/filedust/)

# filedust

**filedust** is a small, fast, and safe command-line tool that scans your filesystem for obvious junk — things like Python __pycache__ folders, build artifacts, editor backup files, and leftover temporary files — and cleans them up.

Think of it as “`autoremove` for files.”

## Features

### Cleans common junk
Deletes well-known clutter such as:
* `__pycache__/`

* `.pytest_cache`, `.mypy_cache`, `.ruff_cache`

* `build/`, `dist/`

* editor backups `*~`, `*.swp`, `*.tmp`, etc.

* OS metadata like `.DS_Store`, `Thumbs.db`

###  Rich, colorful table output
It wasn't essential, but it's easy to read at a glance.

### Single confirmation prompt
One interactive prompt at the end of the run (unless -y is used).

### Reclaimed space summary
Shows how much disk space can be freed.

### Safe by design
Never touches dotfiles, configs, project files, or anything important.

## Installation

### From PyPI
```
pip install filedust
```

### From this repository
```
git clone https://github.com/guardutils/filedust.git
cd filedust/
poetry install
```

### TAB completion
Add this to your `.bashrc`
```
eval "$(register-python-argcomplete filedust)"
```
And then
```
source ~/.bashrc
```
