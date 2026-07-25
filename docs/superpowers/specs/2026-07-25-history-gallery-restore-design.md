# History Gallery restore design

History records already persist `output_dir`, while the shared figure lifecycle
stores the active run pointer and manifest below that directory. Restore should
therefore re-use the existing `MainWindowFigureMixin._populate_plots()` boundary
after assigning the restored output directory; it must not discover files or
rebuild figures itself.

The change is intentionally small: valid history records reload the manifest-only
Gallery, invalid/missing source behavior remains unchanged, and all downstream
Editor/export actions continue to consume the same `FigureGalleryEntry` carrying
`run_root`, `document_path`, publication role, and provenance context.
