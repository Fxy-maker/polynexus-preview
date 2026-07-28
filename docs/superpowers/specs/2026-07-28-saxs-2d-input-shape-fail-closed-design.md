# SAXS 2D input shape fail-closed design

## Decision

Before anisotropy analysis, convert the supplied matrix and axes to detached
numeric arrays and require the declared sector-map contract:

```text
I_2d.ndim == 2
I_2d.shape == (len(chi), len(q))
len(q_1d) == len(I_1d)
```

Empty or non-convertible inputs are structurally invalid. They are not
repaired. The analyzer returns its existing empty result and routes an empty
metric payload through `build_orientation_evidence`, producing `Unusable`
evidence. A structural reason code records why no orientation result exists.

## Invariants

- Valid inputs follow the existing analysis path in scientific behavior.
- No input object is mutated.
- Detector quality remains a sector-map report and never becomes raw-detector
  evidence.
- No geometry, mask, saturation, orientation, or physical thresholds are
  inferred.
- Strict JSON serialization remains valid for all returned evidence.

## Evidence

The focused regression will reproduce the current boolean-indexing failure and
then prove the fail-closed result, while existing configured-axis, auto-axis,
isotropic, and empty-path tests protect valid and degraded behavior.
