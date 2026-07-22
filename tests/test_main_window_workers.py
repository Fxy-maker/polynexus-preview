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


def test_analysis_and_batch_workers_expose_cooperative_lifecycle_signals() -> None:
    analysis = AnalysisWorker("saxs", "sample.edf", "out")
    batch = BatchWorker("saxs", ["sample.edf"], "out")

    assert hasattr(analysis, "stage")
    assert hasattr(analysis, "cancelled")
    assert hasattr(batch, "stage")
    assert hasattr(batch, "cancelled")
    analysis.cancel()
    batch.cancel()
    assert analysis._cancel_requested is True
    assert batch._cancel_requested is True
