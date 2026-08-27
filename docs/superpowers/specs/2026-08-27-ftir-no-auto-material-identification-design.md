# FTIR No-Auto-Material Identification

The IR provider will treat material as an optional analysis hint. It will only
call the polymer peak database when `polymer_name` is explicitly present. With
an empty hint, peak assignments remain generic spectral regions and the result
does not claim a polymer identity. This preserves generic calculations while
making the provenance honest.
