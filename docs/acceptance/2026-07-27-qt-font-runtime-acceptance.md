# Qt Font Runtime Acceptance — 2026-07-27

The canonical Windows Qt runtime was checked without forcing an offscreen
platform. It reported 399 installed font families, resolved the application
font to `Microsoft YaHei UI`, and covered the representative Chinese labels
`中文温度应变结果`.

The same check under `QT_QPA_PLATFORM=offscreen` reported an empty Qt font
database and no glyph coverage. This explains square CJK placeholders in
offscreen captures; it is not evidence of a missing production fallback.

No production font, Qt theme, or Matplotlib publication-font change was made.
Live font and pixel-level approval still require a restarted-GUI human review.

The task-scoped verifier passed task/memory checks, Ruff, compile/type
baseline, quality `283 passed`, preprocessing `106 passed`, and whitespace
with exit code `0` using external basetemp
`C:\Temp\PolyNexus_qt_font_runtime_verify`.

Evidence is tracked in
`docs/agent/tasks/2026-07-27-qt-font-runtime-acceptance.md`.
