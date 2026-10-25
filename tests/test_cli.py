from metricflow_platform.cli import build_parser


def test_dbt_arguments_are_passed_through_unchanged():
    args = build_parser().parse_args(["dbt", "build", "--select", "staging", "--fail-fast"])

    assert args.command == "dbt"
    assert args.dbt_args == ["build", "--select", "staging", "--fail-fast"]


def test_ingest_accepts_data_dir_override(tmp_path):
    args = build_parser().parse_args(["ingest", "--data-dir", str(tmp_path)])

    assert args.data_dir == tmp_path
