from polynexus.gui.chart_editor_capability_service import descriptor_for_editor_mode


def test_editor_capabilities_distinguish_object_and_static_modes():
    object_mode = descriptor_for_editor_mode("EDITOR_MODE_OBJECT")
    static_mode = descriptor_for_editor_mode("EDITOR_MODE_STATIC")

    assert object_mode is not None and object_mode.editable_objects is True
    assert static_mode is not None and static_mode.editable_objects is False
    assert static_mode.crop is True


def test_unknown_editor_mode_has_no_capability_claim():
    assert descriptor_for_editor_mode("unknown") is None
