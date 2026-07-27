# Qt Font Runtime Acceptance

Status: automated evidence complete; live visual approval remains open
Date: 2026-07-27

## Goal

Verify that the canonical Windows Qt runtime resolves the GUI's CJK font
chain, and distinguish that evidence from offscreen screenshot limitations.

## Scope

- Scope: `polynexus/app.py`, `polynexus/gui/theme.py`, and the Windows Qt
  runtime used by the canonical worktree.
- Non-goals: changing scientific analysis, Matplotlib publication fonts,
  generated figures, or claiming pixel-level GUI approval from offscreen
  captures.

## Non-goals

- Changing scientific analysis, Matplotlib publication fonts, generated
  figures, or claiming pixel-level GUI approval from offscreen captures.

## Affected boundaries

- Read-only runtime checks at the `PySide6` application-font boundary.
- GUI acceptance and durable documentation under `docs/acceptance/` and
  `docs/agent/`.
- No core analysis, figure-generation, export, persistence, or dataset
  boundary is changed.

## Acceptance criteria

- [x] The real Windows Qt runtime has a non-empty font database.
- [x] `QApplication.font()` and `QFontInfo` resolve the requested CJK family.
- [x] Representative Chinese GUI characters report glyph coverage.
- [x] Offscreen font behavior is recorded as an environment limitation.
- [x] No production font or publication-style change is needed.
- [ ] Restarted-GUI pixel-level and all-route visual review is completed by a
  human reviewer.

## Evidence

Real Windows Qt runtime, with `QT_QPA_PLATFORM` unset:

```text
font_database_count=399
requested_family=Microsoft YaHei UI
app_font_family=Microsoft YaHei UI
resolved_family=Microsoft YaHei UI
resolved_point_size=10
glyphs={'中': True, '文': True, '温': True, '度': True, '应': True,
        '变': True, '结': True, '果': True}
```

The same diagnostic under `QT_QPA_PLATFORM=offscreen` returned:

```text
font_database_count=0
resolved_family=
glyphs={'中': False, '文': False, '温': False, '度': False, '应': False,
        '变': False, '结': False, '果': False}
```

Therefore, offscreen square glyphs cannot be used as evidence that the live
Windows GUI font chain is broken. The existing font chain remains:
`Microsoft YaHei UI` → `Microsoft YaHei` → `Noto Sans CJK SC` → `Source Han
Sans SC` → `Segoe UI Variable Text` → `Segoe UI`.

## Implementation plan

1. Inspect the application font assignment and theme fallback chain.
2. Run the same glyph diagnostic on the native Windows Qt platform and with
   the offscreen platform.
3. Record the evidence and leave production code unchanged when the native
   runtime has coverage.
4. Run the task-scoped verifier and preserve the remaining human visual gates.

## Verification

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-27-qt-font-runtime-acceptance.md --changed --types
python -c "from PySide6.QtWidgets import QApplication; from PySide6.QtGui import QFont,QFontInfo,QFontMetricsF,QFontDatabase; app=QApplication([]); app.setFont(QFont('Microsoft YaHei UI',10)); actual=app.font(); info=QFontInfo(actual); metrics=QFontMetricsF(actual); chars='中文温度应变结果'; print('font_database_count=',len(QFontDatabase.families())); print('app_font_family=',actual.family()); print('resolved_family=',info.family()); print('glyphs=',{ch:metrics.inFontUcs4(ord(ch)) for ch in chars}); app.quit()"
```

Result: exit code `0`; all live Windows glyph checks were `True`. The
offscreen comparison also exited `0` and demonstrated the empty font
database limitation.

Task-scoped verifier result: `python scripts/verify.py --task
docs/agent/tasks/2026-07-27-qt-font-runtime-acceptance.md --changed --types`
passed task/memory checks, Ruff, compile/type baseline, quality `283 passed`,
preprocessing `106 passed`, and whitespace checks with exit code `0`. The
verifier used external basetemp
`C:\Temp\PolyNexus_qt_font_runtime_verify`.

## Remaining release gates

This closes the automated font-runtime evidence gap only. It does not close
the normal-width right-edge review, restarted-GUI route walkthrough, real-data
scientific review, or final release/publication approval.
