from polynexus.gui.figure_annotations import (
    load_annotations_from_entry,
    normalize_annotation_payload,
    save_annotations_to_entry,
)


def test_annotation_state_round_trip():
    entry = {"style": {"font": "Small"}}
    annotations = [
        {
            "id": "ann-001",
            "type": "text",
            "x": 0.25,
            "y": 0.5,
            "text": "alpha peak",
            "font_size": 12,
            "color": "#111111",
        }
    ]

    updated = save_annotations_to_entry(entry, annotations)

    assert updated["style"] == {"font": "Small"}
    assert load_annotations_from_entry(updated) == annotations


def test_missing_annotations_loads_as_empty_list():
    assert load_annotations_from_entry({}) == []
    assert load_annotations_from_entry({"annotations": "bad"}) == []


def test_unknown_annotation_type_is_preserved_but_marked_unknown():
    annotation = normalize_annotation_payload(
        {"id": "ann-x", "type": "callout", "x": 0.1, "y": 0.2, "text": "note"}
    )

    assert annotation["id"] == "ann-x"
    assert annotation["type"] == "unknown"
    assert annotation["original_type"] == "callout"
    assert annotation["text"] == "note"
