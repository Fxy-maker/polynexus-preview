from types import SimpleNamespace

from polynexus.cli.batch_preset_service import (
    batch_cli_overrides_from_args,
    batch_preset_values_from_args,
    describe_batch_task,
)


def test_batch_preset_values_from_args_normalizes_defaults():
    args = SimpleNamespace(
        input_dir=None,
        technique="saxs",
        pattern=None,
        workers=None,
        output_dir="",
    )

    assert batch_preset_values_from_args(args) == {
        "input_dir": "",
        "technique": "saxs",
        "pattern": "*",
        "workers": 1,
        "output_dir": "",
    }


def test_batch_cli_overrides_from_args_skips_default_values():
    args = SimpleNamespace(
        input_dir="",
        technique="waxs",
        pattern="*",
        workers=1,
        output_dir=None,
    )

    assert batch_cli_overrides_from_args(args) == {"technique": "waxs"}


def test_describe_batch_task_formats_compact_summary():
    values = {
        "technique": "ir",
        "input_dir": "inputs",
        "pattern": "*.csv",
        "output_dir": "out",
        "workers": 4,
    }

    assert describe_batch_task(values) == (
        "technique=ir, input_dir=inputs, pattern=*.csv, output_dir=out, workers=4"
    )
