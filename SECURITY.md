# filedust Threat Model and Security Scope

`filedust` is a command-line filesystem cleanup tool. It is designed to be executed intentionally by a local user to find and delete obvious junk under that user's home directory.

Because of that design, filedust's security model is different from that of a network service, web application, daemon, sandbox, or setuid program. filedust does not attempt to defend against arbitrary compromise of the account executing it. If an attacker can control the command line, shell environment, current working directory, installed Python package, user configuration file, or files under the user's home directory, they may be able to influence what filedust scans or deletes. That situation is considered a local trust-boundary failure outside filedust's intended security model.

filedust deletes filesystem entries. It does not securely wipe data, protect file contents, restore deleted files, quarantine files, or provide an undo log.

## Core Assumptions

filedust assumes that the person running the tool understands what they are asking it to do.

In particular:

- If `-y` or `--yes` is used, the operator is intentionally bypassing the interactive confirmation prompt.
- If `~/.filedust.conf` exists, its include and exclude patterns are trusted local user configuration chosen by the operator.
- If a user include rule matches a path, the operator intentionally opted that path into cleanup.
- The current user's home directory is the intended boundary for scanning and deletion.
- The operator is expected to review the report before confirming deletion.
- The operator is expected not to run filedust with elevated privileges unless they understand the impact of deleting files as that account.

## What filedust Scans

filedust scans for a narrow set of deletion candidates:

