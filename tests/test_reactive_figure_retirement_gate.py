from polynexus.core.figures.retirement_gate import evaluate_legacy_retirement


def test_retirement_gate_blocks_when_inventory_has_legacy_or_candidate_routes():
    result = evaluate_legacy_retirement(
        {
            "saxs.temperature": "v2_preview_ready",
            "ir": "adapter_candidate",
            "dsc": "legacy_object",
            "legacy_images": "static_compat",
        },
        {"saxs.temperature": True, "ir": False, "dsc": False, "legacy_images": True},
    )

    assert not result.eligible
    assert "route_not_ready:ir:adapter_candidate" in result.blockers
    assert "route_not_ready:dsc:legacy_object" in result.blockers
    assert "review_pending:ir" in result.blockers


def test_retirement_gate_allows_removal_only_after_default_and_review_gates():
    result = evaluate_legacy_retirement(
        {
            "saxs.temperature": "v2_default",
            "legacy_images": "static_compat",
        },
        {"saxs.temperature": True, "legacy_images": True},
    )

    assert result.eligible
    assert result.blockers == ()


def test_approved_reactive_figure_inventory_is_route_convergence_eligible():
    inventory = {
        "saxs.temperature": "v2_default",
        "saxs.strain": "v2_default",
        "saxs.static": "v2_default",
        "dsc": "v2_default",
        "ir": "v2_default",
        "waxs.static": "v2_default",
        "waxs.temperature": "v2_default",
        "waxs.strain": "v2_default",
        "nmr": "v2_default",
        "legacy.image": "static_compat",
    }

    result = evaluate_legacy_retirement(
        inventory,
        {route: True for route in inventory},
    )

    assert result.eligible
    assert result.blockers == ()
