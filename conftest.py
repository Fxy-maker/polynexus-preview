"""Repository pytest defaults for bounded external test storage."""

from pathlib import Path

from scripts.test_storage import (
    begin_run_state,
    create_run_basetemp,
    finalize_run_state,
    resolve_retention_profile,
)


def pytest_configure(config) -> None:
    """Use one external per-process basetemp unless the caller supplied one."""

    if getattr(config.option, "basetemp", None) is not None:
        return
    project_root = Path(__file__).resolve().parent
    base = create_run_basetemp(project_root)
    config.option.basetemp = str(base)
    config._polynexus_run_state = begin_run_state(
        base,
        project_root=project_root,
        profile=resolve_retention_profile(),
    )
    config._polynexus_exit_code = None


def pytest_sessionfinish(session, exitstatus) -> None:
    """Remember pytest's terminal status for post-session cleanup."""

    if hasattr(session.config, "_polynexus_run_state"):
        session.config._polynexus_exit_code = int(exitstatus)


def pytest_unconfigure(config) -> None:
    """Finalize and, when safe, remove the agent-owned run directory."""

    state = getattr(config, "_polynexus_run_state", None)
    exit_code = getattr(config, "_polynexus_exit_code", None)
    if state is not None and exit_code is not None:
        finalize_run_state(state, exit_code=exit_code, process_active=False)
