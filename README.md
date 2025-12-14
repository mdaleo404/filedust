[![Licence](https://img.shields.io/badge/GPL--3.0-orange?label=Licence)](https://git.sysmd.uk/guardutils/filedust/src/branch/main/LICENCE)
[![Gitea Release](https://img.shields.io/gitea/v/release/guardutils/filedust?gitea_url=https%3A%2F%2Fgit.sysmd.uk%2F&style=flat&color=orange&logo=gitea)](https://git.sysmd.uk/guardutils/filedust/releases)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-blue?logo=pre-commit&style=flat)](https://git.sysmd.uk/guardutils/filedust/src/branch/main/.pre-commit-config.yaml)

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
* It ONLY runs within user's `$HOME`

* Put user in control by reading `~/.filedust.conf`

* Never touches dotfiles, configs, project files, or anything important unless you want.

## Installation

### From GuardUtils package repo

This is the preferred method of installation.

### Debian/Ubuntu

#### 1) Import the GPG key

```bash
sudo mkdir -p /usr/share/keyrings
curl -fsSL https://repo.sysmd.uk/guardutils/guardutils.gpg | sudo gpg --dearmor -o /usr/share/keyrings/guardutils.gpg
```

The GPG fingerprint is `0032C71FA6A11EF9567D4434C5C06BD4603C28B1`.

#### 2) Add the APT source

```bash
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/guardutils.gpg] https://repo.sysmd.uk/guardutils/debian stable main" | sudo tee /etc/apt/sources.list.d/guardutils.list
```

#### 3) Update and install

```
sudo apt update
sudo apt install filedust
```

### Fedora/RHEL

#### 1) Import the GPG key

```
sudo rpm --import https://repo.sysmd.uk/guardutils/guardutils.gpg
```

#### 2) Add the repository configuration

```
sudo tee /etc/yum.repos.d/guardutils.repo > /dev/null << 'EOF'
[guardutils]
name=GuardUtils Repository
baseurl=https://repo.sysmd.uk/guardutils/rpm/$basearch
enabled=1
gpgcheck=1
repo_gpgcheck=1
gpgkey=https://repo.sysmd.uk/guardutils/guardutils.gpg
EOF
```

#### 4) Update and install

```
sudo dnf upgrade --refresh
sudo dnf install filedust
```

### From PyPI
```
pip install filedust
```

### From this repository
```
git clone https://git.sysmd.uk/guardutils/filedust.git
cd filedust/
poetry install
```

### Custom config
You can download the example and add your custom rule
```
wget -O ~/.filedust.conf https://git.sysmd.uk/guardutils/filedust/raw/branch/main/.filedust.conf.example
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

## pre-commit
This project uses [**pre-commit**](https://pre-commit.com/) to run automatic formatting and security checks before each commit (Black, Bandit, and various safety checks).

To enable it:
```
poetry install
poetry run pre-commit install
```
This ensures consistent formatting, catches common issues early, and keeps the codebase clean.
