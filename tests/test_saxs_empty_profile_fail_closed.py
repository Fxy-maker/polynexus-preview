import numpy as np

from polynexus.core.saxs_engine.config import SAXSConfig
from polynexus.core.saxs_engine.core import analyze_single


def test_empty_profile_returns_unusable_structured_result_and_provenance():
    result = analyze_single(
        [],
        [],
        SAXSConfig(),
        source_id="frame-empty",
        raw_data_ref="raw/frame-empty.edf",
    )

    assert result.q.size == 0
    assert result.I.size == 0
    assert result.I_smooth.size == 0
    assert result.long_period is not None
    assert result.structure is not None
    assert result.metric_evidence == {}

    assert result.data_quality_report["level"] == "Unusable"
    assert result.data_quality_report["source_id"] == "frame-empty"
    assert result.data_quality_report["raw_data_ref"] == "raw/frame-empty.edf"
    assert result.data_quality_report["actions"] == []
    assert result.guinier_evidence["level"] == "Unusable"
    assert result.guinier_evidence["metric"]["data_quality_ref"] == "frame-empty"

    assert np.asarray(result.q).size == 0
