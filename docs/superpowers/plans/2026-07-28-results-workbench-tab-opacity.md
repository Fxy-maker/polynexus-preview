# Results Workbench 主 Tab 透明效果修复计划

## Diagnosis

Native SAXS route capture showed that the Results labels already had active
Light-theme text colors, while the Results tab page retained a
`QGraphicsOpacityEffect` after `_on_tab_changed`. The effect was applied to the
whole page by the shared tab transition and reduced the apparent contrast of
all child content.

## Implementation

1. Add a focused regression test proving that `_on_tab_changed` leaves the
   selected main Tab page without a graphics effect.
2. Remove the full-page fade call from `_on_tab_changed`; keep `fade_in` for
   the explicitly animated drop banner and leave all content contracts intact.
3. Run focused Qt tests, native SAXS visual route capture, and the structured
   changed/type verifier.
4. Record the result in agent memory and checkpoint only the task-card,
   production, and focused-test files in the atomic commit.

## Review boundary

This is a GUI presentation/lifecycle correction and needs human visual review;
it does not authorize scientific or release sign-off.
