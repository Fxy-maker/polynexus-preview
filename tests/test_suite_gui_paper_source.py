from polynexus.gui.suite_manager_adapter import SuiteManagerAdapter

def test_gui_adapter_exposes_manuscript_source(monkeypatch):
    monkeypatch.setattr('polynexus.gui.suite_manager_adapter.build_manuscript_source', lambda p,b=None: type('S',(),{'to_dict':lambda self:{'source_id':'s'}})())
    assert SuiteManagerAdapter.manuscript_source('pkg')['source_id']=='s'
