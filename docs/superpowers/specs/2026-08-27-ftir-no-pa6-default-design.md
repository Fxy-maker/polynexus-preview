# IR No-Implicit-Material Design

IR has two separate behaviors: generic spectral computation and material-aware interpretation. Generic computation must work without material metadata. Material-aware peak assignment may use an explicit user/context hint; when absent, the existing observed-peak identification remains an opt-in heuristic and its result is evidence, not a forced default.

The implementation removes the GUI schema's PA6 default and the temperature-series provider's PA6 fallback. ComputeRunService remains the single cross-entry boundary; a supplied project_context.material.name may populate an existing IRConfig.polymer_name, but no caller is required to provide it. No equation or reference library is changed.
