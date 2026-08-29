from pathlib import Path
from polynexus.suite.paper_contracts import FigurePlan
from polynexus.suite.figure_plans import render_figure_plan
from polynexus.suite.figure_quality import check_figure_quality

def test_svg_is_canonical_and_optional_assets(tmp_path: Path):
    plan=FigurePlan.create(title='curve', source_ids=('run-1',), x_label='Temperature', y_label='Signal', unit='a.u.', data=((0,1),(1,2)), outputs=('svg','json'))
    result=render_figure_plan(plan,tmp_path)
    assert result['svg'].endswith('.svg') and Path(result['svg']).is_file()
    assert Path(result['json']).is_file()
    quality=check_figure_quality(plan,result['svg'])
    assert quality['status']=='passed'

def test_quality_flags_missing_labels(tmp_path: Path):
    plan=FigurePlan.create(title='curve', data=((0,1),(1,2)))
    result=render_figure_plan(plan,tmp_path)
    assert check_figure_quality(plan,result['svg'])['status']=='review_required'
