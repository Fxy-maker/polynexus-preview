# DSC Results Workbench checkpoint

## Delivered

DSC standard, isothermal, and non-isothermal modes now have mode-specific
Workbench narratives, review tabs, and real publication-provider Manifest IDs:

- Standard: `dsc.standard.thermogram` and
  `dsc.comparison.thermal-events`.
- Isothermal: `dsc.isothermal.avrami` and `dsc.isothermal.series`.
- Non-isothermal: `dsc.nonisothermal.conversion` and
  `dsc.nonisothermal.kissinger`.

The existing DSC analysis/evidence templates remain the source of hero,
primary, support, and diagnostic values. The Workbench only consumes the
structured presentation and routes figure selection through the shared
Manifest/Gallery boundary.

## Verification evidence

- DSC engine, figure provider, publication-provider, cutover, FigureDocument,
  evaluation, and Workbench profile matrix: 53 passed.
- Results Workbench and main-window regression matrix: 47 passed.
- Ruff, compileall, and `git diff --check`: passed.

## Remaining acceptance boundary

- Restarted-GUI visual review, real-data scientific sign-off, and the final
  AI-off/failure/fallback cross-technique matrix remain release gates.
- The next vertical slice is WAXS, using the same profile/Manifest pattern.
