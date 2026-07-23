from polynexus.gui.run_state_service import (
    RunState,
    RunStatus,
    should_publish_result,
    transition_run_state,
)


def test_run_state_transitions_from_idle_to_cancelled():
    state = transition_run_state(RunState(), "start")
    assert state.status is RunStatus.RUNNING

    state = transition_run_state(state, "cancel")
    assert state.status is RunStatus.CANCELLING

    state = transition_run_state(state, "cancelled")
    assert state.status is RunStatus.CANCELLED
    assert should_publish_result(state) is False


def test_run_state_transitions_running_to_failed():
    state = transition_run_state(RunState(RunStatus.RUNNING), "fail")

    assert state.status is RunStatus.FAILED
    assert should_publish_result(state) is False


def test_completed_run_is_the_only_terminal_state_that_publishes_results():
    state = transition_run_state(RunState(RunStatus.RUNNING), "complete")

    assert state.status is RunStatus.COMPLETE
    assert should_publish_result(state) is True
