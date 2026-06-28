# filedust Development Guide

Interested in the internals of filedust?

This guide describes the current `filedust` codebase for maintainers. It focuses on how the project is organised, how scanner rules flow into deletion candidates, and which safety invariants matter when changing the code.

---

## 1. What filedust does

`filedust` is a small command-line cleaner for obvious filesystem junk inside the invoking user's home directory.

Its core pipeline is:

```text
User-selected path
  |
  | filedust [PATH] [--dry-run] [-y]
  v
Home-contained scanner
  built-in junk rules
  user include/exclude rules from ~/.filedust.conf
  |
  v
Findings list
  path, kind, reason
  |
  v
Rich report and reclaimed-space estimate
  |
  | confirmation, unless --dry-run or --yes
  v
Deletion of reported files and directories
```

`filedust` deliberately targets narrow, recognisable junk:

```text
Python and test caches
common build artifacts
editor backup files
temporary files
OS metadata files
user-configured include patterns
```

It is not a general disk-cleaning daemon, secure erase tool, duplicate finder, package manager, backup system, or sandbox.

---

## 2. Repository layout

The project is a single Python package under `src/filedust/`.

```text
src/filedust/
  __init__.py              package marker
  cli.py                   argparse CLI, Rich output, confirmation, deletion
  junk.py                  user rules, glob matching, filesystem scan

pyproject.toml             Poetry package metadata and console script
poetry.lock                locked dependency graph
README.md                  user-facing documentation
.filedust.conf.example     example user include/exclude configuration
.pre-commit-config.yaml    Bandit, Black, and generic pre-commit hooks
.gitea/workflows/          lint, dependency audit, SBOM, and Grype workflows
dist/                      built release artifacts, not source
```

The installed command is configured in `pyproject.toml`:

```toml
[tool.poetry.scripts]
filedust = "filedust.cli:main"
```

There is no `filedust/__main__.py` at the time of writing, so `python -m filedust` is not the supported entry point. Use the installed `filedust` command or `poetry run filedust` during development.

---

## 3. Main runtime flow

All user-facing behaviour enters through `filedust.cli.main()`.

```text
filedust command
  -> filedust.cli.main()
     -> build argparse parser
     -> install argcomplete hook
     -> parse arguments
     -> expand and resolve requested path
     -> refuse paths outside $HOME
     -> load ~/.filedust.conf rules
     -> scan with junk.iter_junk()
     -> compute approximate reclaimed size
     -> render Rich report and summary
     -> return on --dry-run
     -> delete immediately on --yes
     -> otherwise ask one confirmation prompt
     -> delete reported findings
```

The command surface is intentionally small:

```text
PATH        optional directory to scan, default: current directory
--dry-run   show findings and summary without deleting anything
-y, --yes   delete findings without the interactive confirmation prompt
--version   print installed package version
```

Important dependency direction:

```text
cli.py
  depends on junk.py, argparse, argcomplete, pathlib, shutil, Rich

junk.py
  depends on pathlib, os.walk, configparser, fnmatch, dataclasses
```

Keep scanner and matching logic in `junk.py`. Keep CLI parsing, presentation, confirmation, and deletion orchestration in `cli.py`.

---

## 4. User rules

User rules are loaded from:

```text
~/.filedust.conf
```

The format is INI-like and uses no-value keys:

```ini
[exclude]
Projects/important/*

[include]
node_modules
*.tmp
```

`load_user_rules()` preserves key case by setting:

```python
parser.optionxform = str
```

Rule patterns are matched against paths relative to `$HOME`, not relative to the scan root.

Supported wildcard semantics are implemented in `matches_any()` and `_match_parts()`:

```text
*   matches exactly one path segment
**  matches zero or more path segments
```

Matching is case-sensitive because it delegates per-segment matching to `fnmatch()` without normalising case.

---

## 5. Built-in junk rules

Built-in junk directory names live in `junk.JUNK_DIR_NAMES`.

Current examples include:

```text
__pycache__
.pytest_cache
.mypy_cache
.ruff_cache
.nox
.tox
.hypothesis
.gradle
.parcel-cache
.turbo
.next
.vite
.sass-cache
dist
```

Built-in junk file patterns live in `junk.JUNK_FILE_PATTERNS`.

