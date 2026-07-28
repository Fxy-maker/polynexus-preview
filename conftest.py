"""Repository pytest defaults for bounded external test storage."""

from pathlib import Path

from scripts.test_storage import create_run_basetemp


def pytest_configure(config) -> None:
    """Use one external per-process basetemp unless the caller supplied one."""

    if getattr(config.option, "basetemp", None) is None:
        config.option.basetemp = str(create_run_basetemp(Path(__file__).resolve().parent))
