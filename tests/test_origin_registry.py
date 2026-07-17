from polynexus.origin.registry import build_default_adapters, order_adapters


def test_registry_orders_injected_adapters_by_priority():
    class FakeAdapter:
        def __init__(self, adapter_id, priority):
            self.adapter_id = adapter_id
            self.priority = priority

    adapters = order_adapters(
        [
            FakeAdapter("package", 10),
            FakeAdapter("originpro", 100),
            FakeAdapter("com_labtalk", 80),
        ]
    )

    assert [adapter.adapter_id for adapter in adapters] == [
        "originpro",
        "com_labtalk",
        "package",
    ]


def test_default_registry_contains_all_three_adapters():
    adapters = build_default_adapters()

    assert [adapter.adapter_id for adapter in adapters] == [
        "originpro",
        "com_labtalk",
        "package",
    ]
