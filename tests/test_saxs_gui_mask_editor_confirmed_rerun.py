from __future__ import annotations

import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
from PySide6.QtWidgets import QApplication

from polynexus.core.saxs_engine.config import SAXSConfig
from polynexus.core.saxs_engine.preprocess import preprocess_pipeline
from polynexus.gui.main_window_run_mixin import MainWindowRunMixin
from polynexus.gui.saxs_mask_edit_service import build_saxs_mask_edit_context
from polynexus.gui.widgets.saxs_mask_editor import SAXSDetectorMaskEditor


def _result(image, base_mask):
    return SimpleNamespace(
        raw_data={"img": image, "mask_edit_base_mask": base_mask},
    )


def test_single_image_preprocess_exposes_detached_base_mask(monkeypatch) -> None:
    import polynexus.core.saxs_engine.preprocess as preprocess_module

    image = np.zeros((3, 4), dtype=float)
    cfg = SAXSConfig(
        is_isotropic=True,
        analysis_priority="isotropic",
        dummy_val=0.0,
        ddummy=0.01,
        use_pyfai_integration=False,
    )
    monkeypatch.setattr(preprocess_module, "build_integrator", lambda _cfg: object())
    monkeypatch.setattr(
        preprocess_module,
        "integrate_full",
        lambda *_args, **_kwargs: (
            np.array([0.01, 0.02]),
            np.array([1.0, 2.0]),
        ),
    )

    result = preprocess_pipeline(image, cfg)

    base_mask = result["mask_edit_base_mask"]
    assert base_mask.dtype == bool
    assert base_mask.shape == image.shape
    assert base_mask is not np.asarray(image)
    assert bool(base_mask[0, 0]) is True


def test_mask_editor_context_is_static_single_2d_only() -> None:
    image = np.ones((4, 4), dtype=float)
    base_mask = np.zeros((4, 4), dtype=bool)
    result = _result(image, base_mask)

    context = build_saxs_mask_edit_context(
        result,
        technique="saxs",
        submodule_id="saxs.static",
        input_mode="single",
        source_path="sample.edf",
    )

    assert context is not None
    assert context.source_path == "sample.edf"
    assert context.image.shape == (4, 4)
    assert context.base_mask.shape == (4, 4)
    assert build_saxs_mask_edit_context(
        result,
        technique="saxs",
        submodule_id="saxs.temperature",
        input_mode="sequence",
        source_path="sample",
    ) is None
    assert build_saxs_mask_edit_context(
        _result(np.ones(8), base_mask),
        technique="saxs",
        submodule_id="saxs.static",
        input_mode="single",
        source_path="sample.dat",
    ) is None


def test_mask_editor_confirm_emits_validated_candidate_and_cancel_is_noop() -> None:
    app = QApplication.instance() or QApplication([])
    image = np.arange(16, dtype=float).reshape(4, 4)
    base_mask = np.zeros((4, 4), dtype=bool)
    editor = SAXSDetectorMaskEditor(image, base_mask, source_path="sample.edf")
    emitted: list[dict] = []
    editor.candidate_confirmed.connect(emitted.append)

    editor.canvas.set_cell_state(1, 2, True)
    editor._confirm_candidate()

    assert len(emitted) == 1
    assert emitted[0]["confirmed"] is True
    assert emitted[0]["operations"] == [[1, 2, True]]
    assert editor.result() == 1

    cancelled = SAXSDetectorMaskEditor(image, base_mask, source_path="sample.edf")
    cancelled_emitted: list[dict] = []
    cancelled.candidate_confirmed.connect(cancelled_emitted.append)
    cancelled.reject()
    app.processEvents()
    assert cancelled_emitted == []


def test_mask_editor_reset_returns_to_no_change_without_emitting() -> None:
    app = QApplication.instance() or QApplication([])
    editor = SAXSDetectorMaskEditor(
        np.ones((3, 3), dtype=float),
        np.zeros((3, 3), dtype=bool),
        source_path="sample.edf",
    )
    emitted: list[dict] = []
    editor.candidate_confirmed.connect(emitted.append)

    editor.canvas.set_cell_state(0, 0, True)
    editor.canvas.reset()
    editor._confirm_candidate()
    app.processEvents()

    assert editor.canvas.changed_pixel_count() == 0
    assert editor._confirm_button.isEnabled() is False
    assert emitted == []


def test_run_mixin_adds_candidate_only_for_confirmed_editor_action() -> None:
    class Harness:
        pass

    candidate = {"confirmed": True}
    kwargs = MainWindowRunMixin._analysis_worker_kwargs(
        Harness(),
        config=object(),
        submodule_id="saxs.static",
        mask_edit_candidate=candidate,
    )

    assert kwargs == {
        "config": kwargs["config"],
        "submodule_id": "saxs.static",
        "mask_edit_candidate": candidate,
    }
    assert "mask_edit_candidate" not in MainWindowRunMixin._analysis_worker_kwargs(
        Harness(),
        config=object(),
        submodule_id="saxs.static",
    )
