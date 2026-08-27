# Gallery Logical Filters — Acceptance

The GUI evidence-gallery adapter now supports optional case-insensitive filters
for technique, group, and logical role. Filtering happens before filesystem
asset loading, so a user can view one group without seeing unrelated export
formats or techniques. Existing callers retain the previous behavior.

Verification: `24 passed` in gallery/evidence-view tests; scientific provider
outputs and package schemas were not changed.
