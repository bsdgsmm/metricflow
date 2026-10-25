from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from pathlib import Path

from metricflow.config import PROJECT_ROOT
from metricflow.logging_config import configure_logging
from metricflow.sample_data import DEFAULT_SEED, generate_dataset, write_dataset

logger = logging.getLogger("metricflow.cli")


def _generate_sample_data(args: argparse.Namespace) -> int:
    dataset = generate_dataset(seed=args.seed)
    write_dataset(dataset, args.output_dir)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="metricflow", description="MetricFlow pipeline commands")
    parser.add_argument("--log-level", default=None, help="Override METRICFLOW_LOG_LEVEL")
    subcommands = parser.add_subparsers(dest="command", required=True)

    generate = subcommands.add_parser(
        "generate-sample-data", help="Regenerate the synthetic sample dataset"
    )
    generate.add_argument("--seed", type=int, default=DEFAULT_SEED, help="Random seed")
    generate.add_argument(
        "--output-dir", type=Path, default=PROJECT_ROOT / "data" / "sample", help="Target folder"
    )
    generate.set_defaults(handler=_generate_sample_data)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(args.log_level or "INFO")
    try:
        return args.handler(args)
    except Exception:
        logger.exception("command_failed command=%s", args.command)
        return 1


if __name__ == "__main__":
    sys.exit(main())
