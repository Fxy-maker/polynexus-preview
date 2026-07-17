from polynexus.core.figure_edit_capabilities import capabilities_for


def test_line_capabilities_expose_line_editing_but_not_text_editing():
    capabilities = capabilities_for({"id": "line-1", "type": "line"})

    assert capabilities.style is True
    assert capabilities.color is True
    assert capabilities.line_style is True
    assert capabilities.geometry is True
    assert capabilities.text is False


def test_capabilities_cover_supported_objects_and_keep_unknown_conservative():
    text = capabilities_for({"type": "text"})
    series = capabilities_for({"type": "plot_series"})
    background = capabilities_for({"type": "image_background"})
    legend = capabilities_for({"type": "legend"})
    unknown = capabilities_for({"type": "vendor_extension"})

    assert text.text and text.font_size and text.deletable and text.reorderable
    assert series.marker and series.marker_size and series.line_width
    assert background.crop and background.locked
    assert not background.deletable and not background.reorderable
    assert legend.geometry and legend.text and legend.deletable
    assert unknown == capabilities_for({"type": "unknown"})
    assert not any(unknown.__dict__.values())


def test_explicitly_locked_editable_object_has_no_mutating_capabilities():
    capabilities = capabilities_for({"type": "line", "locked": True})

    assert capabilities.locked is True
    assert capabilities.style is False
    assert capabilities.geometry is False
    assert capabilities.deletable is False
    assert capabilities.reorderable is False


def test_color_validation_accepts_hex_and_matplotlib_named_colors():
    from polynexus.core.figure_edit_capabilities import is_valid_color

    assert is_valid_color("#12AbEF")
    assert is_valid_color("tab:blue")
    assert is_valid_color("rebeccapurple")
    assert not is_valid_color("bad")
    assert not is_valid_color("NaN")
