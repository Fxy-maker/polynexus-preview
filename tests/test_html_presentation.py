import re
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
    assert slide_count == 46
    assert html.count("data-chapter=") == 46
    assert html.count("data-visual=") == 46
    assert html.count("data-notes=") == 46
    assert "SAXS" in html
    assert "DSC" in html
    assert "WAXS" in html
    assert "IR" in html
    assert "NMR" in html

    chapter_counts = {
        chapter: html.count(f'data-chapter="{chapter}"')
        for chapter in (
            "01 / WHY POLYNEXUS",
            "02 / SAXS DEEP DIVE",
            "03 / SEQUENCE AND 2D",
            "04 / FIVE TECHNIQUES",
            "05 / AI ADVISOR",
        )
    }
    assert chapter_counts == {
        "01 / WHY POLYNEXUS": 7,
        "02 / SAXS DEEP DIVE": 20,
        "03 / SEQUENCE AND 2D": 6,
        "04 / FIVE TECHNIQUES": 6,
        "05 / AI ADVISOR": 7,
    }

    for term in (
        "q = 4π sinθ / λ",
        "Guinier",
        "Porod",
        "Bragg",
        "Lorentz",
        "IDF",
        "invariant",
        "background subtraction",
        "temperature",
        "strain",
        "azimuthal",
        "DSC",
        "WAXS",
        "IR",
        "NMR",
        "fit quality",
        "parameter stability",
        "physical plausibility",
        "data quality",
        "flow-ribbon",
        "ensureFlowRibbons",
        "updateFlowRibbon",
        "lecture-enter",
        "process-sweep",
    ):
        assert term in html

    assert "@media (prefers-reduced-motion: reduce)" in html
    assert "lecture-slide .flow-ribbon" in html


def test_saxs_method_slides_have_distinct_model_scope():
    html = PRESENTATION.read_text(encoding="utf-8")

    expected_by_slide = {
        "17 / 46": ("LOW / MID / HIGH Q", "model map"),
        "18 / 46": ("Guinier", "Rg"),
        "19 / 46": ("I(0)", "window stability"),
        "20 / 46": ("Porod", "assumption"),
        "21 / 46": ("Porod exponent", "restriction"),
        "22 / 46": ("Bragg", "d = 2π/q*"),
        "23 / 46": ("Lorentz", "correction"),
        "24 / 46": ("correlation function", "IDF"),
        "25 / 46": ("invariant Q", "integral"),
        "26 / 46": ("cross-method", "matrix"),
        "27 / 46": ("quality state", "fail closed"),
    }

    for slide_no, terms in expected_by_slide.items():
        match = re.search(
            rf'<section class="slide [^>]*>.*?<div class="slide-no">{re.escape(slide_no)}</div>',
            html,
            flags=re.DOTALL,
        )
        assert match, slide_no
        slide = match.group(0)
        for term in terms:
            assert term.lower() in slide.lower(), (slide_no, term)


def test_opening_introduces_product_before_the_saxs_map():
    html = PRESENTATION.read_text(encoding="utf-8")
    opening_claims = (
        "PolyNexus<br><span>从数据到证据</span>",
        "DSC · WAXS · SAXS · IR · NMR",
        "同一份样品，<br>从五种入口进入分析。",
        "从原始数据到论文图表",
        "为什么需要它？",
        "PolyNexus 的核心思路",
        "接下来，<br>我们先把 <span>SAXS</span> 讲透。",
    )

    positions = [html.index(claim) for claim in opening_claims]
    assert positions == sorted(positions)
    assert "data <span>→</span> models <span>→</span> quality <span>→</span> figures" in html


def test_saxs_chapter_explains_processing_methods_and_quality_boundaries():
    html = PRESENTATION.read_text(encoding="utf-8")

    for term in (
        "CSV / DAT / TXT / XY",
        "pyFAI",
        "manual integration",
        "transmission / thickness",
        "Savitzky-Golay",
        "beamstop",
        "q-window",
        "simulated teaching data",
        "ideal curve",
        "problem curve",
        "background drift",
        "peak overlap",
        "Quantitative",
        "Trend",
        "Diagnostic",
        "Unusable",
        "Q_star_valid",
        "sasmodels",
    ):
        assert term in html


def test_ai_chapter_explains_bounded_advisor_and_review_flow():
    html = PRESENTATION.read_text(encoding="utf-8")

    for term in (
        "AI Advisor",
        "LLM API",
        "RAG",
        "Chroma / BM25",
        "deterministic orchestrator",
        "PreprocessIntent",
        "shadow",
        "confirm-only",
        "keep_original",
        "user confirmation",
        "reference_cases",
        "offline mock",
    ):
        assert term in html


def test_presentation_exposes_narration_navigation_and_motion_safety():
    html = PRESENTATION.read_text(encoding="utf-8")

    assert "ArrowRight" in html
    assert "touchstart" in html
    assert "prefers-reduced-motion" in html
    assert "data-notes" in html
    assert "data-caption" in html
    assert "fit quality" in html
    assert "physical plausibility" in html


def test_presentation_has_recording_and_presenter_mode_controls():
    html = PRESENTATION.read_text(encoding="utf-8")

    for term in (
        'id="fullscreen"',
        'id="speakerMode"',
        'id="presenterShell"',
        'id="presenterCurrent"',
        'id="presenterNext"',
        'id="presenterNotes"',
        'id="presenterPrev"',
        'id="presenterNextButton"',
        "requestFullscreen",
        "fullscreenchange",
        "openPresenterMode",
        "BroadcastChannel",
        "presenter=1",
        "recording-mode",
        "presenter-ready",
        "presenter-command",
        "requestPresenterMove",
        "SPEAKER_NOTES",
        "getSpeakerNotes",
        "2.3fr",
        "minmax(150px, .48fr)",
    ):
        assert term in html
