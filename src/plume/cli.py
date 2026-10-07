"""Small headless CLI for config/workspace preparation."""

from __future__ import annotations

import argparse
from pathlib import Path

from .config import load_config
from .errors import PlumeError
from .workspace import prepare_run


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="plume")
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare = subparsers.add_parser(
        "prepare",
        help="normalize a config, resolve local providers, and create a run manifest",
    )
    prepare.add_argument("config", type=Path)
    prepare.add_argument("--workspace", type=Path, default=None)
    prepare.add_argument("--run-id", default=None)
    prepare.add_argument("--git-sha", default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            config = load_config(args.config)
            prepared = prepare_run(
                config,
                workspace_override=args.workspace,
                run_id=args.run_id,
                git_sha=args.git_sha,
            )
            print(prepared.run_dir)
            return 0
    except PlumeError as exc:
        parser.exit(2, f"plume: error: {exc}\n")
    raise AssertionError("unreachable")
