from types import SimpleNamespace
from polynexus.suite.paper_source import build_manuscript_source

def test_bridge_projects_existing_metrics_without_recompute(monkeypatch, tmp_path):
    metric=SimpleNamespace(metric_id='m1',technique='dsc',metric_key='Tm',value=185.0,unit='C',method='peak',source_locator='run.json',evidence_id='e1',run_id='r1',raw_source_hashes=('h',),status='completed',writing_eligibility='results_candidate',reason_codes=(),figures=('figures/a.svg',),tables=('tables/t.csv',))
    ev=SimpleNamespace(evidence_id='e1',technique='dsc',status='ready',source_runs=('r1',),raw_sources=('raw.csv',),figures=('figures/a.svg',),tables=('tables/t.csv',),results_metric_ids=('m1',),discussion_metric_ids=(),supported_interpretations=('melting',),prohibited_conclusions=('causality',),limitations=('single run',))
    view=SimpleNamespace(package_id='pkg',version=1,metrics=(metric,),evidence=(ev,),figures=('figures/a.svg',),tables=('tables/t.csv',),limitations=('limit',),human_review=(),figure_views=())
    monkeypatch.setattr('polynexus.suite.paper_source.load_evidence_package_view', lambda p:view)
    source=build_manuscript_source(tmp_path)
    assert source.package_id == 'pkg'
    assert source.projection['metrics'][0]['value'] == 185.0
    assert source.projection['claims'][0]['metric_ids'] == ['m1']
    assert source.limitations == ('limit','single run')
