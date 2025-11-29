from __future__ import annotations

import importlib.metadata
import argparse
import argcomplete
import shutil
from pathlib import Path
from typing import List

from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm
from rich import box

from .junk import Finding, iter_junk, load_user_rules


console = Console()


def get_version():
    try:
        return importlib.metadata.version("filedust")
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def file_size(p: Path) -> int:
    try:
        return p.stat().st_size
    except Exception:
        return 0


def dir_size(p: Path) -> int:
    total = 0
    try:
        for sub in p.rglob("*"):
            if sub.is_file():
                total += file_size(sub)
    except Exception:
        pass
    return total


def compute_total_size(findings: List[Finding]) -> int:
    total = 0
    for f in findings:
        if f.kind == "file":
            total += file_size(f.path)
        else:
            total += dir_size(f.path)
    return total


def human_size(num: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if num < 1024:
            return f"{num:.1f} {unit}"
        num /= 1024
    return f"{num:.1f} PB"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="filedust",
        description=(
            "Clean obvious junk from your filesystem: caches, build artifacts, "
            "and temporary/editor backup files."
        ),
    )

    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"filedust {get_version()}",
    )

    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Directory to scan (default: current directory).",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted but do not remove anything.",
    )

    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Delete without prompting for confirmation.",
    )

    try:
        argcomplete.autocomplete(parser)
    except ImportError:
        pass

    return parser


def print_table(findings: List[Finding]) -> None:
    if not findings:
        return

    table = Table(
        title="filedust junk report",
        title_style="bold yellow",
        box=box.SIMPLE_HEAVY,
    )

    table.add_column("Type", style="magenta", no_wrap=True)
    table.add_column("Path", style="white")
    table.add_column("Reason", style="cyan")

    for f in findings:
        style = "bright_green" if f.kind == "file" else "bright_blue"
        table.add_row(
            f"[{style}]{f.kind}[/{style}]",
            str(f.path),
            f.reason,
        )

    console.print()
    console.print(table)


def print_summary_block(findings: List[Finding], total_size: int) -> None:
    file_count = sum(1 for f in findings if f.kind == "file")
    dir_count = sum(1 for f in findings if f.kind == "dir")

    console.print("\n[bold underline]Summary[/]\n")
    console.print(f"  • Junk files:        [cyan]{file_count}[/]")
    console.print(f"  • Junk directories:  [cyan]{dir_count}[/]")
    console.print(
        f"  • Potential reclaimed space: [green]{human_size(total_size)}[/]\n"
    )


def delete_all(findings: List[Finding]) -> int:
    failures = 0

    # Delete files first
    for f in [x for x in findings if x.kind == "file"]:
        try:
            f.path.unlink(missing_ok=True)
            console.print(f"[green]✓ deleted file[/]: {f.path}")
        except Exception as exc:
            failures += 1
            console.print(f"[red]✗ failed to delete[/] {f.path}: {exc}")

    # Delete directories second
    for d in [x for x in findings if x.kind == "dir"]:
        try:
            shutil.rmtree(d.path)
            console.print(f"[green]✓ deleted dir [/]: {d.path}")
        except Exception as exc:
            failures += 1
            console.print(f"[red]✗ failed to delete[/] {d.path}: {exc}")

    return failures


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    root = Path(args.path).expanduser()
    home = Path.home().resolve()
    root_resolved = root.resolve()

    # Ensure root is inside the user's home directory
    try:
        root_resolved.relative_to(home)
    except ValueError:
        console.print(
            f"[red]Error:[/] Refusing to operate outside the user's home directory.\n"
            f"Requested: {root_resolved}\n"
            f"Allowed:   {home}"
        )
        return 1

    if not root.exists():
        console.print(f"[red]Error:[/] Path not found: {root}")
        return 1

    print("Looking for junk ...")

    if root.resolve() == Path("/"):
        console.print(
            "[yellow]Running filedust on the entire filesystem (/). "
            "This may take a while and may require sudo for deletions.[/]"
        )

    rules = load_user_rules()
    findings = list(iter_junk(root, rules=rules))
    total_size = compute_total_size(findings)

    if not findings:
        console.print("[green]No junk found![/]")
        return 0

    print_table(findings)
    print_summary_block(findings, total_size)

    # Default = dry-run
    if args.dry_run:
        console.print("[yellow]Dry-run only[/]: no deletions performed.")
        return 0

    # Bulk: skip interactive prompt
    if args.yes:
        return delete_all(findings)

    # Interactive prompt for ALL items at once
    console.print("[bold yellow]Cleanup confirmation[/]")
    if not Confirm.ask(
        "Do you want to clean this up?", default=False, show_default=True
    ):
        console.print("[cyan]Operation canceled.[/]")
        return 0

    return delete_all(findings)


if __name__ == "__main__":
    raise SystemExit(main())