Current examples include:

```text
*~
*.swp
*.swo
*.swpx
*.tmp
*.temp
*.bak
*.orig
*.rej
.DS_Store
Thumbs.db
desktop.ini
```

Protected traversal directory names live in `junk.SKIP_DIR_NAMES`.

Current examples include:

```text
.cache
build
.gnupg
.git
.hg
.svn
.bzr
.idea
.vscode
```

These protected names are normally not descended into. If a user include pattern explicitly matches one of them, filedust reports the directory itself as a finding and still does not descend into it.

---

## 6. Finding objects

The scanner yields `junk.Finding` dataclass instances.

```python
@dataclass
class Finding:
    path: Path
    kind: str  # "file" or "dir"
    reason: str
```

Current `reason` values are:

```text
user_include
junk_dir
junk_file
broken_symlink
```

The CLI treats `kind == "file"` as an `unlink()` operation and `kind == "dir"` as a `shutil.rmtree()` operation. Keep this contract stable or update `delete_all()` with any new kinds.

---

## 7. Scanning behaviour

The scan entry point is `junk.iter_junk(root, rules=None)`.

Important scanner invariants:

```text
resolve the scan root before walking
walk with os.walk(..., followlinks=False)
match user rules relative to $HOME
apply user exclude before built-in junk detection
apply user include before built-in file junk detection
do not descend into symlink directories
do not follow valid symlink targets
handle unreadable paths without crashing
keep traversal contained in $HOME
```

The CLI performs the first home-boundary check before scanning:

```python
root_resolved.relative_to(Path.home().resolve())
```

`iter_junk()` also skips any walked directory that cannot be resolved relative to the module-level `HOME` constant.

### 7.1 Exclude rules

User excludes win over both user includes and built-in junk detection for a matching subtree or file.

For directories, an excluded path clears `dirnames` and prevents scanning that subtree:

```text
[exclude]
Projects/important/**
```

### 7.2 Include rules

User includes let the operator opt into paths that are not built-in junk.

Examples:

```text
[include]
node_modules
Downloads/**/*.tmp
```

Use include rules carefully. The scanner treats a matching directory as deletable and stops descending into it.

### 7.3 Symlinks

The scanner uses `lstat()` checks and `os.walk(..., followlinks=False)`.

Current behaviour:

```text
symlink directories are not descended into
valid symlink files are not auto-deleted by built-in rules
valid symlink files can be deleted only by user include rules
broken symlinks can be deleted by user include rules or by built-in junk file patterns that match the symlink name
symlink targets are not followed for scanning
```

Be careful when changing symlink behaviour. Any change must preserve the no-follow target boundary unless the tool's security model is deliberately redesigned.

---

## 8. Size reporting

The CLI computes an approximate reclaimed-space summary before deletion.

```text
file_size(path)       -> path.stat().st_size, or 0 on error
dir_size(path)        -> sum sizes of regular files under path.rglob("*")
compute_total_size()  -> total over all findings
human_size()          -> B, KB, MB, GB, TB, PB string
```

Size reporting is best-effort. It may differ from actual freed disk blocks because it uses file sizes rather than filesystem allocation data, because `stat()` can follow symlinks for explicitly included symlink file findings, and because the filesystem can change between scan, summary, and deletion.

---

## 9. Deletion behaviour

Deletion is centralised in `cli.delete_all(findings)`.

Current order:

```text
delete file findings first with Path.unlink(missing_ok=True)
delete directory findings second with shutil.rmtree(path)
print success or failure for each finding
return the number of failed deletions
```

The CLI calls `delete_all()` only after one of these conditions:

```text
--yes was provided
the user accepted the Rich confirmation prompt
```

`--dry-run` returns before deletion.

Do not add deletion paths outside `delete_all()` without preserving the same reporting and confirmation model.

---

## 10. Safety model

Important product boundaries:

```text
filedust only operates under the invoking user's $HOME
filedust does not automatically escalate privileges
filedust does not use sudo
filedust does not run as a daemon
filedust does not follow symlink targets while scanning
filedust previews all findings before deleting unless --yes is used
filedust deletes only paths yielded as findings
filedust does not securely wipe file contents
```

The most important guardrail is the home containment check in `cli.main()`. Preserve it for every operation that can scan or delete.

