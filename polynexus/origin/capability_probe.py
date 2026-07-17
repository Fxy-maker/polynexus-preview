"""Non-invasive detection of OriginLab and optional automation capabilities."""

from __future__ import annotations

import importlib.util
import os
import platform
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


ORIGIN_COM_PROGIDS = ("Origin.ApplicationSI", "Origin.Application")


@dataclass(frozen=True)
class OriginCapability:
    installed: bool
    version: str = ""
    originpro_available: bool = False
    com_available: bool = False
    reason: str = ""


def _module_available(module_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_name) is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False


def _candidate_origin_paths() -> list[Path]:
    candidates: list[Path] = []
    configured = str(os.environ.get("ORIGIN_EXE") or "").strip()
    if configured:
        candidates.append(Path(configured))

    for command in ("Origin.exe", "OriginPro.exe"):
        resolved = shutil.which(command)
        if resolved:
            candidates.append(Path(resolved))

    for environment_name in ("ProgramFiles", "ProgramFiles(x86)"):
        root = os.environ.get(environment_name)
        if not root:
            continue
        origin_root = Path(root) / "OriginLab"
        if not origin_root.exists():
            continue
        candidates.extend(origin_root.glob("Origin*/Origin.exe"))
        candidates.extend(origin_root.glob("Origin*/OriginPro.exe"))
    return candidates


def _find_installation() -> tuple[bool, str]:
    for candidate in _candidate_origin_paths():
        if candidate.is_file():
            return True, ""
    return False, ""


def _find_com_server() -> bool:
    if platform.system() != "Windows":
        return False
    try:
        import winreg
    except ImportError:
        return False

    for progid in ORIGIN_COM_PROGIDS:
        try:
            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, f"{progid}\\CLSID"):
                return True
        except OSError:
            continue
    return False


class OriginCapabilityProbe:
    """Probe installation state without starting Origin or opening a COM session."""

    def __init__(
        self,
        *,
        installation_finder: Callable[[], tuple[bool, str]] | None = None,
        com_server_finder: Callable[[], bool] | None = None,
        module_finder: Callable[[str], bool] | None = None,
    ) -> None:
        self._installation_finder = installation_finder or _find_installation
        self._com_server_finder = com_server_finder or _find_com_server
        self._module_finder = module_finder or _module_available

    def probe(self) -> OriginCapability:
        if platform.system() != "Windows":
            return OriginCapability(
                installed=False,
                reason="Origin automation requires Windows",
            )

        try:
            installed, version = self._installation_finder()
        except Exception as exc:  # pragma: no cover - exact OS failure varies
            return OriginCapability(installed=False, reason=str(exc))

        try:
            originpro_available = bool(self._module_finder("originpro"))
        except Exception:
            originpro_available = False

        try:
            com_available = bool(
                self._module_finder("win32com.client") and self._com_server_finder()
            )
        except Exception:
            com_available = False

        reason = "" if installed else "Origin installation was not detected"
        return OriginCapability(
            installed=bool(installed),
            version=str(version or ""),
            originpro_available=originpro_available,
            com_available=com_available,
            reason=reason,
        )
