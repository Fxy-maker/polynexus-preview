---
task_id: 2026-07-29-full-goal-requirements-audit
kind: release-verification-audit
status: completed
---

# Full-software goal requirements audit

## Goal

Map every explicit full-software delivery requirement to current authoritative
evidence and preserve the distinction between automated proof, visual evidence,
and human scientific/release approval.

## Non-goals

- Do not mark the overall delivery task complete from partial or provider-only
  evidence.
- Do not infer IR mapping/ROI, NMR assignment, or Joint conflict semantics.
- Do not delete or migrate test data, source files, or scratch artifacts.

## Affected boundaries

- Overall task card `docs/agent/tasks/2026-07-25-full-software-vertical-delivery.md`
- Shared platform, all technique mode acceptance records, and release gates.
- Durable audit/acceptance documentation only.

## Implementation plan

1. Read the total goal, module order, acceptance criteria, and current evidence.
2. Map shared and mode-specific automated evidence to each named requirement.
3. Mark missing/weak evidence and human decisions explicitly.
4. Verify and checkpoint this audit without changing product behavior.

## Requirement matrix

| Requirement | Current evidence | Classification |
| --- | --- | --- |
| Shared Results Workbench/profile/Figure contracts | `57 passed` Workbench/Figure matrix; full boundary `2986 passed` | automated evidence |
| Input/preprocessing and Golden path | real walkthrough `15 passed`; Golden `3 passed`; AI/fallback `25 passed` | automated evidence |
| SAXS static/temperature/strain | real `3` cases and native route `3`; SAXS-specific contracts | automated evidence; temperature/strain science open |
| DSC standard/isothermal/non-isothermal | real `3` cases and native route `3` | automated evidence; non-isothermal role review open |
| WAXS static/temperature/strain/2D | real `3` cases including strain/2D and native route `3` | automated evidence; scientific review open |
| IR standard/temperature-2D/mapping | real `2`, native `2`, synthetic mapping route; official Thermo/OMNIC Picta semantics profile | reviewer disposition recorded as diagnostic-only; native map, sample ROI, flattening order, detector calibration, and source-matched promotion evidence remain absent |
| NMR liquid H/C/solid H/C | real `4` and native `4`; JEOL axis provenance and assignment-limited status are explicit | reviewer disposition recorded: ambiguous solid-C peaks remain unassigned and Xc promotion is prohibited without assignment truth and calibrated axis |
| Joint provenance/lifecycle | real transport, synthetic lifecycle, deterministic AI boundary, and native route evidence | reviewer disposition recorded: no automatic technique priority; unresolved conflicts remain diagnostic-only |
| Manifest/Gallery/Editor/export/history | real published-run lifecycle plus current native route captures for Results/Gallery/History/Editor/PackageExporter fallback | route construction is evidenced; complete human visual review and release approval remain open |
| AI-off/failure/fallback | fresh `25 passed` matrix | automated safety evidence; scientific approval open |
| Full repository/boundary gate | `2986 passed, 17 skipped, 12 warnings`; direct boundary exit `0` | automated gate green |
| Restarted-GUI visual acceptance | current native selector completed `17` cases with Results/Gallery/History/Editor/PackageExporter captures; canonical shell was also inspected unlocked | route evidence is recorded; complete all-mode human visual acceptance remains separate |
| Human scientific/release approval | Conservative IR, NMR solid-C, and Joint dispositions recorded in the release packet | final release remains conditional on source-specific evidence, restarted-GUI review, and the separate SAXS decision |

## Acceptance criteria

- [x] Every named technique/mode has an evidence classification.
- [x] Automated evidence is separated from visual and scientific approval.
- [x] Missing evidence and the next external requirement are explicit.
- [x] No production/data/scratch mutation is introduced by this audit.

## Verification

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-29-full-goal-requirements-audit.md --changed --types
git diff --check
```

## Conclusion

The automated implementation/lifecycle gates are substantially evidenced, and
the conservative IR/NMR/Joint dispositions are now recorded. The overall
delivery task remains active because the source-specific payloads are absent,
complete all-route visual inspection is not yet the final release authority,
and SAXS plus final project authorization remain separate conditions.

## Explicit changed-file allowlist

- `docs/agent/tasks/2026-07-29-full-goal-requirements-audit.md`
- `docs/acceptance/2026-07-29-full-goal-requirements-audit.md`
- `docs/agent/memory/active-work.md`
