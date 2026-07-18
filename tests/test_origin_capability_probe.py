from pathlib import Path

from polynexus.origin import capability_probe
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


def test_candidate_paths_use_user_registry_when_process_environment_is_stale(monkeypatch):
    configured_path = Path(r"D:\Program Files\OriginLab\Origin2026\Origin64.exe")
    monkeypatch.delenv("ORIGIN_EXE", raising=False)
    monkeypatch.setattr(capability_probe.platform, "system", lambda: "Windows")
    monkeypatch.setattr(capability_probe, "_read_user_origin_exe", lambda: str(configured_path))
    monkeypatch.setenv("ProgramFiles", "")
    monkeypatch.setenv("ProgramFiles(x86)", "")

    candidates = capability_probe._candidate_origin_paths()

    assert configured_path in candidates
