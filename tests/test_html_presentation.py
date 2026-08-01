from pathlib import Path


PRESENTATION = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "presentations"
    / "polynexus-overview.html"
)


def test_presentation_has_a_fixed_stage_and_complete_slide_story():
    html = PRESENTATION.read_text(encoding="utf-8")

    assert html.lstrip().lower().startswith("<!doctype html>")
    assert 'class="deck-viewport"' in html
    assert 'class="deck-stage"' in html
    slide_count = html.count('class="slide ')
    assert 18 <= slide_count <= 20
    assert "SAXS" in html
    assert "DSC" in html
    assert "WAXS" in html
    assert "IR" in html
    assert "NMR" in html


def test_presentation_exposes_narration_navigation_and_motion_safety():
    html = PRESENTATION.read_text(encoding="utf-8")

    assert "ArrowRight" in html
    assert "touchstart" in html
    assert "prefers-reduced-motion" in html
    assert "data-notes" in html
    assert "data-caption" in html
    assert "fit quality" in html
    assert "physical plausibility" in html
