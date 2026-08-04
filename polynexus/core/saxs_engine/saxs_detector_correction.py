"""Fail-closed detector correction contracts for 2D SAXS preprocessing.

This module deliberately contains no production calibration equations. A
reviewed backend may be registered explicitly by code after detector and
beamline evidence has been accepted.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import math
from types import MappingProxyType
from typing import Any, Iterable, Literal, Mapping, Protocol

import numpy as np

from .saxs_orientation_reliability import CorrectionLedgerEntry


CorrectionMode = Literal["disabled", "candidate", "reviewed"]
CorrectionStatus = Literal[
    "applied",
    "rejected",
    "unavailable",
    "not_requested",
    "candidate_only",
]

REVIEW_SCOPE = "saxs.detector_calibration"
_OPERATIONS = (
    "dark_correction",
    "flat_field_correction",
    "background_correction",
    "isotropic_reference_correction",
    "polarization_correction",
    "solid_angle_correction",
    "transmission_normalization",
    "thickness_normalization",
)
_ROLE_OPERATIONS = {
    "dark": "dark_correction",
    "dark_frame": "dark_correction",
    "flat": "flat_field_correction",
    "flat_field": "flat_field_correction",
    "background": "background_correction",
    "isotropic_reference": "isotropic_reference_correction",
    "standard": "isotropic_reference_correction",
}


def _digest_array(value: Any) -> str | None:
    try:
        array = np.asarray(value)
    except (TypeError, ValueError):
        return None
    if array.size == 0:
        return hashlib.sha256(b"").hexdigest()
    contiguous = np.ascontiguousarray(array)
    payload = f"{contiguous.dtype.str}:{contiguous.shape}:".encode("ascii")
    return hashlib.sha256(payload + contiguous.tobytes()).hexdigest()


def detector_array_digest(value: Any) -> str | None:
    """Return a detached digest for an image/mask integration input."""

    return _digest_array(value)


def detector_input_digest(image: Any, mask: Any) -> str | None:
    """Digest the exact image and mask pair supplied to an integration path."""

    image_digest = _digest_array(image)
    mask_digest = _digest_array(np.asarray(mask, dtype=np.uint8))
    if image_digest is None or mask_digest is None:
        return None
    return hashlib.sha256(
        f"image:{image_digest}:mask:{mask_digest}".encode("ascii")
    ).hexdigest()


def _freeze_array(value: Any, *, dtype: Any = float) -> np.ndarray:
    array = np.array(value, dtype=dtype, copy=True)
    array.setflags(write=False)
    return array


def _freeze_mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return MappingProxyType(dict(value or {}))


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(child) for child in value]
    if isinstance(value, np.ndarray):
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        number = float(value)
        return number if math.isfinite(number) else None
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    return str(value)


def _normalized_operation(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def _operation_for_role(role: str) -> str | None:
    normalized = _normalized_operation(role)
    if normalized in _ROLE_OPERATIONS:
        return _ROLE_OPERATIONS[normalized]
    if normalized in _OPERATIONS:
        return normalized
    return None


def _bool_value(value: Any) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    return str(value or "").strip().lower() in {"1", "true", "yes", "applied", "corrected"}


@dataclass(frozen=True)
class DetectorCalibrationFrame:
    role: str
    source_id: str
    content_digest: str
    image: np.ndarray = field(repr=False, compare=False)
    metadata: Mapping[str, Any] = field(default_factory=dict, compare=False)

    def __post_init__(self) -> None:
        image = _freeze_array(self.image)
        object.__setattr__(self, "image", image)
        object.__setattr__(self, "role", _normalized_operation(self.role))
        object.__setattr__(self, "source_id", str(self.source_id))
        object.__setattr__(self, "content_digest", str(self.content_digest))
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))

    @classmethod
    def from_array(
        cls,
        *,
        role: str,
        source_id: str,
        image: Any,
        metadata: Mapping[str, Any] | None = None,
        content_digest: str | None = None,
    ) -> "DetectorCalibrationFrame":
        detached = np.array(image, dtype=float, copy=True)
        return cls(
            role=role,
            source_id=source_id,
            content_digest=content_digest or _digest_array(detached) or "",
            image=detached,
            metadata=metadata or {},
        )


@dataclass(frozen=True)
class DetectorCorrectionRequest:
    mode: CorrectionMode
    sample_source_id: str
    policy_id: str | None = None
    review_record_digest: str | None = None
    frames: tuple[DetectorCalibrationFrame, ...] = ()
    explicit_scalars: Mapping[str, Any] = field(default_factory=dict)
    geometry_digest: str | None = None
    review_scope: str = REVIEW_SCOPE

    def __post_init__(self) -> None:
        object.__setattr__(self, "mode", str(self.mode).strip().lower())
        object.__setattr__(self, "sample_source_id", str(self.sample_source_id))
        object.__setattr__(self, "frames", tuple(self.frames))
        object.__setattr__(self, "explicit_scalars", _freeze_mapping(self.explicit_scalars))
        object.__setattr__(self, "review_scope", str(self.review_scope or ""))

    @classmethod
    def disabled(cls, sample_source_id: str) -> "DetectorCorrectionRequest":
        return cls(mode="disabled", sample_source_id=sample_source_id)


class DetectorCorrectionBackend(Protocol):
    policy_id: str
    operation_order: tuple[str, ...]

    def apply_validated(
        self,
        sample: np.ndarray,
        mask: np.ndarray,
        request: DetectorCorrectionRequest,
    ) -> tuple[np.ndarray, np.ndarray, tuple[CorrectionLedgerEntry, ...]]:
        ...


@dataclass(frozen=True)
class DetectorCorrectionRegistry:
    backends: Mapping[str, DetectorCorrectionBackend] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "backends", _freeze_mapping(self.backends))

    @property
    def policy_ids(self) -> tuple[str, ...]:
        return tuple(sorted(str(key) for key in self.backends))


def default_detector_correction_registry() -> DetectorCorrectionRegistry:
    """Return the empty production registry until calibration is reviewed."""

    return DetectorCorrectionRegistry({})


@dataclass(frozen=True)
class DetectorCorrectionResult:
    effective_image: np.ndarray = field(repr=False, compare=False)
    effective_mask: np.ndarray = field(repr=False, compare=False)
    correction_ledger: tuple[CorrectionLedgerEntry, ...]
    candidate_systematic_harmonic: Mapping[str, Any]
    level: str
    applicable: bool
    reason_codes: tuple[str, ...]
    status: CorrectionStatus = "not_requested"
    policy_id: str | None = None
    sample_source_id: str = ""
    review_record_digest: str | None = None
    frame_evidence: tuple[Mapping[str, Any], ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "effective_image", _freeze_array(self.effective_image))
        object.__setattr__(
            self,
            "effective_mask",
            _freeze_array(self.effective_mask, dtype=bool),
        )
        object.__setattr__(self, "correction_ledger", tuple(self.correction_ledger))
        object.__setattr__(self, "candidate_systematic_harmonic", _freeze_mapping(self.candidate_systematic_harmonic))
        object.__setattr__(self, "reason_codes", tuple(str(item) for item in self.reason_codes))
        object.__setattr__(self, "frame_evidence", tuple(_freeze_mapping(item) for item in self.frame_evidence))

    def to_evidence_dict(self) -> dict[str, Any]:
        return _json_safe({
            "status": self.status,
            "level": self.level,
            "applicable": self.applicable,
            "policy_id": self.policy_id,
            "sample_source_id": self.sample_source_id,
            "review_record_digest": self.review_record_digest,
            "review_scope": REVIEW_SCOPE,
            "frames": self.frame_evidence,
            "correction_ledger": tuple(item.to_dict() for item in self.correction_ledger),
            "candidate_systematic_harmonic": self.candidate_systematic_harmonic,
            "reason_codes": self.reason_codes,
        })


def _ledger(
    *,
    status: CorrectionStatus,
    reason_codes: Iterable[str],
    request: DetectorCorrectionRequest,
    applied_operations: Iterable[str] = (),
) -> tuple[CorrectionLedgerEntry, ...]:
    applied = set(applied_operations)
    reasons = tuple(dict.fromkeys(str(item) for item in reason_codes))
    entries: list[CorrectionLedgerEntry] = []
    for operation in _OPERATIONS:
        operation_status: str
        if operation in applied:
            operation_status = "applied"
        elif status == "candidate_only" and _request_operations(request) and operation in _request_operations(request):
            operation_status = "candidate_only"
        elif status == "not_requested":
            operation_status = "not_requested"
        else:
            operation_status = "unavailable"
        entries.append(CorrectionLedgerEntry(
            operation=operation,
            status=operation_status,
            source=request.policy_id or "detector_correction_registry",
            reason_codes=reasons,
        ))
    return tuple(entries)


def _request_operations(request: DetectorCorrectionRequest) -> tuple[str, ...]:
    operations = {
        operation for frame in request.frames
        if (operation := _operation_for_role(frame.role)) is not None
    }
    if _bool_value(request.explicit_scalars.get("apply_transmission")):
        operations.add("transmission_normalization")
    if _bool_value(request.explicit_scalars.get("apply_thickness")):
        operations.add("thickness_normalization")
    return tuple(operation for operation in _OPERATIONS if operation in operations)


def _identity_result(
    image: np.ndarray,
    mask: np.ndarray,
    request: DetectorCorrectionRequest,
    *,
    reason_codes: Iterable[str],
    status: CorrectionStatus = "not_requested",
    level: str = "Diagnostic",
    ledger: tuple[CorrectionLedgerEntry, ...] | None = None,
    candidate_systematic_harmonic: Mapping[str, Any] | None = None,
) -> DetectorCorrectionResult:
    reasons = tuple(dict.fromkeys(str(item) for item in reason_codes))
    return DetectorCorrectionResult(
        effective_image=image,
        effective_mask=mask,
        correction_ledger=ledger or _ledger(status=status, reason_codes=reasons, request=request),
        candidate_systematic_harmonic=candidate_systematic_harmonic or {},
        level=level,
        applicable=False,
        reason_codes=reasons,
        status=status,
        policy_id=request.policy_id,
        sample_source_id=request.sample_source_id,
        review_record_digest=request.review_record_digest,
        frame_evidence=tuple({
            "role": frame.role,
            "source_id": frame.source_id,
            "content_digest": frame.content_digest,
        } for frame in request.frames),
    )


def _validate_request(
    image: np.ndarray,
    mask: np.ndarray,
    request: DetectorCorrectionRequest,
    registry: DetectorCorrectionRegistry,
    legacy_operations: Iterable[str],
) -> tuple[bool, tuple[str, ...]]:
    reasons: list[str] = []
    if request.mode not in {"disabled", "candidate", "reviewed"}:
        reasons.append("correction_mode_invalid")
    if request.mode in {"candidate", "reviewed"}:
        if not request.policy_id:
            reasons.append("calibration_policy_missing")
        if not request.review_record_digest:
            reasons.append("calibration_review_digest_missing")
        if request.review_scope != REVIEW_SCOPE:
            reasons.append("calibration_review_scope_invalid")
        if request.policy_id and request.policy_id not in registry.backends:
            reasons.append("calibration_policy_unknown")
    if image.ndim != 2 or mask.ndim != 2:
        reasons.append("detector_input_not_2d")
    if image.shape != mask.shape:
        reasons.append("detector_mask_shape_mismatch")
    if request.mode in {"candidate", "reviewed"} and not np.all(np.isfinite(image)):
        reasons.append("detector_input_nonfinite")
    if request.mode in {"candidate", "reviewed"} and not np.all(np.isfinite(mask)):
        reasons.append("detector_mask_nonfinite")

    seen_roles: set[str] = set()
    detector_models: set[str] = set()
    serials: set[str] = set()
    geometry_digests: set[str] = set()
    for frame in request.frames:
        if frame.role in seen_roles:
            reasons.append("calibration_duplicate_role")
        seen_roles.add(frame.role)
        if frame.image.ndim != 2 or frame.image.shape != image.shape:
            reasons.append("calibration_shape_mismatch")
        if not np.all(np.isfinite(frame.image)):
            reasons.append("calibration_frame_nonfinite")
        if frame.content_digest != (_digest_array(frame.image) or ""):
            reasons.append("calibration_content_digest_mismatch")
        if frame.role in {"flat", "flat_field"} and np.any(frame.image <= 0):
            reasons.append("flat_field_nonpositive_pixel")
        metadata = frame.metadata
        for field_name, values in (
            ("detector_model", detector_models),
            ("detector_serial_number", serials),
        ):
            value = str(metadata.get(field_name) or "").strip()
            if value:
                values.add(value)
        geometry = str(metadata.get("geometry_digest") or "").strip()
        if geometry:
            geometry_digests.add(geometry)
        try:
            exposure = float(metadata.get("exposure_time_s"))
        except (TypeError, ValueError):
            exposure = None
        if exposure is not None and (not np.isfinite(exposure) or exposure <= 0):
            reasons.append("calibration_exposure_invalid")

    if len(detector_models) > 1:
        reasons.append("calibration_detector_model_mismatch")
    if len(serials) > 1:
        reasons.append("calibration_detector_serial_mismatch")
    if request.geometry_digest and geometry_digests and geometry_digests != {request.geometry_digest}:
        reasons.append("calibration_geometry_digest_mismatch")
    if request.geometry_digest and not geometry_digests and request.frames:
        reasons.append("calibration_geometry_digest_missing")

    for name in ("sample_exposure_s",):
        if name in request.explicit_scalars:
            try:
                number = float(request.explicit_scalars[name])
            except (TypeError, ValueError):
                number = None
            if number is None or not np.isfinite(number) or number <= 0:
                reasons.append("sample_exposure_invalid")

    operation_map = {
        "flat_field_correction": "flat_field_already_applied",
        "background_correction": "background_already_applied",
        "polarization_correction": "polarization_already_applied",
        "solid_angle_correction": "solid_angle_already_applied",
    }
    for operation, flag in operation_map.items():
        if operation in _request_operations(request) and _bool_value(request.explicit_scalars.get(flag)):
            reasons.append(f"{operation}_double_correction")
    if "background_correction" in _request_operations(request):
        required = ("transmission_sample", "sample_thickness_m")
        for name in required:
            if name not in request.explicit_scalars:
                reasons.append(f"{name}_explicit_value_missing")

    legacy = {_normalized_operation(item) for item in legacy_operations}
    for operation in _request_operations(request):
        if operation in legacy:
            reasons.append(f"{operation}_owner_conflict")
    return not reasons, tuple(dict.fromkeys(reasons))


def evaluate_detector_correction(
    image: Any,
    mask: Any,
    request: DetectorCorrectionRequest,
    *,
    registry: DetectorCorrectionRegistry | None = None,
    legacy_operations: Iterable[str] = (),
) -> DetectorCorrectionResult:
    """Evaluate and, only when reviewed, transactionally apply correction."""

    sample = np.array(image, dtype=float, copy=True)
    base_mask = np.array(mask, dtype=bool, copy=True)
    if request.mode == "disabled":
        return _identity_result(
            sample,
            base_mask,
            request,
            reason_codes=("detector_correction_disabled",),
        )

    active_registry = registry or default_detector_correction_registry()
    accepted, reasons = _validate_request(
        sample, base_mask, request, active_registry, legacy_operations,
    )
    if not accepted:
        return _identity_result(sample, base_mask, request, reason_codes=reasons, status="rejected")
    if request.mode == "candidate":
        return _identity_result(
            sample,
            base_mask,
            request,
            reason_codes=("detector_correction_candidate_only",),
            status="candidate_only",
        )

    backend = active_registry.backends.get(request.policy_id or "")
    if backend is None:
        return _identity_result(
            sample,
            base_mask,
            request,
            reason_codes=("detector_correction_backend_unavailable",),
            status="unavailable",
        )
    input_digest = _digest_array(sample)
    mask_digest = _digest_array(base_mask)
    try:
        output_image, output_mask, ledger = backend.apply_validated(sample, base_mask, request)
        if _digest_array(sample) != input_digest or _digest_array(base_mask) != mask_digest:
            raise ValueError("backend_mutated_input")
        output_image = np.array(output_image, dtype=float, copy=True)
        output_mask = np.array(output_mask, dtype=bool, copy=True)
        if output_image.shape != sample.shape or output_mask.shape != base_mask.shape:
            raise ValueError("backend_output_shape_mismatch")
        if not np.all(np.isfinite(output_image)):
            raise ValueError("backend_output_nonfinite")
        if not isinstance(ledger, tuple) or not all(isinstance(item, CorrectionLedgerEntry) for item in ledger):
            raise ValueError("backend_ledger_invalid")
        expected = tuple(_normalized_operation(item) for item in getattr(backend, "operation_order", ()))
        actual = tuple(item.operation for item in ledger if item.status == "applied")
        if len(set(actual)) != len(actual) or any(operation not in actual for operation in expected):
            raise ValueError("backend_ledger_incomplete")
    except Exception as exc:
        reason = str(exc) or "backend_transaction_failed"
        return _identity_result(
            sample,
            base_mask,
            request,
            reason_codes=(reason,),
            status="rejected",
        )

    return DetectorCorrectionResult(
        effective_image=output_image,
        effective_mask=output_mask,
        correction_ledger=ledger,
        candidate_systematic_harmonic={},
        level="Quantitative",
        applicable=True,
        reason_codes=(),
        status="applied",
        policy_id=request.policy_id,
        sample_source_id=request.sample_source_id,
        review_record_digest=request.review_record_digest,
        frame_evidence=tuple({
            "role": frame.role,
            "source_id": frame.source_id,
            "content_digest": frame.content_digest,
        } for frame in request.frames),
    )


__all__ = [
    "CorrectionMode",
    "CorrectionStatus",
    "REVIEW_SCOPE",
    "DetectorCalibrationFrame",
    "DetectorCorrectionRequest",
    "DetectorCorrectionBackend",
    "DetectorCorrectionRegistry",
    "DetectorCorrectionResult",
    "default_detector_correction_registry",
    "detector_array_digest",
    "detector_input_digest",
    "evaluate_detector_correction",
]
