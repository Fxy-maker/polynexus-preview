# DSC Non-isothermal Method Evidence Design

Date: 2026-07-29
Status: approved working design

## Problem

The non-isothermal DSC publication provider can receive a completed kinetics
method result with valid fit metadata and rates but without authoritative
method plot coordinates. Its current fallback repeats one reported parameter
for every rate, creating a constant curve that looks like measured or fitted
evidence. That violates the shared publication rule that a provider may only
project completed evidence and may not fabricate a conclusion.

## Decision

Use `_method_points()` as the only source of method-plot coordinates. A method
without at least two finite, aligned x/y points is not plot-ready, even when
its fit metadata passes the existing quality gate:

- return the existing method definition as `diagnostic`;
- emit an empty diagnostic data source and no plot objects;
- record `missing_method_plot_data`, the method parameters, fit quality, and
  zero plot points in the recipe metadata;
- keep the conversion-series role and all existing scientific thresholds
  unchanged.

When authoritative x/y points exist, the existing role selection, plot
objects, and method parameters remain unchanged. No `NonIsothermalResult`
schema or analysis algorithm is changed; the provider only stops inventing
coordinates.

## Error and fallback semantics

Missing method coordinates are a publication evidence limitation, not a
runtime exception. The conversion figure may remain Main when its own curves
are valid. The affected kinetics method is Diagnostics and cannot be promoted
by its fit metadata alone.

## Verification boundary

The regression must prove that rates plus a finite method parameter do not
produce a curve, while a fixture with explicit finite x/y points still permits
the qualified Main method path. Existing provider, lifecycle, real-fixture,
quality, and boundary tests remain in scope.
