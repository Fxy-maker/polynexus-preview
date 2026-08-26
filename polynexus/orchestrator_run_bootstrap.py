from __future__ import annotations

from copy import deepcopy

from polynexus.core.compute import ComputeRunService


def _initialize_run_session(self):
    from polynexus import orchestrator as orchestrator_module

    data_path = self._resolve_data_file(self.data_file)
    submodule_id = self._submodule_id()
    engine = orchestrator_module.get_engine(self.technique, submodule_id=submodule_id)
    if engine is None:
        raise RuntimeError(f"{self.technique.upper()} engine is not registered.")
    self._engine = engine

    # Valid source files use the same canonical run producer as Quick Analysis,
    # Batch, and Agent/Codex.  The in-memory engine is still supplied so later
    # candidate rounds can mutate and replay its controlled configuration.
    self._compute_run = None
    if data_path.exists():
        compute_run = ComputeRunService(
            lambda *args, **kwargs: engine,
        ).run_direct(
            technique=self.technique,
            path=data_path,
            output_dir="",
            submodule_id=submodule_id,
            engine=engine,
        )
        if compute_run.status != "completed":
            raise RuntimeError(
                ", ".join(compute_run.reasons) or compute_run.status
            )
        self._compute_run = compute_run
    else:
        # Existing synthetic callers use a provider-only fake path.  Do not
        # fabricate a canonical artifact for a source that cannot be hashed.
        engine.run_pipeline(str(data_path), output_dir="")
    baseline = self._record_round(engine, 0, None, changes={}, accepted=True)
    self.history.append(baseline)
    self._baseline_r_squared = baseline.r_squared
    self._best_r_squared = baseline.r_squared
    self._baseline_eval_score = baseline.eval_score
    self._best_eval_score = baseline.eval_score
    self._best_config = deepcopy(self._engine_config(engine))
    self._best_output = dict(baseline.output_parameters)
    self._best_record = baseline

    return data_path, engine, baseline
