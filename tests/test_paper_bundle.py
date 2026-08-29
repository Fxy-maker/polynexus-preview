from pathlib import Path
from types import SimpleNamespace
from polynexus.suite.paper_source import build_paper_bundle

def test_bundle_contains_ranked_figures_and_source(monkeypatch,tmp_path: Path):
    svg=tmp_path/'a.svg'; svg.write_text('<svg width="100" height="80"></svg>')
    metric=SimpleNamespace(metric_id='m',technique='ftir',metric_key='peak',value=1,unit='a.u.',method='peak',source_locator='run',evidence_id='e',run_id='r',raw_source_hashes=(),status='completed',writing_eligibility='results_candidate',reason_codes=(),figures=('figures/a.svg',),tables=())
    ev=SimpleNamespace(evidence_id='e',technique='ftir',status='ready',source_runs=('r',),raw_sources=(),figures=('figures/a.svg',),tables=(),results_metric_ids=('m',),discussion_metric_ids=(),supported_interpretations=(),prohibited_conclusions=(),limitations=())
    fv=SimpleNamespace(id='a',svg='figures/a.svg',role='main',technique='ftir',status='ready')
    view=SimpleNamespace(package_id='p',version=1,metrics=(metric,),evidence=(ev,),figures=('figures/a.svg',),tables=(),limitations=(),human_review=(),figure_views=(fv,))
    monkeypatch.setattr('polynexus.suite.paper_source.load_evidence_package_view',lambda p:view)
    bundle=build_paper_bundle(tmp_path,tmp_path/'out')
    assert bundle['source']['package_id']=='p'
    assert bundle['figure_candidates'][0]['figure_id']
    assert Path(bundle['source_path']).is_file()
