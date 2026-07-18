from polynexus.origin.capability_probe import OriginCapabilityProbe


def test_probe_is_unavailable_without_windows(monkeypatch):
    monkeypatch.setattr(
        "polynexus.origin.capability_probe.platform.system",
        lambda: "Linux",
    )

    report = OriginCapabilityProbe().probe()

    assert report.installed is False
    assert report.com_available is False
    assert "Windows" in report.reason


def test_probe_reports_optional_integrations_independently(monkeypatch):
    monkeypatch.setattr(
        "polynexus.origin.capability_probe.platform.system",
        lambda: "Windows",
    )
    report = OriginCapabilityProbe(
        installation_finder=lambda: (True, "2026.1"),
        com_server_finder=lambda: True,
        module_finder=lambda name: name == "originpro" or name == "win32com.client",
    ).probe()

    assert report.installed is True
    assert report.version == "2026.1"
    assert report.originpro_available is True
    assert report.com_available is True


def test_probe_catches_finder_errors(monkeypatch):
    monkeypatch.setattr(
        "polynexus.origin.capability_probe.platform.system",
        lambda: "Windows",
    )

    def broken_finder():
        raise OSError("registry unavailable")

    report = OriginCapabilityProbe(installation_finder=broken_finder).probe()

    assert report.installed is False
    assert "registry unavailable" in report.reason
