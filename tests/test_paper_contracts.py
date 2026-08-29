import pytest

from polynexus.suite.paper_contracts import (
    PaperBrief, ClaimRecord, FigurePlan, CitationRequest, ManuscriptSource,
    PreflightReport, InputRequest, FormulaRecord, stable_id,
)

def test_contracts_round_trip_and_stable_ids():
    brief = PaperBrief.create(research_question="How does treatment affect crystallinity?", title_hint="PA6")
    claim = ClaimRecord.create(text="Crystallinity increases.", evidence_ids=("ev-1",), metric_ids=("m-1",))
    figure = FigurePlan.create(title="DSC comparison", source_ids=("run-1",), layout="overlay")
    citation = CitationRequest.create(key="smith2024", locator="doi:10.1/x", mode="auto")
    source = ManuscriptSource.create(package_id="pkg-1", claim_ids=(claim.claim_id,), figure_plan_ids=(figure.figure_id,), citation_ids=(citation.citation_id,))
    report = PreflightReport.create(source_id=source.source_id, errors=(), warnings=("review_required",))
    for item in (brief, claim, figure, citation, source, report):
        restored = type(item).from_dict(item.to_dict())
        assert restored == item
        assert restored.version == 1
        assert restored.schema_version == 1
        assert restored.object_id
    assert stable_id("claim", {"text": "x"}) == stable_id("claim", {"text": "x"})

def test_adaptive_input_only_for_material_ambiguity():
    brief = PaperBrief.create(research_question="question")
    assert brief.status == "draft"
    assert brief.needs_input == ()
    request = InputRequest.create(reason="sample_group_ambiguous", message="Choose a group", fields=("group",), material=True)
    waiting = PaperBrief.create(research_question="question", needs_input=(request,))
    assert waiting.status == "needs_input"
    assert InputRequest.from_dict(request.to_dict()) == request

def test_contracts_reject_invalid_version_and_unbound_claim():
    with pytest.raises(ValueError):
        PaperBrief.from_dict({"version": 2, "research_question": "q"})
    with pytest.raises(ValueError):
        ClaimRecord.create(text="", evidence_ids=())
    with pytest.raises(ValueError):
        CitationRequest.create(key="", locator="doi:x")
def test_formula_record_validates_units_and_roundtrips():
    f=FormulaRecord.create(expression='X=(A-A0)/(Ainf-A0)', variables={'A':'signal','A0':'signal'}, units={'A':'J/g'}, source='method:avrami')
    assert FormulaRecord.from_dict(f.to_dict())==f
    assert f.source and f.formula_id
