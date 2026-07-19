# Daily Task: Origin label display polish

## Goal

Make native OriginPro figures render PolyNexus mathtext axis labels as readable
Unicode text and keep the existing multi-series graph visually clean.

## Non-goals

- Do not change source data, curve values, axis scale semantics, or fallback
  export behavior.
- Do not introduce Origin-specific rich-text syntax into persisted figure
  documents.

## Acceptance criteria

- [x] `$I$ (a.u.)` renders as `I (a.u.)`.
- [x] `$q$ (nm$^{-1}$)` renders as `q (nm⁻¹)`.
- [x] Common Greek/symbol commands such as `\mu` render as Unicode.
- [x] The native export still contains one Graph, five plots, named series,
  document colors, and a logarithmic Y axis.
- [x] Static and Origin-compatible fallback exports are unchanged.

## Verification

```powershell
python -m pytest tests/test_originpro_adapter.py tests/test_origin_mapping.py -q
python -m ruff check polynexus/origin/originpro_adapter.py tests/test_originpro_adapter.py
python -m compileall -q polynexus/origin tests/test_originpro_adapter.py
git diff --check
```

The real OriginPro smoke also exported a temporary PNG preview showing the
clean Unicode labels; the temporary native project remains Origin-owned until
the application closes.
