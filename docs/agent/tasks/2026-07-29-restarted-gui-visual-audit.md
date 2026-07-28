---
task_id: 2026-07-29-restarted-gui-visual-audit
kind: release-verification-audit
status: completed
---

# Restarted GUI visual audit attempt

## Goal

Start the canonical GUI from the current checkout and obtain a fresh OS-level
visual capture for the remaining restarted-GUI release gate.

## Non-goals

- Do not change production code, fixtures, or GUI state on disk.
- Do not infer visual or scientific acceptance from a lock-screen image.
- Do not close the full release gate when the application content is not visible.

## Affected boundaries

- `scripts/launch_gui.py`
- Windows desktop/window capture
- Durable audit evidence only.

## Implementation plan

1. Launch the canonical GUI from `D:\PolyNexus`.
2. Confirm the real Qt window exists and is responsive.
3. Capture the desktop and the window handle to a temporary path.
4. Classify the evidence and close only the process started by this audit.

## Acceptance criteria

- [x] The canonical GUI starts from the current checkout.
- [x] The Qt window reports title `PolyNexus v2.0` and responds.
- [x] Both desktop and handle capture commands return image paths.
- [x] The lock-screen limitation is recorded without claiming GUI acceptance.
- [x] The audit-started GUI process is closed; no repository/data cleanup occurs.

## Verification

```powershell
$gui = Start-Process -FilePath 'D:\PolyNexus\Python\pythoncore-3.14-64\python.exe' `
  -ArgumentList 'scripts/launch_gui.py' -WorkingDirectory 'D:\PolyNexus' -PassThru
# GUI child: PID 16436; title PolyNexus v2.0; Responding=True

powershell -ExecutionPolicy Bypass -File `
  'C:\Users\Fan Xuyi\.codex\skills\screenshot\scripts\take_screenshot.ps1' -Mode temp
# C:\Users\Fan Xuyi\AppData\Local\Temp\codex-shot-2026-07-29_00-09-10.png

powershell -ExecutionPolicy Bypass -File `
  'C:\Users\Fan Xuyi\.codex\skills\screenshot\scripts\take_screenshot.ps1' `
  -WindowHandle 107548328 -Mode temp
# C:\Users\Fan Xuyi\AppData\Local\Temp\codex-shot-2026-07-29_00-09-52.png

python scripts/verify.py --task docs/agent/tasks/2026-07-29-restarted-gui-visual-audit.md --changed --types
git diff --check
```

## Result and limitation

The process was alive and responsive, but the Windows session was locked.
Both images show only the lock screen, not PolyNexus content. Therefore this
attempt is an environment limitation, not a product pass or failure. A user
unlocked session is required for the all-route restarted-GUI visual review.

## Explicit changed-file allowlist

- `docs/agent/tasks/2026-07-29-restarted-gui-visual-audit.md`
- `docs/acceptance/2026-07-29-restarted-gui-visual-audit.md`
- `docs/agent/memory/active-work.md`
