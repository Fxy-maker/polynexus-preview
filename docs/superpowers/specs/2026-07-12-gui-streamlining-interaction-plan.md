# GUI Streamlining: Final Interaction Plan and Retention Checklist

**Date:** 2026-07-12
**Status:** Interaction design and scope baseline; implementation intentionally deferred.

## 1. Goal

Reduce duplicated GUI entry points and clarify page responsibilities without
removing scientific analysis capability, raw evidence, history, export formats,
or recovery access. This is the final interaction baseline for the last GUI
streamlining wave.

The streamlining changes navigation and ownership of actions. It does not
change scientific algorithms, result schemas, manifest contracts, or the
meaning of an analysis result.

## 2. Design principles

1. One user intent has one primary visible entry point.
2. Actions follow the object currently being operated on: data, configuration,
   current result, figure, historical run, sample, or joint analysis.
3. Contextual shortcuts may remain when they carry selection context; global
   duplicates without context should disappear.
4. A hidden or deferred action is not deleted until its replacement is tested
   and its keyboard/menu route is documented.
5. Scientific evidence remains inspectable even when the surrounding UI is
   simplified.
6. Empty, loading, warning, and recovery states are first-class states, not
   blank panels.

## 3. Information architecture

The main window keeps five stable workspaces:

| Workspace | Primary responsibility | Primary actions |
| --- | --- | --- |
| Data | Import source data and choose output location | Open file, open folder, choose output, inspect loaded source |
| Config | Configure the selected technique | Edit parameters, save/load/delete preset, apply recent calibration |
| Results | Review the current run | Read summary, inspect tables, compare, confirm, export result tables |
| Plots | Inspect published figure artifacts | Browse manifest gallery, preview, edit/view selected figure, recover legacy figures explicitly |
| History | Navigate persisted runs and review lineage | Select run, compare against a baseline, confirm/review, open historical context |

The sidebar remains the navigation source of truth for technique and workspace
selection. It may expose the Sample Library and Joint Analysis as contextual
workspaces, but they must not create parallel copies of Results or History.

## 4. Interaction flows

### 4.1 Standard analysis flow

```text
Choose technique
  -> Data: load source and output location
  -> Config: set parameters and optional preset
  -> Run: execute the selected technique
  -> Results: review current evidence
  -> Plots: inspect the active manifest-backed figure pack
  -> History: compare, confirm, or revisit the run
  -> Export: export the current result/table/figure in its owning context
```

The top bar may expose only actions that operate on the current analysis
context: Run, Replot when valid, and the context-appropriate Export action.
Review, plots, history, and joint-analysis actions belong to their workspaces
and are not repeated as unrelated global buttons.

### 4.2 Results review flow

The Results workspace is one review surface with three stable regions:

1. Current-run summary and evidence status.
2. Structured result tables with raw-value sorting and table export.
3. Review actions: compare, confirm, and technique-specific diagnostics.

The current run is selected by persisted run identity. A comparison control
selects one baseline and opens the shared comparison surface. A confirmation
change updates the current result, History, and any review aggregation through
the existing service boundary.

Optimization or convergence review remains available from the review context,
but its label must state that it is an optimization/review surface rather than
implying that it is a second result page.

### 4.3 Plot review flow

The Plots workspace opens on the manifest-backed gallery. The user selects one
logical figure card, then the preview area exposes the selected figure's
available operations:

- Preview and close preview.
- Open an independent viewer.
- Open the editor using the manifest entry and capability report.
- Inspect secondary assets belonging to the same figure.

The top-level View Current Figure button is redundant when the preview already
has a View action. It should be removed only after the preview action has the
same enablement and error behavior. The gallery card must not retain a second
edit route if the preview is the canonical edit route.

Historical Figure Recovery remains a separate, explicitly labeled action. It
must never replace the active gallery selection or silently turn a legacy file
into the current run.

### 4.4 History flow

History owns persisted run selection, lineage, comparison context, and review
status. It keeps the ability to open a historical run in its own context. It
does not duplicate the current Results table or the active Plots gallery.

The current run is visibly distinguished from comparison candidates. Empty
history, missing files, and incompatible records show an explanatory state and
leave the current workspace intact.

### 4.5 Sample and joint-analysis flow

The Sample Library keeps sample creation, editing, batch management, use for
analysis, and cross-technique selection. A sample or batch selection carries
its context into the single Joint Analysis workspace.

Joint Analysis has one visible entry and one generation/run action. Legacy joint
mode aliases may normalize internally, but they must not appear as separate
navigation destinations.

## 5. Action ownership rules

