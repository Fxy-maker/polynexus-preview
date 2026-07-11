import json
from dataclasses import asdict

from polynexus.utils.config import GlobalConfig, ProjectConfig


def test_global_config_uses_one_complete_figure_output_profile():
    payload = asdict(GlobalConfig())

    assert payload["figure_output_profile"] == "paper_complete"
    assert "figure_format" not in payload
    assert "figure_dpi" not in payload


def test_project_config_ignores_legacy_figure_format_inputs(tmp_path):
    path = tmp_path / "legacy-config.json"
    path.write_text(
        json.dumps(
            {
                "global": {
                    "figure_format": "png",
                    "figure_dpi": 72,
                    "figure_output_profile": "paper_complete",
                },
                "saxs": {
                    "figure_format": "svg",
                    "figure_dpi": 150,
                },
                "ir": {
                    "fig_format": "pdf",
                    "fig_dpi": 300,
                },
            }
        ),
        encoding="utf-8",
    )

    config = ProjectConfig.from_json(str(path))

    assert config.global_cfg.figure_output_profile == "paper_complete"
    assert not hasattr(config.global_cfg, "figure_format")
    assert not hasattr(config.global_cfg, "figure_dpi")
    assert not hasattr(config.saxs, "figure_format")
    assert not hasattr(config.ir, "fig_format")
