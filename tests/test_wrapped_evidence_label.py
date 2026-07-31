import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QSizePolicy

from polynexus.gui.widgets.wrapped_evidence_label import WrappedEvidenceLabel


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_long_evidence_keeps_height_for_width_when_results_shrink_policy_is_applied() -> None:
    _app()
    source = (
        "Assignment readiness | assignment_limited | Assignment source | generic_region | "
        "Axis | source=default_range | units=ppm | calibrated=false | Vendor axis | x/1 | "
        "Carbon13 | origin x_offset=100 ppm | sweep x span=20000 Hz"
    )
    label = WrappedEvidenceLabel()
    label.setWordWrap(True)
    label.setText(source)
    label.setMinimumWidth(0)
    label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)

    assert label.text() == source
    assert label.hasHeightForWidth()
    assert label.heightForWidth(320) > label.heightForWidth(960)