| Action | Canonical owner | Duplicate treatment |
| --- | --- | --- |
| Run analysis | Top bar in analysis context | Do not repeat on Results, Plots, or History |
| Replot | Top bar when the current technique supports it | Keep disabled state; do not create a second plot toolbar |
| Export result/table | Results or current analysis context | Keep figure asset export inside Plots/figure context |
| Compare runs | Results and History, sharing one service | Preserve both only because each supplies different selection context |
| Confirm result | Results and History | Both may remain; they must update the same persisted state |
| Open figure viewer | Selected-figure preview | Remove duplicate global/topbar route after parity verification |
| Edit figure | Selected-figure preview | Remove gallery-card duplicate after parity verification |
| Recover legacy figure | Plots recovery action | Keep separate from active gallery |
| Joint analysis | Sample context and one Joint workspace | Remove pseudo-technique duplicates |
| Optimization review | Results/History review context | Remove misleading global duplicate |

## 6. Retention checklist

### Always retain

- SAXS, WAXS, DSC, IR, and NMR technique navigation and all supported analysis
  submodules.
- Data import from files, folders, and drag-and-drop where currently supported.
- Output directory selection and visible source/output context.
- Configuration parameters, presets, recent calibration actions, and their
  persistence contracts.
- Current-run summary, structured tables, raw values, sorting, status details,
  warnings, and technique-specific evidence.
- Result-table export and publication-oriented figure exports.
- Manifest-only active figure gallery, logical figure cards, secondary assets,
  preview, independent viewer, and manifest-bound editor entry.
- Explicit Historical Figure Recovery and its honest classification of legacy
  candidates.
- History records, current-run identity, comparison, confirmation, and lineage.
- Sample creation/editing, batch management, use-for-analysis, and contextual
  Joint Analysis selection.
- The single Joint Analysis workspace and its busy/selection safety rules.
- Theme switching, language switching, recent data, visible logs, warning
  summaries, keyboard copy behavior, and accessible tooltips.
- Existing result/document/manifest schemas and service-layer contracts.

### Keep, but move to contextual ownership

- Review/optimization actions: Results or History, not a second global review
  dashboard entry.
- Figure view/edit actions: selected figure preview, not both toolbar and card.
- Figure asset export: Plots/selected figure, not an unrelated global button.
- Joint Analysis: Sample/Joint context, not pseudo-technique navigation.
- Recent project operations: sidebar/history context, not duplicate top-bar
  actions.

### Temporarily defer

- Full GUI shell rewrite or replacement of the current mixin architecture.
- New multi-panel editor architecture or broad style-system refactoring.
- Automatic legacy gallery fallback; the active gallery remains manifest-only.
- SAXS temperature/strain production behavior changes; those belong to the
  production cutover task and scientific review.
- New visual dashboard widgets, animations, or broad density changes before
  the interaction ownership is stable.
- Removing compatibility aliases, old settings keys, or historical data paths
  before migration evidence exists.

### Candidate for removal after replacement verification

- Duplicate top-bar review button/menu action when the contextual review route
  is proven equivalent.
- Duplicate top-level View Current Figure action when preview View is equivalent.
- Duplicate gallery-card Edit action when preview Edit is equivalent.
- Pseudo-technique entries that only represent legacy joint-mode aliases.
- Dead signal handlers, labels, translations, and test helpers belonging only
  to removed entry points.

No candidate in this section may be deleted merely because a new button exists.
The replacement must have focused tests, Chinese/English labels, keyboard and
minimum-size coverage, and an error-state check first.

## 7. Responsive and accessibility contract

The four critical views—Data, Results, Plots, and Joint Analysis—must remain
usable at 1280x820 and the minimum supported 960x600 window size in both
Chinese and English.

- Primary actions remain visible and inside their parent layout.
- Dense action rows may wrap or split into labeled rows; actions must not be
  hidden to make the layout fit.
- A tooltip is supplementary, not the only label for a primary operation.
- Keyboard focus, copy shortcuts, selection state, disabled state, and visible
  error messages retain their existing semantics.
- Long translated labels must not silently clip the only actionable control.

## 8. Implementation gates for the later final wave

Do not start the GUI code changes until this interaction baseline is approved
and the following gates remain true:

1. Active figure gallery is manifest-only and legacy recovery is separate.
2. Editor source/style context review has passed.
3. SAXS/WAXS/DSC publication paths and their status contracts are stable.
4. Existing Results, History, Sample, Joint, and Figure Editor focused tests
   are green before each UI slice.
5. Each slice has a before/after ownership list and no unexplained deletion.

Recommended implementation order:

1. Navigation and workspace ownership, with no behavior deletion.
2. Results/History review consolidation and shared confirmation state.
3. Plot preview/view/edit ownership and responsive layout.
4. Joint/Sample contextual routing and translation/accessibility cleanup.
5. Delete only verified duplicate routes, then run the full GUI regression
   matrix and manual 1280x820/960x600 checks.

## 9. Non-goals for this planning task

- No GUI code changes.
- No button deletion.
- No schema or persistence migration.
- No old data deletion.
- No production scientific behavior change.
