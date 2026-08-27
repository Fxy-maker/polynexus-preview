# SAXS No-Material Reference Design

Static SAXS calibration must not depend on a material token in a filename. The provider will choose the first batch result with a finite Q invariant, preserving input order; if none is finite it retains the existing first-frame fallback so missing data remains an unavailable calibration rather than a hard failure. This keeps the algorithm deterministic without claiming that the first frame is scientifically the best control.
