from __future__ import annotations

import os
import configparser
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path
from typing import Iterable, List


class UserRules:
    def __init__(self):
        self.include: list[str] = []
        self.exclude: list[str] = []


def load_user_rules() -> UserRules:
    rules = UserRules()
    cfg_path = Path.home() / ".filedust.conf"

    if cfg_path.exists():
        parser = configparser.ConfigParser(allow_no_value=True)
        parser.optionxform = str
        parser.read(cfg_path)

        if parser.has_section("include"):
            rules.include = list(parser["include"].keys())

        if parser.has_section("exclude"):
            rules.exclude = list(parser["exclude"].keys())

    return rules


def matches_any(patterns: list[str], relpath: Path) -> bool:
    """
    True globstar matcher.

    Rules:
    - *  matches exactly one path segment
    - ** matches zero or more segments
    - Patterns are relative to $HOME
    """

    path_parts = relpath.parts

    for pat in patterns:
        pat = pat.strip("/")

        pat_parts = tuple(pat.split("/"))

        if _match_parts(pat_parts, path_parts):
            return True

    return False


def _match_parts(pat: tuple[str, ...], path: tuple[str, ...]) -> bool:
    """Recursive glob matcher with ** support."""
    if not pat:
        return not path

    if pat[0] == "**":
        # ** matches zero or more segments
        return _match_parts(pat[1:], path) or (
            bool(path) and _match_parts(pat, path[1:])
        )

    if not path:
        return False

    if fnmatch(path[0], pat[0]):
        return _match_parts(pat[1:], path[1:])

    return False


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
    ".gradle",
    ".parcel-cache",
    ".turbo",
    ".next",
    ".vite",
    ".sass-cache",
    ".sass-cache",
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
    ".cache",
    "build",
    ".gnupg",
    ".git",
    ".hg",
    ".svn",
    ".bzr",
    ".idea",
    ".vscode",
}


HOME = Path.home().resolve()


def safe_exists(path: Path) -> bool | None:
    """Return True/False if the path exists, or None if permission denied."""
    try:
        return path.exists()
    except Exception:
        return None


def safe_resolve(path: Path, root: Path) -> Path | None:
    """
    Resolve symlinks only if safe.
    Return resolved path if it stays within root.
    Return None if:
      - resolution escapes the root
      - resolution fails
      - permission denied
    """
    try:
        resolved = path.resolve(strict=False)  # NEVER strict
        resolved.relative_to(root)  # ensure containment
        return resolved
    except Exception:
        return None


def is_junk_dir_name(name: str) -> bool:
    return name in JUNK_DIR_NAMES


def is_junk_file_name(name: str) -> bool:
    return any(fnmatch(name, pattern) for pattern in JUNK_FILE_PATTERNS)


def iter_junk(root: Path, rules: UserRules | None = None) -> Iterable[Finding]:
    """
    Safe, fast junk scanner:
      - Never follows symlinks.
      - Broken symlinks are not automatically junk — they follow normal rules.
      - User include/exclude overrides all.
      - Built-in junk rules applied only when safe.
      - SKIP_DIR_NAMES protected unless user includes.
      - Fully contained in $HOME.
      - No crashes from PermissionError or unreadable paths.
    """
    if rules is None:
        rules = UserRules()

    root = root.resolve()
    root_str = str(root)

    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirpath_p = Path(dirpath)

        try:
            rel_dir = dirpath_p.resolve().relative_to(HOME)
        except ValueError:
            # Should never happen due to earlier checks
            continue

        # USER EXCLUDE → skip entire subtree
        if matches_any(rules.exclude, rel_dir):
            dirnames[:] = []
            continue

        pruned = []

        # Handling dirs
        for d in dirnames:
            child = dirpath_p / d

            try:
                st = child.lstat()
            except Exception:
                continue  # unreadable

            is_symlink = (st.st_mode & 0o170000) == 0o120000

            if is_symlink:
                # If broken symlink dir treat as file later via filenames (skip descent)
                continue

            rel_child = rel_dir / d

            # User exclude wins
            if matches_any(rules.exclude, rel_child):
                continue

            # SKIP_DIR_NAMES unless user includes
            if d in SKIP_DIR_NAMES and not matches_any(
                rules.include, rel_child
            ):
                continue

            pruned.append(d)

        dirnames[:] = pruned

        # Detect JUNK dirs
        i = 0
        while i < len(dirnames):
            name = dirnames[i]
            rel_child = rel_dir / name

            # User include directory
            if matches_any(rules.include, rel_child):
                yield Finding(dirpath_p / name, "dir", "user_include")
                del dirnames[i]
                continue

            # Built-in safe junk dirs
            if is_junk_dir_name(name):
                yield Finding(dirpath_p / name, "dir", "junk_dir")
                del dirnames[i]
                continue

            i += 1

        # Handling files (including symlinks)
        for fname in filenames:
            fpath = dirpath_p / fname
            rel_file = rel_dir / fname

            try:
                st = fpath.lstat()
            except Exception:
                continue

            is_symlink = (st.st_mode & 0o170000) == 0o120000

            # Handling broken symlinks
            if is_symlink:
                exists = safe_exists(fpath)

                # Permission denied → skip
                if exists is None:
                    continue

                # User exclude wins
                if matches_any(rules.exclude, rel_file):
                    continue

                # User include wins
                if matches_any(rules.include, rel_file):
                    yield Finding(fpath, "file", "user_include")
                    continue

                # Broken symlink?
                if exists is False:
                    # DO NOT auto-delete — classify like regular file
                    # Only built-in junk patterns apply
                    if is_junk_file_name(fname):
                        yield Finding(fpath, "file", "broken_symlink")
                    continue

                # Valid symlink — NEVER follow; only user-include counts
                continue

            # Regular files
            # User exclude wins
            if matches_any(rules.exclude, rel_file):
                continue

            # User include wins
            if matches_any(rules.include, rel_file):
                yield Finding(fpath, "file", "user_include")
                continue

            # Built-in junk patterns (safe ones)
            if is_junk_file_name(fname):
                yield Finding(fpath, "file", "junk_file")
