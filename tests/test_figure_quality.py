from polynexus.suite.paper_contracts import FigurePlan
from polynexus.suite.figure_quality import check_svg_quality

def test_quality_detects_clipping_and_missing_units(tmp_path):
    p=tmp_path/'bad.svg'; p.write_text('<svg width="10" height="10"><text>cut</text></svg>')
    result=check_svg_quality(p, required_labels=('X [C]',))
    assert result['status']=='review_required'
    assert result['issues']
