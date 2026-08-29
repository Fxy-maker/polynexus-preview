import json
from pathlib import Path
from polynexus.suite.paper_contracts import FigurePlan
from polynexus.suite.figure_review import rank_figure_candidates, save_review_decisions

def test_rank_and_persist_human_decisions(tmp_path: Path):
    good=FigurePlan.create(title='good',source_ids=('run',),x_label='x',y_label='y',data=((0,0),(1,1)))
    bad=FigurePlan.create(title='bad')
    ranked=rank_figure_candidates((good,bad))
    assert ranked[0]['figure_id']==good.figure_id
    out=save_review_decisions(tmp_path, [(good.figure_id,'selected','looks clear')])
    payload=json.loads(Path(out).read_text())
    assert payload['decisions'][0]['decision']=='selected'

def test_diagnostic_cannot_be_selected():
    p=FigurePlan.create(title='diag',source_ids=())
    ranked=rank_figure_candidates((p,))
    assert ranked[0]['eligible'] is False
