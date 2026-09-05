# PolyNexus public validation pack

This pack is a reproducible index of openly licensed data selected for
PolyNexus parser, canonical conversion, and replay preparation. The manifest
is committed; archives are intentionally stored outside the Git repository at
`D:\PolyNexus-validation-data` by default.

## Scope

The first pass has complete, checksum-verified archives for TGA, DMA, FTIR,
NMR, SAXS, WAXS, and a PLA/chitosan supplementary package. It also records a
DSC archive and a second SAXS archive that are currently incomplete at the
remote mirror and therefore remain `candidate`, not validation inputs. Zenodo
record `14723415` is the most useful polymer-oriented source because it
contains multiple thermal, viscoelastic, infrared, and polymer-NMR archives.
The SAXS and WAXS records are retained as format/sequence smoke tests because
they are openly downloadable, but their materials are not polymers and they
cannot support polymer scientific claims.

The PLA/chitosan package contains two Origin GPC project files and Bruker NMR
directories, but no portable chromatogram export or tensile stress-strain
table. It is therefore retained as a promising vendor-format case, not yet a
ready SEC or mechanics replay case. Rheology still has no confirmed, small,
openly downloadable raw/instrument-export source in this pack. Keep SEC/GPC
and rheology routes on synthetic and local fixtures until sources with clear
licensing, checksums, and sufficient instrument metadata are found.

## Rebuild

```powershell
python scripts/validation_pack.py validate
python scripts/validation_pack.py download
python scripts/validation_pack.py inspect
python scripts/validation_pack.py lock
python scripts/validation_pack.py validate --require-local
```

Use `--data-root <path>` to keep the external pack elsewhere. The downloader
uses Zenodo's published MD5 checksum and writes a local SHA-256 in the download
report. `lock` writes the external `validation-manifest.lock.json` with local
SHA-256 values and archive inspection summaries. Interrupted downloads remain
as `.part` files and are resumed on the next run; a file is renamed into place
only after checksum verification.

## Scientific boundary

`candidate` means source metadata is recorded, not that the file is ready for
capability promotion. Archive members must still be inspected and bound to a
`CanonicalDataset/CanonicalExperiment`. Independent replay, standard sample,
negative control, formal uncertainty, and human scientific review remain
required before any capability can be promoted. Source labels such as `Raw
data`, `Tg`, or `stress-strain` are preserved as provenance, not accepted as
PolyNexus conclusions.

The next step after download is to convert a small, explicitly selected member
from each archive into replay cases with expected values and tolerances. Do not
bulk-extract every archive into the repository or treat processed curves as
acquisition raw data.
