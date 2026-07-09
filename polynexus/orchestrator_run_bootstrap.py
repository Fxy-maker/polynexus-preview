from __future__ import annotations

from copy import deepcopy


def _initialize_run_session(self):
    from polynexus import orchestrator as orchestrator_module

    data_path = self._resolve_data_file(self.data_file)
    submodule_id = self._submodule_id()
    engine = orchestrator_module.get_engine(self.technique, submodule_id=submodule_id)
    if engine is None:
        raise RuntimeError(f"{self.technique.upper()} engine is not registered.")
    self._engine = engine

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
