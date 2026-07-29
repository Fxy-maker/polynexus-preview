# Gallery Missing-Asset Selection Design

## Status

Approved for the current atomic implementation task.

## Problem

The active Gallery already skips entries with no asset path during initial
selection. A Manifest entry can still contain a non-empty path after the file
has been removed or an export has failed. That stale path is then selected and
can be forwarded to the Editor.

## Decision

Use filesystem existence as the only additional gate for the no-preference
initial-selection fallback. A candidate is usable when its normalized text is
non-empty and `Path(candidate).exists()` is true. Iterate entries in their
existing order and choose the first entry with a usable candidate path.

The preferred-path branch is deliberately unchanged. Preferred matching is a
separate identity-preserving contract and may still return a conservative
empty path when the Manifest points at a stale preferred asset. If every entry
is missing, retain the existing fallback shape: select the first entry and
return an empty path.

## Error handling

The helper is pure and local. It does not inspect file contents, alter the
Manifest, repair paths, or remove diagnostic entries. Filesystem failures are
treated as unusable by using a small `try/except OSError` around `exists()`.

## Testing

Add focused tests for three cases: a missing first entry followed by a real
entry, an existing first entry, and all entries missing. Keep the current
assetless diagnostic regression and preferred-path tests unchanged.
