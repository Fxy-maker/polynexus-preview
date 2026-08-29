import json
from pathlib import Path
from polynexus.suite.paper_contracts import CitationRequest
from polynexus.suite.citations import render_citations, export_bibliography

def test_static_csl_render_without_zotero(tmp_path: Path):
    req=CitationRequest.create(key='smith2024',locator='doi:10/x',mode='static',metadata={'author':'Smith, J.','year':2024,'title':'Polymer study','journal':'J. Polym.'})
    result=render_citations((req,), zotero_available=False)
    assert result['mode']=='static'
    assert '[smith2024]' in result['inline']
    out=export_bibliography(tmp_path,(req,),result)
    assert Path(out['bib']).is_file() and Path(out['json']).is_file()

def test_dynamic_mode_preserves_keys():
    req=CitationRequest.create(key='k',locator='doi:x',mode='dynamic')
    result=render_citations((req,),zotero_available=True)
    assert result['mode']=='dynamic' and 'k' in result['inline']
