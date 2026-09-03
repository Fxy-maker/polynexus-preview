# Contributing to PolyNexus

PolyNexus is an AI-oriented polymer research workbench. Contributions are
welcome, especially deterministic analysis improvements, import templates,
tests, documentation, and interoperability adapters.

## Contribution boundary

The Core owns deterministic calculations, canonical data conversion, result
provenance, and shared project/run/chart/evidence/export contracts. AI, GUI,
CLI, and plugins must consume or request those public contracts; they must not
invent scientific values or create a private persistence representation.

Please keep every new capability honest about its maturity:

- `available`: a deterministic provider, declared inputs/outputs, focused
  regression tests, and documented scientific limits exist.
- `experimental`: the route is intentionally discoverable for evaluation, but
  its provider, validation range, or evidence semantics are incomplete.
- `unsupported`: no executable provider is supplied. Do not emit placeholder
  scientific values for it.

## Before opening a change

- Read `AGENTS.md` and the relevant public contract.
- Preserve unrelated local changes.
- Add or update a focused regression test for behavior changes.
- Keep GUI, CLI, and AI routes on the same public result objects.
- Do not commit raw user measurements, generated evidence packages, local
  databases, logs, API keys, or machine-specific configuration.
- Include only sample data that you have the right to redistribute, together
  with its source and license in the fixture documentation.

Run the focused tests for the changed boundary, then run:

```powershell
python scripts/verify.py --changed --types
```

See [the open-source guide](docs/OPEN_SOURCE.md) for release boundaries and
the [agent contract](AGENTS.md) for repository workflow details.
