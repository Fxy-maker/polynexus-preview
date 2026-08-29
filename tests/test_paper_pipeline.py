from polynexus.suite.paper_contracts import ManuscriptSource, ClaimRecord, FigurePlan, CitationRequest, FormulaRecord
from polynexus.suite.paper_pipeline import assemble_manuscript
from polynexus.suite.preflight import preflight_manuscript

def test_pipeline_assembles_and_preflights():
    c=ClaimRecord.create(text='A claim',evidence_ids=('e',),metric_ids=('m',))
    f=FigurePlan.create(title='fig',source_ids=('fig.svg',),x_label='x',y_label='y',data=((0,0),(1,1)))
    s=ManuscriptSource.create(package_id='p',claim_ids=(c.claim_id,),figure_plan_ids=(f.figure_id,))
    result=assemble_manuscript(s,(c,),(f,),())
    assert result['sections'] and result['claims'][0]['claim_id']==c.claim_id
    report=preflight_manuscript(result)
    assert report.status in {'passed','review_required'}
from pathlib import Path
from polynexus.suite.paper_pipeline import export_manuscript

def test_export_writes_reviewable_markdown(tmp_path: Path):
    out=export_manuscript({'package_id':'p','sections':[{'name':'Results','claim_ids':[]}],'claims':[],'figures':[],'citations':[],'formulas':[],'limitations':[]},tmp_path)
    assert Path(out['markdown']).is_file() and Path(out['json']).is_file()
