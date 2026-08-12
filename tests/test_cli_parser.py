from polynexus.cli.parser import build_parser, parse_args


def test_cli_parser_exposes_primary_entry_points():
    parser = build_parser()

    assert parser.prog == "polynexus"

    batch = parser.parse_args(["batch", "data", "--technique", "saxs"])
    assert batch.cmd == "batch"
    assert batch.input_dir == "data"
    assert batch.technique == "saxs"

    tune = parse_args(["ai-tune", "--file", "sample.edf", "--polymer", "PA6"])
    assert tune.cmd == "ai-tune"
    assert tune.file == "sample.edf"
    assert tune.polymer == "PA6"

    single = parser.parse_args(["waxs", "sample.raw"])
    assert single.cmd == "waxs"
    assert single.input == "sample.raw"

    workflow = parser.parse_args(["agent-workflow", "inspect", "--manifest", "tpae.json"])
    assert workflow.cmd == "agent-workflow"
    assert workflow.operation == "inspect"
