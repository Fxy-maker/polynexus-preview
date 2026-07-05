"""Tests for persistent plot edit sidecars."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from polynexus.core.plot_edits import (
    apply_figure_edit,
    delete_style_preset,
    figure_output_root,
    figure_state_key,
    load_figure_annotations,
    load_figure_asset_spec,
    list_style_presets,
    load_style_preset,
    save_figure_annotations,
    save_figure_asset_spec,
    save_figure_edit,
    savefig_with_edits,
    save_style_preset,
    style_presets_path,
)


def test_figure_output_root_for_nested_saxs_paths(tmp_path):
    summary = tmp_path / "summary" / "Fig_1_overview.pdf"
    per_frame = tmp_path / "per_frame" / "frame_001" / "01_profile.pdf"
    figures = tmp_path / "figures" / "Fig-W1_profile.svg"

    assert figure_output_root(str(summary)) == tmp_path
    assert figure_output_root(str(per_frame)) == tmp_path
    assert figure_output_root(str(figures)) == tmp_path
    assert figure_state_key(str(per_frame)) == "per_frame/frame_001/01_profile.pdf"


def test_apply_figure_edit_updates_matplotlib_figure(tmp_path):
    path = tmp_path / "figures" / "edited.svg"
    path.parent.mkdir()
    save_figure_edit(
        str(path),
        {
            "title": "Edited",
            "xlabel": "Edited X",
            "ylabel": "Edited Y",
            "colour_scheme": "Warm",
            "font": "Large",
            "line_width": "Thick",
            "figure_size": "Square",
            "grid_on": False,
            "grid_alpha": 0.1,
            "bg_color": "#FFFFFF",
        },
    )

    fig, ax = plt.subplots()
    line, = ax.plot([0, 1], [0, 1])
    apply_figure_edit(fig, str(path))

    assert ax.get_title() == "Edited"
    assert ax.get_xlabel() == "Edited X"
    assert ax.get_ylabel() == "Edited Y"
    assert line.get_color() == "#8B0000"
    assert line.get_linewidth() == 2.0

    savefig_with_edits(fig, str(path))
    assert path.exists()
    assert (tmp_path / "plot_edits.json").exists()


def test_style_preset_round_trip_in_user_scope(tmp_path, monkeypatch):
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    path, name = save_style_preset(
        "Paper Light",
        {
            "colour_scheme": "Wong (SCI)",
            "font": "Small",
            "line_width": "Normal",
            "figure_size": "Small (4in)",
            "grid_on": False,
            "grid_alpha": 0.0,
            "bg_color": "#FFFFFF",
            "dpi": 150,
        },
    )

    assert name == "Paper Light"
    assert path == style_presets_path()
    assert list_style_presets() == ["Paper Light"]
    assert load_style_preset("Paper Light")["colour_scheme"] == "Wong (SCI)"
    assert delete_style_preset("Paper Light") is True
    assert list_style_presets() == []
    assert delete_style_preset("Missing") is False


def test_plot_edits_persist_annotations_and_asset_spec(tmp_path):
    path = tmp_path / "figures" / "edited.png"
    path.parent.mkdir()
    annotation = {
        "id": "ann-001",
        "type": "text",
        "x": 0.25,
        "y": 0.5,
        "text": "alpha peak",
    }
    asset_spec = {
        "figure_id": "edited",
        "sidecar_key": "figures/edited.png",
        "master_path": str((tmp_path / "figures" / "edited.svg").resolve()),
        "preview_path": str(path.resolve()),
        "available_formats": ["png", "svg"],
    }

    save_figure_annotations(str(path), [annotation])
    save_figure_asset_spec(str(path), asset_spec)
    save_figure_edit(str(path), {"font": "Small"})

    assert load_figure_annotations(str(path)) == [annotation]
    assert load_figure_asset_spec(str(path)) == asset_spec
    assert (tmp_path / "plot_edits.json").exists()
