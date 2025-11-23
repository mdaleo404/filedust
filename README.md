[![License](https://img.shields.io/github/license/mdaleo404/filedust)](LICENCE)
[![Language](https://img.shields.io/github/languages/top/mdaleo404/filedust.svg)](https://github.com/mdaleo404/filedust/)
![GitHub Release](https://img.shields.io/github/v/release/mdaleo404/filedust?display_name=release&logo=github)
![PyPI - Version](https://img.shields.io/pypi/v/filedust?logo=pypi)
[![Build Status](https://img.shields.io/github/actions/workflow/status/mdaleo404/filedust/.github/workflows/lint-and-security.yml)](https://github.com/mdaleo404/filedust/actions)
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
