from __future__ import annotations

from polynexus.gui.workspace_context import (
    WorkspaceContext,
    WorkspaceResultStatus,
)


def test_context_normalizes_identity_fields_and_builds_stable_key():
    context = WorkspaceContext(
        technique=" SAXS ",
        submodule=" saxs.temperature ",
        source_path="D:/run/sample.edf",
        input_mode=" sequence ",
        output_dir="D:/run/polynexus_output",
    )

    assert context.technique == "saxs"
    assert context.submodule == "saxs.temperature"
    assert context.input_mode == "sequence"
    assert context.identity_key == (
        "saxs",
        "saxs.temperature",
        "d:/run/sample.edf",
        "sequence",
        "d:/run/polynexus_output",
    )


def test_result_context_is_current_only_for_same_identity_and_run():
    active = WorkspaceContext(
        technique="saxs",
        source_path="D:/run/sample.edf",
        output_dir="D:/run/polynexus_output",
        run_id="run-1",
        result_status=WorkspaceResultStatus.COMPLETE,
    )
    same = active.with_result(run_id="run-1")
    other_run = active.with_result(run_id="run-2")
    other_source = active.with_source("D:/run/other.edf")

    assert active.result_matches(same)
    assert not active.result_matches(other_run)
    assert not active.result_matches(other_source)
    assert other_run.result_status is WorkspaceResultStatus.STALE


def test_empty_and_cancelled_contexts_have_explicit_status():
    assert WorkspaceContext.empty().result_status is WorkspaceResultStatus.EMPTY
    cancelled = WorkspaceContext.empty().with_result(
        run_id="run-cancelled",
        result_status=WorkspaceResultStatus.CANCELLED,
    )
    assert cancelled.result_status is WorkspaceResultStatus.CANCELLED
