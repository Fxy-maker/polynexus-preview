from __future__ import annotations

from pathlib import Path

import pytest


def test_real_zero_five_percent_replay_requires_external_reviewed_fixture() -> None:
    """Keep real-data acceptance read-only and explicit about missing EDFs."""

    project_root = Path(__file__).resolve().parents[1]
    source = project_root / "测试数据" / "saxs" / "PAD8原位拉伸"
    edf_files = sorted(source.rglob("*.edf")) if source.exists() else []
    if not edf_files:
        pytest.skip(
            "external zero/five-percent EDF fixture unavailable; "
            "mount the reviewed read-only bundle before replay"
        )

    # The fixture is intentionally not guessed from filenames. A reviewed
    # zero/five-percent mapping is required before any cross-frame claim.
    pytest.skip(
        f"reviewed zero/five-percent mapping required for {len(edf_files)} EDF files"
    )