---

## 11. Development commands

Install dependencies:

```bash
poetry install
```

Run the CLI in the development environment:

```bash
poetry run filedust --help
poetry run filedust --dry-run .
```

Run pre-commit hooks:

```bash
poetry run pre-commit run --all-files
```

Run the pytest suite:

```bash
poetry run pytest
```

Current tests live under `tests/`. Scanner and rule coverage is in `tests/test_junk.py`; CLI, confirmation, and deletion coverage is in `tests/test_cli.py`. New behaviour should include focused tests, especially for `$HOME` containment, excludes, symlinks, dry-run, and deletion ordering.

Build release artifacts:

```bash
poetry build
```

---

## 12. Automation and security scanning

Gitea pull request workflow:

```text
.gitea/workflows/lint-and-security.yml
  -> set up Python 3.13
  -> install pre-commit
  -> pre-commit run --all-files
  -> install Poetry and poetry-plugin-export
  -> export dependencies
  -> pip-audit dependency audit
```

Scheduled/manual security workflow:

```text
.gitea/workflows/security-scan.yml
  -> install verified Cosign, Syft, and Grype
  -> generate SBOM
  -> scan for vulnerabilities
  -> notify Node-RED on fixable vulnerabilities
  -> fail workflow on fixable Medium, High, or Critical vulnerabilities
```

Pre-commit currently includes Bandit, Black, trailing whitespace, EOF, YAML, and TOML checks.

Bandit is configured for `src/filedust/` and skips `B110` and `B112`, which reflects the codebase's deliberate best-effort exception handling in filesystem traversal.

---

## 13. Common maintenance tasks

### 13.1 Add a new CLI option

1. Add the argparse option in `cli.build_parser()`.
2. Decide whether it affects scanning, reporting, confirmation, or deletion.
3. Keep scanner changes in `junk.py` if filesystem enumeration or matching changes.
4. Keep output and prompt changes in `cli.py`.
5. Update README usage examples.
6. Add tests for parser behaviour and the affected operation.

### 13.2 Add a built-in junk pattern

1. Decide whether the pattern is safe enough to delete without project-specific context.
2. Add directory names to `JUNK_DIR_NAMES` or file patterns to `JUNK_FILE_PATTERNS`.
3. Consider whether the path should instead be a user include example.
4. Update README examples if it changes user-visible expectations.
5. Add tests covering the new rule and exclude precedence.

### 13.3 Change user rule matching

1. Start with `matches_any()` and `_match_parts()` in `junk.py`.
2. Preserve `$HOME`-relative matching unless intentionally breaking compatibility.
3. Preserve `*` and `**` semantics or document the compatibility break.
4. Preserve exclude precedence.
5. Update `.filedust.conf.example` and README.
6. Add tests for simple, recursive, and non-matching patterns.

### 13.4 Change deletion behaviour

1. Start with `delete_all()` in `cli.py`.
2. Keep scan/report and mutation separated.
3. Preserve `--dry-run` as non-mutating.
4. Preserve confirmation unless `--yes` is provided.
5. Preserve per-path failure reporting.
6. Consider filesystem races between scan and delete.
7. Add tests with temporary directories.

### 13.5 Add tests

Good first test areas:

```text
matches_any handles *, **, case sensitivity, and stripped slashes
load_user_rules reads include and exclude sections with case preserved
iter_junk detects built-in junk directories and files
iter_junk gives exclude rules precedence
iter_junk handles user includes
iter_junk does not follow symlink targets
CLI refuses paths outside $HOME
--dry-run does not call deletion
delete_all reports failures and deletes files before directories
```

Use temporary directories and temporary home directories where possible. Avoid tests that require root.

---

## 14. Important maintenance hazards

### 14.1 Home containment is the main safety boundary

`filedust` is marketed as safe because it refuses to operate outside `$HOME`. Any feature that accepts paths must preserve this boundary before scanning or deleting.

### 14.2 User includes are powerful

Built-in rules should stay conservative. User include rules intentionally allow broader cleanup. Keep the distinction clear in documentation and output.

### 14.3 Exclude precedence must remain predictable

Excludes are the operator's escape hatch. Avoid changes where an include or built-in rule can override an explicit exclude.

### 14.4 Symlink handling is security-sensitive

