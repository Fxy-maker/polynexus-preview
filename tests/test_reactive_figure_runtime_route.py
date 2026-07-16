from polynexus.core.figures.runtime_route import resolve_runtime_route


def test_runtime_route_keeps_v2_ready_entry_on_legacy_until_default_gate_is_enabled():
    route = resolve_runtime_route(
        {
            "v2_runtime": "ready",
            "v2_default": False,
            "editing_mode": "object",
            "object_editing": True,
        }
    )

    assert route.name == "legacy_object"
    assert route.reason_code == "v2_default_disabled"


def test_runtime_route_selects_v2_only_with_explicit_ready_default_capability():
    route = resolve_runtime_route(
        {
            "v2_runtime": "ready",
            "v2_default": True,
            "v2_reviewed": True,
            "editing_mode": "object",
            "object_editing": True,
        }
    )

    assert route.name == "reactive_v2"
    assert route.reason_code == "v2_default_enabled"


def test_runtime_route_keeps_unreviewed_v2_default_on_legacy():
    route = resolve_runtime_route(
        {
            "v2_runtime": "ready",
            "v2_default": True,
            "v2_reviewed": False,
            "editing_mode": "object",
            "object_editing": True,
        }
    )

    assert route.name == "legacy_object"
    assert route.reason_code == "v2_default_review_pending"
    assert route.v2_ready is True


def test_runtime_route_preserves_static_compatibility_for_non_object_entries():
    route = resolve_runtime_route(
        {
            "v2_runtime": "static_fallback",
            "v2_default": False,
            "editing_mode": "static",
            "object_editing": False,
        }
    )

    assert route.name == "static_compat"
    assert route.reason_code == "static_capability"
