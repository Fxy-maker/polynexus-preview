# NMR Shared Entry Without Material Defaults

## Decision

Extend the existing material-neutral one-dimensional converter to recognize NMR
ppm tables and add a source-bound envelope for FID/vendor NMR inputs. The
`ComputeRunService` will attach this template for NMR before invoking the
existing NMR provider. No provider algorithm is rewritten.

## Data flow

```text
NMR table/FID/vendor directory
  -> nmr.spectrum.v1 or raw-file-envelope.nmr.v1
  -> existing NMR provider
  -> ComputeRun with artifact/template/plan/result linkage
```

The canonical template records observed columns, units, row locators, and the
source hash. For opaque vendor inputs it records only the source hash and
format; it does not pretend the vendor bytes have been decoded into a table.

## Material semantics

`polymer_name` is an optional context hint. When absent, peak detection,
deconvolution, region integrals, SNR, FWHM, and relaxation metrics continue to
run. Generic region labels are not material assignments. The built-in polymer
shift library is queried only when an explicit polymer name is supplied (or a
caller explicitly opts into unscoped matching). Solid 13C Xc is available only
when crystalline and amorphous phases are explicitly assigned and pass the
existing assignment gate.

## Compatibility

The GUI, CLI, Batch, and Agent/Codex paths keep their public APIs. They all
receive the same `ComputeRun` projection. Existing direct `run_pipeline` calls
remain valid for compatibility and continue to use the NMR engine unchanged.