- Built-in junk directory names such as `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `.tox`, `.nox`, `.next`, `.vite`, `.turbo`, and `dist`.
- Built-in junk file patterns such as `*~`, `*.swp`, `*.tmp`, `*.bak`, `.DS_Store`, `Thumbs.db`, and `desktop.ini`.
- User include patterns from `~/.filedust.conf`.

filedust deliberately avoids broad cleanup features such as:

- System-wide scanning outside the invoking user's home directory.
- Automatic privilege escalation.
- Following symlink targets while scanning.
- Secure deletion or shredding.
- Restoring deleted files.
- Deleting package-manager-owned files outside the user's home directory.
- Deleting arbitrary files based on age, owner, permissions, or size alone.
- Interpreting untrusted remote policy.

## What Is In Scope

filedust tries to protect users from common and serious mistakes that can occur when a local cleanup tool deletes filesystem entries.

In-scope security concerns include:

- filedust must refuse scan roots that resolve outside the invoking user's home directory.
- Dry-run mode must not delete files or directories.
- Mutating cleanup must require confirmation unless `--yes` is provided.
- filedust must not automatically run sudo or otherwise escalate privileges.
- Scanning should use no-follow traversal and avoid following symlink targets.
- Built-in rules should remain conservative and limited to obvious junk.
- User exclude rules should take precedence over built-in junk detection and user include cleanup.
- filedust should not descend into protected directories such as `.git`, `.gnupg`, `.cache`, `.idea`, or `.vscode`; if explicitly included by the user, they should be reported as whole-directory findings instead.
- Deletion should be limited to paths reported as findings.
- Unreadable paths and permission errors should not crash the entire scan.
- Shell completion and version display should not mutate filesystem state.

These measures are defense-in-depth. They are intended to reduce the chance of accidental deletion, symlink traversal, or unintended cleanup when filedust is used normally by a local user.

## What Is Out Of Scope

The following are generally out of scope and should not be reported as filedust vulnerabilities unless they also bypass one of filedust's explicit hardening mechanisms:

- A malicious local user who can already control the operator's command line, shell environment, current working directory, Python environment, installed package, or files under the operator's home directory.
- A user intentionally adding dangerous include patterns to `~/.filedust.conf`.
- A user intentionally passing `--yes` and bypassing confirmation.
- A user intentionally selecting a path that contains files they do not want deleted.
- A user running filedust as root or under another account and then being able to delete files accessible to that account.
- A compromised system where an attacker already controls the user's files, shell startup files, Python packages, or terminal session.
- Reports that amount to "if the user configures filedust to delete a path, filedust deletes that path."
- Reports that filedust does not provide secure wipe, quarantine, restore, audit logging, or backup semantics.

filedust is a cleanup tool for trusted local users, not a sandbox for hostile local users. It cannot make unsafe local trust decisions safe if the operator's own execution environment is already attacker-controlled.

## User Configuration

filedust reads optional configuration from:

```text
~/.filedust.conf
```

The file supports two sections:

```ini
[exclude]
Projects/important/**

[include]
Downloads/**/*.tmp
```

Patterns are matched relative to `$HOME`. They support:

```text
*   one path segment
**  zero or more path segments
```

Configuration is trusted local user policy. A malicious or overly broad include rule can cause filedust to report and delete files the user did not intend to remove.

Excludes are intended as the safety override. If a path matches an exclude rule, filedust should skip it even if it also matches an include or built-in junk rule.

## Home Directory Boundary

filedust's primary safety boundary is that the requested scan root must resolve under the invoking user's home directory.

For example, these are intended to be valid when they resolve under `$HOME`:

```bash
filedust
filedust ~/Projects
filedust ~/Downloads --dry-run
```

These are intended to be rejected when they resolve outside `$HOME`:

```bash
filedust /
filedust /tmp
filedust /etc
```

This boundary limits accidental system-wide cleanup. It is not a sandbox against a compromised user account or malicious files controlled by that same user.

## Symlinks And Filesystem Races

filedust uses no-follow traversal with `os.walk(..., followlinks=False)` and `lstat()` checks in the scanner. It should not follow a symlink target and delete files reached through that target as part of normal scanning.

Current intended behaviour:

- Symlink directories are not descended into.
- Valid symlink files are not auto-deleted by built-in junk rules.
- Valid symlink files can be deleted only when matched by user include rules.
- Broken symlinks can be deleted by user include rules or when their own name matches a built-in junk file pattern.

Because filedust operates on a live filesystem, concurrent filesystem changes can still affect what exists at the moment deletion runs. filedust mitigates this by scanning first, reporting findings, asking for confirmation unless `--yes` is used, and handling deletion failures per path. It does not claim to provide a transactional cleanup operation.

## Dry Run And Confirmation

Dry-run mode is expected to be non-mutating:

```bash
filedust --dry-run PATH
```

Without `--dry-run`, filedust reports all findings and asks one confirmation question before deleting anything.

The confirmation prompt is intentionally bypassed by:

```bash
filedust --yes PATH
filedust -y PATH
```

Using `--yes` is an explicit operator decision and is not considered a vulnerability by itself.

## Local Compromise

filedust includes hardening against some local filesystem hazards because it deletes files. For example, it refuses paths outside `$HOME`, avoids following symlink targets during scanning, previews findings, and does not automatically escalate privileges.

However, local compromise cannot be ruled out completely for a CLI tool running as the user. If an attacker can influence the user's shell, Python environment, installed filedust package, configuration file, current working directory, or files under `$HOME`, they may be able to influence filedust's behaviour.

Such scenarios are treated as local compromise or operator trust failures, not as vulnerabilities in filedust by themselves.

## Security Report Guidance

Useful vulnerability reports include issues where filedust behaves unsafely despite the documented trust model. Examples include:

- filedust follows a symlink target during scanning and deletes files outside the intended scanned tree.
- filedust accepts a scan root that resolves outside the invoking user's home directory.
- `--dry-run` deletes files or directories.
- filedust deletes paths that were not reported as findings.
- filedust deletes without confirmation when `--yes` was not provided.
- An explicit exclude rule is bypassed by a built-in junk rule or user include rule.
- filedust automatically escalates privileges or invokes sudo.
- Shell completion or version display causes deletion or other mutation.
- A failed containment or symlink safety check is silently ignored and filedust proceeds with a dangerous deletion.

Less useful reports, and normally out of scope, include:

- "The user can configure an include pattern that deletes important files."
- "The user can pass `--yes` and bypass confirmation."
- "The user can run filedust as root and delete files root can delete."
- "A malicious local user can compromise filedust after already controlling the operator's environment, Python packages, or home directory."
- "filedust does not securely wipe deleted data."
- "filedust does not restore files after deletion."
- "filedust does not scan outside `$HOME`."

Reports about concrete bypasses of filedust's hardening are welcome. The project does not treat intentional user-controlled cleanup policy as a vulnerability by itself.
