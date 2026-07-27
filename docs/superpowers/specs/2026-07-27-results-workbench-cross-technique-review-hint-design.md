# Cross-technique Results Workbench Review Hint Design

## Goal

Expose the existing structured result `summary`, `risk_text`, and `next_text`
through the shared Results Workbench review-hint surface for DSC, WAXS, IR,
NMR, and Joint, while preserving the existing SAXS temperature/strain wording
and navigation behavior.

## Scope

- Reuse the `ResultsTableModel` review text already produced by analysis
  presentation adapters.
- Show the same text in `ResultsTablePanel.set_review_hint()` for every
  non-generic structured profile.
- Use the profile's existing localized review-action label for non-SAXS modes,
  and keep the SAXS-specific action/title for SAXS temperature and strain.
- Preserve language retranslation of both actions.

## Non-goals

- No new scientific interpretation, severity calculation, or evidence
  threshold.
- No changes to result-table sections, provider FigureDefinitions, AI policy,
  or publication roles.
- No review hint for legacy/generic tables without a structured profile.

## Design

`MainWindowOutputMixin._update_results_review_hint()` becomes a presentation
router: it checks the current structured profile, selects existing text, and
chooses an action label. The callback still navigates to the existing Results
tab. `ResultsTablePanel.set_review_hint()` recognizes both the existing SAXS
translation key and the shared Workbench review-action key so a language change
updates the visible action text.

The status remains `review` when existing risk text is present and `neutral`
otherwise. No new `blocked` or `reliable` decision is inferred.

## Acceptance

- A non-SAXS structured result with risk/next text renders one review hint with
  the profile title/action and an existing Results-tab callback.
- Existing SAXS temperature, SAXS strain, unsupported technique, and generic
  table behavior remain unchanged.
- Re-translation updates a generic Workbench hint action label.
- Focused and task-scoped verification pass without full-suite claims.
