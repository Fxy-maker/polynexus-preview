# IR temperature-2D frame provenance design

IR temperature-2D figures continue to use `frame_index` as the plotted axis,
because input ordering and sequence validity are already part of the analysis
contract. The provider will add numeric `temperature_C` and `time_min` columns
to heatmap/band data snapshots, using NaN only when the source frame lacks a
value. Human-readable `stage`, frame label, `time_estimated`, and
`sequence_order_source` remain in the recipe's JSON-safe `frame_metadata`, so
the renderer receives numeric data while Gallery/Editor/export retain the full
condition provenance.