The scanner currently avoids following symlinks. Do not replace `lstat()` with `stat()` or enable `followlinks=True` without a deliberate redesign.

### 14.5 Filesystem races are unavoidable

The filesystem can change between scan, size calculation, confirmation, and deletion. Keep deletion best-effort and report failures clearly.

### 14.6 Directory names can be too broad

Names such as `dist` and `.next` are common build artifacts, but they can be meaningful in some projects. Be conservative when adding broad directory rules.

### 14.7 Size reporting is not an audit log

The reclaimed-space estimate is informational. Do not treat it as exact accounting or proof of deletion.

---

## 15. Troubleshooting guide

### 15.1 filedust refuses to run outside home

The requested scan root resolves outside `Path.home()`. Choose a path under the invoking user's home directory.

### 15.2 A path was not detected

Check, in order:

1. Is the path under `$HOME`?
2. Is the path under the selected scan root?
3. Is the path excluded by `~/.filedust.conf`?
4. Is the directory name in `SKIP_DIR_NAMES`?
5. Is it a valid symlink target that filedust intentionally does not follow?
6. Does the name match a built-in junk rule or user include rule?

### 15.3 A path was detected unexpectedly

Check whether it matches a built-in name or pattern, or whether a user include rule in `~/.filedust.conf` matches it relative to `$HOME`.

### 15.4 Deletion failed

The file may have been removed already, permissions may have changed, or the directory may no longer be removable. `delete_all()` reports each failed path and continues with the rest.

### 15.5 Completion does not work

Check that argcomplete is installed and registered for the shell:

```bash
eval "$(register-python-argcomplete filedust)"
```

---

## 16. Practical code-reading map

```text
Feature/question                 Start with                    Then read
CLI option behaviour             cli.py:build_parser()          cli.py:main()
Version output                   cli.py:get_version()           pyproject.toml
Home boundary                    cli.py:main()                  junk.py:iter_junk()
Rich report                      cli.py:print_table()           cli.py:print_summary_block()
Deletion                         cli.py:delete_all()            junk.py:Finding
User config                      junk.py:load_user_rules()      .filedust.conf.example
Pattern matching                 junk.py:matches_any()          junk.py:_match_parts()
Built-in junk rules              junk.py:JUNK_DIR_NAMES         junk.py:JUNK_FILE_PATTERNS
Traversal skips                  junk.py:SKIP_DIR_NAMES         junk.py:iter_junk()
Symlink behaviour                junk.py:iter_junk()            cli.py:delete_all()
Packaging                        pyproject.toml                 Poetry docs
Automation                       .gitea/workflows/              .pre-commit-config.yaml
```

---

## 17. Glossary

**Finding** A scanner result containing a path, kind, and reason.

**Junk directory** A directory whose basename is in `JUNK_DIR_NAMES`.

**Junk file** A file whose basename matches `JUNK_FILE_PATTERNS`.

**User include** A pattern in `~/.filedust.conf` that opts a path into cleanup.

**User exclude** A pattern in `~/.filedust.conf` that opts a path or subtree out of cleanup.

**Scan root** The user-selected path passed to `filedust`, defaulting to the current directory.

**Home boundary** The requirement that scan roots resolve under `Path.home()`.

**Dry run** A run that reports findings without deleting anything.

---

## 18. Final maintenance model

Most changes should preserve this model:

```text
Resolve the requested path under $HOME
  -> scan without following symlink targets
  -> apply user excludes before cleanup rules
  -> report every deletion candidate before mutation
  -> delete only after --yes or interactive confirmation
  -> report failures without crashing the whole run
```

Before changing code, ask:

1. Does this preserve the `$HOME` containment boundary?
2. Does this preserve dry-run as non-mutating?
3. Does this preserve confirmation before deletion unless `--yes` is passed?
4. Does this preserve exclude precedence?
5. Does this avoid following symlink targets?
6. Is this built-in rule conservative enough, or should it be a user include example?
7. Are filesystem race behaviours clear and best-effort?
8. Do README examples, `.filedust.conf.example`, and shell completion still match the command surface?
9. Are there focused tests for the edge case being changed?

Keeping those boundaries clear is the main way to maintain filedust without turning a narrow junk cleaner into a risky general-purpose deletion tool.
