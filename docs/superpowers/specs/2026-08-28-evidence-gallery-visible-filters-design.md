# Evidence Gallery Visible Filters

The read-only evidence dialog adds two lightweight selectors above the existing
`ChartGallery`: technique and group. Values come only from the immutable
`EvidencePackageView.figure_views` index. Selection calls the existing adapter,
which applies case-insensitive logical filtering before resolving SVG assets.
The gallery remains read-only and keeps its own role/category/search controls.
