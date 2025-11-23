from __future__ import annotations

import os
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path
from typing import Iterable, List


@dataclass
class Finding:
    path: Path
    kind: str  # "file" or "dir"
    reason: str


# Directories that are *typically* safe to delete completely.
JUNK_DIR_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".nox",
    ".tox",
    ".hypothesis",
    ".cache",
    ".gradle",
    ".parcel-cache",
    ".turbo",
    ".next",
    ".vite",
    ".sass-cache",
    ".sass-cache",
    "build",
    "dist",
}

# File name patterns that are almost always junk / temporary.
JUNK_FILE_PATTERNS = [
    "*~",
    "*.swp",
    "*.swo",
    "*.swpx",
    "*.tmp",
    "*.temp",
    "*.bak",
    "*.orig",
    "*.rej",
    ".DS_Store",
    "Thumbs.db",
    "desktop.ini",
]

# VCS / system dirs
SKIP_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    ".bzr",
    ".idea",
    ".vscode",
}


def is_junk_dir_name(name: str) -> bool:
    return name in JUNK_DIR_NAMES


def is_junk_file_name(name: str) -> bool:
    return any(fnmatch(name, pattern) for pattern in JUNK_FILE_PATTERNS)


def iter_junk(root: Path) -> Iterable[Finding]:
    """
    Walk the tree under `root` and yield junk candidates.

    filedust:
      - Skips known critical / config directories (SKIP_DIR_NAMES).
      - Treats known "junk" directory names as removable as a whole.
      - Treats known junk file patterns as removable.
    """
    root = root.resolve()

    for dirpath, dirnames, filenames in os.walk(root):
        dirpath_p = Path(dirpath)

        # Prune dirs we never touch at all.
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIR_NAMES]

        # Detect junk directories (and skip walking inside them).
        i = 0
        while i < len(dirnames):
            name = dirnames[i]
            if is_junk_dir_name(name):
                junk_dir = dirpath_p / name
                yield Finding(path=junk_dir, kind="dir", reason="junk_dir")
                # Remove from walk so we don't descend into it.
                del dirnames[i]
                continue
            i += 1

        # Now process files.
        for fname in filenames:
            if is_junk_file_name(fname):
                fpath = dirpath_p / fname
                yield Finding(path=fpath, kind="file", reason="junk_file")
