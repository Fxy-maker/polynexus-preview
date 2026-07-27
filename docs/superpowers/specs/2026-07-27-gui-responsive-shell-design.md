# GUI responsive shell design

## Goal

Make the restarted canonical PolyNexus window usable at its default and
maximized desktop sizes without clipping the Results Workbench header or its
top-bar actions.

## Evidence and root cause

The restarted process was verified by `scripts/launch_gui.py --diagnose` to
load `D:\PolyNexus` and the current branch. A real screenshot showed the
default 1280-pixel window and the maximized window both clipped on the right.
`MainWindowShellMixin._apply_responsive_shell()` currently uses only the full
window width and keeps the header metrics and secondary top-bar actions visible
until the window is below 1120 pixels. The content width is smaller because the
sidebar consumes part of the window, and the header/top-bar layouts have no
overflow-aware compression policy.

## Design

Keep the existing Workbench information architecture and make the shell
responsive at the shell boundary:

1. Derive the compact decision from the actual content width when available,
   with the window width as a test-double fallback.
2. In compact content, hide non-essential workflow metrics while keeping the
   task card and workspace title visible. The task detail remains word-wrapped.
3. When the top-bar layout reports overflow, hide replot and export shortcuts
   in priority order; their File-menu/export routes remain available.
4. Give the top-bar and header's flexible widgets zero minimum width and an
   expanding/ignored horizontal policy so long localized labels do not force a
   viewport wider than the window.
5. Place the History action toolbar in an internal horizontal scroll container
   so all actions remain available without forcing the whole Workbench wider
   than the viewport.
6. Keep the behavior centralized at the GUI shell boundary; no technique-specific
   analysis or publication logic moves into GUI event handlers.

## Non-goals

- Do not change scientific calculations, evidence states, figure roles,
  Results Workbench profiles, or export contracts.
- Do not replace the existing sidebar, tabs, or menu navigation.
- Do not delete user data, real fixtures, generated outputs, or scratch files.

## Acceptance

- At a window width of 1280 with a narrower content area, secondary metrics and
  top-bar shortcuts collapse without hiding the task card.
- At a sufficiently wide content area, the full metric and shortcut set remains
  visible.
- The focused shell regression covers the content-width decision and overflow
  priority.
- A restarted canonical GUI screenshot shows no right-edge clipping after the
  fix.
