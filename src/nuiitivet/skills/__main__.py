"""Entry point for ``python -m nuiitivet.skills`` — install the bundled agent skills.

Subcommands::

    python -m nuiitivet.skills install              # → ./.claude/skills/
    python -m nuiitivet.skills install --user       # → ~/.claude/skills/
    python -m nuiitivet.skills install --dest DIR   # → DIR
    python -m nuiitivet.skills install nuiitivet-app  # only the named skill(s)
    python -m nuiitivet.skills list                 # print the bundled skill names

``install`` replaces any existing copy of each skill, so re-running it after
``pip install -U nuiitivet`` updates the skills to match the framework.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional, Sequence

from . import available_skills, install


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m nuiitivet.skills",
        description="Install the Claude Code skills bundled with nuiitivet.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    inst = subparsers.add_parser(
        "install",
        help="Copy the bundled skills into a Claude Code skills directory.",
    )
    inst.add_argument(
        "names",
        nargs="*",
        metavar="SKILL",
        help="Skills to install (default: all bundled skills).",
    )
    where = inst.add_mutually_exclusive_group()
    where.add_argument(
        "--user",
        action="store_true",
        help="Install into ~/.claude/skills/ instead of ./.claude/skills/.",
    )
    where.add_argument(
        "--dest",
        type=Path,
        help="Install into this directory instead of ./.claude/skills/.",
    )

    subparsers.add_parser("list", help="Print the names of the bundled skills.")

    return parser


def _install(args: argparse.Namespace) -> int:
    if args.dest is not None:
        dest = args.dest
    elif args.user:
        dest = Path.home() / ".claude" / "skills"
    else:
        dest = Path.cwd() / ".claude" / "skills"
    try:
        installed = install(dest, names=args.names or None)
    except (FileNotFoundError, ValueError) as exc:
        print(f"[nuiitivet.skills] {exc}", file=sys.stderr)
        return 1
    for path in installed:
        print(f"[nuiitivet.skills] installed {path}")
    return 0


def _list() -> int:
    try:
        names = available_skills()
    except FileNotFoundError as exc:
        print(f"[nuiitivet.skills] {exc}", file=sys.stderr)
        return 1
    for name in names:
        print(name)
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "list":
        return _list()
    return _install(args)


if __name__ == "__main__":
    raise SystemExit(main())
