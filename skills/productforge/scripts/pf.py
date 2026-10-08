#!/usr/bin/env python3
"""ProductForge CLI — the deterministic core behind the ``productforge`` skill.

Contract: IMPLEMENTATION_PLAN.md §8. Every subcommand accepts ``--workspace DIR``
and ``--json`` (before or after the subcommand name). Exit codes: 0 ok,
1 check failed, 2 usage error / not implemented.

Standard library only. Run with any Python >= 3.9.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pflib import __version__  # noqa: E402
from pflib.errors import EXIT_OK, NotImplementedPF, PFError  # noqa: E402
from pflib.io import emit  # noqa: E402

Handler = Callable[[argparse.Namespace], Any]


def _cmd_status(args: argparse.Namespace) -> dict[str, Any]:
    # Real implementation (workspace discovery, counts, gate progress): Phase 02.
    return {"workspace": None, "message": "No ProductForge workspace found"}


def _not_implemented(name: str, phase: str) -> Handler:
    def handler(args: argparse.Namespace) -> Any:
        raise NotImplementedPF(f"{name}: not implemented (phase {phase})")

    return handler


def _add_init(p: argparse.ArgumentParser) -> None:
    p.add_argument("url", help="public product URL")
    p.add_argument("--scope", help="optional scope, e.g. 'issue tracking'")
    p.add_argument("--out", help="output workspace directory (default ./<product-slug>/)")
    p.add_argument("--name", help="working name for OUR product (never the target's name)")


def _add_check_command(p: argparse.ArgumentParser) -> None:
    p.add_argument("cmd", help="productforge command, e.g. features")


def _add_advance(p: argparse.ArgumentParser) -> None:
    p.add_argument("--to", required=True, metavar="STATE", help="next lifecycle state")
    p.add_argument("--confirmed", action="store_true", help="the user confirmed the gate report")


def _add_reopen(p: argparse.ArgumentParser) -> None:
    p.add_argument("state", metavar="STATE", help="earlier stage to re-open")
    p.add_argument("--reason", required=True, help="why the stage is re-opened")


def _add_next_id(p: argparse.ArgumentParser) -> None:
    p.add_argument("prefix", help="record prefix, e.g. D")


def _add_staging(p: argparse.ArgumentParser) -> None:
    p.add_argument("action", choices=["new"], help="staging action")
    p.add_argument("--role", required=True, help="role agent that will write the run")


def _add_merge(p: argparse.ArgumentParser) -> None:
    p.add_argument("run_id", help="staging run id")


def _add_validate(p: argparse.ArgumentParser) -> None:
    p.add_argument("--stage", metavar="STATE", help="only this stage's artifacts")
    p.add_argument("--artifact", metavar="PATH", help="only this artifact")


def _add_discover(p: argparse.ArgumentParser) -> None:
    p.add_argument("url", help="root URL to reconnoitre")
    p.add_argument("--max-pages", type=int, help="crawl cap per host")


def _add_trace(p: argparse.ArgumentParser) -> None:
    p.add_argument("--write", action="store_true", help="render spec/TRACEABILITY.md")


def _add_nothing(p: argparse.ArgumentParser) -> None:
    return None


# name, help, argument builder, handler — order mirrors IMPLEMENTATION_PLAN.md §8.
SUBCOMMANDS: list[tuple[str, str, Callable[[argparse.ArgumentParser], None], Handler]] = [
    ("init", "create a workspace and open DISCOVERY", _add_init, _not_implemented("init", "02")),
    ("status", "counts, open stage, gate progress, next command", _add_nothing, _cmd_status),
    ("check-command", "is a productforge command allowed now?", _add_check_command,
     _not_implemented("check-command", "02")),
    ("advance", "pass the open stage's gate and transition", _add_advance,
     _not_implemented("advance", "02")),
    ("reopen", "re-open an earlier stage (feedback loop)", _add_reopen,
     _not_implemented("reopen", "02")),
    ("next-id", "allocate one record ID", _add_next_id, _not_implemented("next-id", "01")),
    ("staging", "manage agent staging runs", _add_staging, _not_implemented("staging", "01")),
    ("merge", "merge a staging run into canonical files", _add_merge,
     _not_implemented("merge", "01")),
    ("validate", "schema, references, confidence and locks", _add_validate,
     _not_implemented("validate", "03")),
    ("discover", "robots/sitemap/link reconnaissance", _add_discover,
     _not_implemented("discover", "06")),
    ("score", "compute feature priorities and decisions", _add_nothing,
     _not_implemented("score", "13")),
    ("lint-phases", "lint generated phase plans", _add_nothing,
     _not_implemented("lint-phases", "15")),
    ("trace", "build the traceability graph", _add_trace, _not_implemented("trace", "16")),
    ("check", "validate + gate + lint + trace", _add_nothing, _not_implemented("check", "03")),
]


def _global_options(parser: argparse.ArgumentParser, suppress: bool) -> None:
    # Subparsers re-declare the globals with SUPPRESS defaults so `pf.py status --json`
    # and `pf.py --json status` both work without the subparser clobbering the value.
    default_ws: Any = argparse.SUPPRESS if suppress else None
    default_json: Any = argparse.SUPPRESS if suppress else False
    parser.add_argument("--workspace", metavar="DIR", default=default_ws,
                        help="workspace directory (default: nearest ancestor with .productforge/)")
    parser.add_argument("--json", action="store_true", default=default_json,
                        help="machine-readable JSON output")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pf.py",
        description="ProductForge deterministic core (IMPLEMENTATION_PLAN.md §8).",
    )
    parser.add_argument("--version", action="version", version=__version__)
    _global_options(parser, suppress=False)
    sub = parser.add_subparsers(dest="command", metavar="<subcommand>")
    sub.required = True
    for name, help_text, add_args, handler in SUBCOMMANDS:
        p = sub.add_parser(name, help=help_text, description=help_text)
        _global_options(p, suppress=True)
        add_args(p)
        p.set_defaults(handler=handler)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = args.handler(args)
    except PFError as exc:
        if args.json:
            emit({"error": exc.code, "message": exc.message}, as_json=True)
        print(f"pf.py: {exc.message}", file=sys.stderr)
        return exc.exit_code
    emit(result, as_json=args.json)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
