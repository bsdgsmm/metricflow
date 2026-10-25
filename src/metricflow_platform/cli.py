from __future__ import annotations

import argparse
import logging
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from metricflow_platform.config import PROJECT_ROOT, load_settings
from metricflow_platform.logging_config import configure_logging
from metricflow_platform.sample_data import DEFAULT_SEED, generate_dataset, write_dataset

logger = logging.getLogger("metricflow_platform.cli")


def _generate_sample_data(args: argparse.Namespace) -> int:
    dataset = generate_dataset(seed=args.seed)
    write_dataset(dataset, args.output_dir)
    return 0


def _init_db(args: argparse.Namespace) -> int:
    from metricflow_platform.database import connect, ensure_schema

    settings = load_settings()
    with connect(settings.database, attempts=10) as conn:
        ensure_schema(conn, settings.raw_schema)
    return 0


def _ingest(args: argparse.Namespace) -> int:
    from metricflow_platform.ingestion import run_ingestion

    run_ingestion(load_settings(), data_dir=args.data_dir)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="metricflow_platform", description="MetricFlow pipeline commands"
    )
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

    init_db = subcommands.add_parser("init-db", help="Create the raw schema and metadata tables")
    init_db.set_defaults(handler=_init_db)

    ingest = subcommands.add_parser("ingest", help="Validate source files and load them")
    ingest.add_argument("--data-dir", type=Path, default=None, help="Override METRICFLOW_DATA_DIR")
    ingest.set_defaults(handler=_ingest)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(args.log_level or os.environ.get("METRICFLOW_LOG_LEVEL", "INFO").upper())
    try:
        return args.handler(args)
    except Exception:
        logger.exception("command_failed command=%s", args.command)
        return 1


if __name__ == "__main__":
    sys.exit(main())
