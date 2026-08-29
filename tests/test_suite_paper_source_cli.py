import json
from types import SimpleNamespace
from polynexus.cli.parser import build_parser
from polynexus.cli import run_suite_service

def test_parser_exposes_manuscript_source():
    args=build_parser().parse_args(['suite','manuscript-source','--package','pkg','--output','out.json'])
    assert args.operation=='manuscript-source' and args.output=='out.json'

def test_cli_manuscript_source_writes_shared_dto(monkeypatch,tmp_path, capsys):
    class Source:
        def to_dict(self): return {'version':1,'source_id':'s','package_id':'p'}
    monkeypatch.setattr(run_suite_service,'build_manuscript_source',lambda p,b=None: Source())
    out=tmp_path/'source.json'
    code=run_suite_service.run_suite(SimpleNamespace(operation='manuscript-source',package='pkg',brief=None,output=str(out),manifest=None,codex_skills_dir=None,lock=None))
    assert code==0 and json.loads(out.read_text())['source_id']=='s'
