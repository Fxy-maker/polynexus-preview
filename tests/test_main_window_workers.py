from __future__ import annotations

import importlib
import importlib.util

from polynexus.gui.main_window import (
    AITuneSignals,
    AITuneWorker,
    AnalysisWorker,
    BatchWorker,
    JointHubWorker,
)


def test_main_window_reuses_worker_classes_from_dedicated_workers_module() -> None:
    spec = importlib.util.find_spec("polynexus.gui.main_window_workers")
    assert spec is not None

    module = importlib.import_module("polynexus.gui.main_window_workers")

    assert AnalysisWorker is module.AnalysisWorker
    assert BatchWorker is module.BatchWorker
    assert JointHubWorker is module.JointHubWorker
    assert AITuneSignals is module.AITuneSignals
    assert AITuneWorker is module.AITuneWorker
