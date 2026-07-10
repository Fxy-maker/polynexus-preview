from __future__ import annotations

import threading

from PySide6.QtCore import QObject, QRunnable, QThread, Signal

from .i18n import tr


def _main_window_module():
    from . import main_window as main_window_module

    return main_window_module


class AnalysisWorker(QThread):
    """Background thread for a single-technique analysis run."""

    log_msg = Signal(str)
    progress = Signal(int, int)
    finished = Signal(object)
    error_msg = Signal(str)

    def __init__(self, technique, filepath, output_dir, config=None, submodule_id=None, engine=None):
        super().__init__()
        self.technique = technique
        self.filepath = filepath
        self.output_dir = output_dir
        self.config = config
        self.submodule_id = submodule_id
        self.engine = engine
        self.skip_to = None

    def run(self):
        main_window_module = _main_window_module()
        logger = main_window_module.PolyNexusLogger.get()
        logger.attach_qt_signal(self.log_msg)

        try:
            logger.info(
                f"AnalysisWorker: technique={self.technique}, "
                f"file={main_window_module.os.path.basename(self.filepath)}"
            )
            engine = self.engine or main_window_module.get_engine(
                self.technique,
                config=self.config,
                submodule_id=getattr(self, "submodule_id", None),
            )
            if engine is None:
                msg = tr("ANALYSIS_UNKNOWN_TECHNIQUE", self.technique)
                logger.error(msg)
                self.error_msg.emit(msg)
                return
            self.engine = engine
            result = engine.run_pipeline(self.filepath, self.output_dir, skip_to=self.skip_to)
            self.finished.emit(result)
        except Exception as exc:
            msg = tr("ANALYSIS_WORKER_ERROR", exc, main_window_module.traceback.format_exc())
            logger.error(msg)
            self.error_msg.emit(msg)
            main_window_module.logger.warning("Single-file analysis worker failed.", exc_info=True)


class BatchWorker(QThread):
    """Background thread for batch (multi-file) analysis."""

    log_msg = Signal(str)
    progress = Signal(int, int)
    file_done = Signal(str, dict)
    batch_finished = Signal(list)
    error_msg = Signal(str)

    def __init__(self, technique, file_list, output_dir, config=None, submodule_id=None):
        super().__init__()
        self.technique = technique
        self.file_list = file_list
        self.output_dir = output_dir
        self.config = config
        self.submodule_id = submodule_id
        self.skip_to = None

    def run(self):
        main_window_module = _main_window_module()
        logger = main_window_module.PolyNexusLogger.get()
        logger.attach_qt_signal(self.log_msg)
        all_results = []
        total = len(self.file_list)

        logger.info(
            f"BatchWorker: technique={self.technique}, "
            f"files={total}, output={self.output_dir}"
        )

        for i, fp in enumerate(self.file_list):
            self.progress.emit(i + 1, total)
            fname = main_window_module.os.path.basename(fp)
            try:
                engine = main_window_module.get_engine(
                    self.technique,
                    config=self.config,
                    submodule_id=self.submodule_id,
                )
                file_out = main_window_module.os.path.join(
                    self.output_dir,
                    main_window_module.os.path.splitext(fname)[0],
                )
                result = engine.run_pipeline(fp, file_out)
                params = engine.get_parameters()
                self.file_done.emit(fname, params)
                logger.info(f"[{i+1}/{total}] {fname} - OK")
                all_results.append({"file": fname, "params": params})
            except Exception as exc:
                logger.error(f"[{i+1}/{total}] {fname} - FAILED: {exc}")
                main_window_module.logger.warning(
                    "Batch analysis worker failed for %s.",
                    fname,
                    exc_info=True,
                )

        self.batch_finished.emit(all_results)


class JointHubWorker(QThread):
    """Background thread for Joint Analysis Hub report generation."""

    finished = Signal(object)
    error_msg = Signal(str)

    def __init__(self, rows, output_dir):
        super().__init__()
        self.rows = rows
        self.output_dir = output_dir

    def run(self):
        main_window_module = _main_window_module()
        try:
            report = main_window_module.build_joint_hub_report(self.rows)
            self.finished.emit(report)
        except Exception as exc:
            self.error_msg.emit(tr("JOINT_OVERVIEW_FAILED", exc))
            main_window_module.logger.warning("Joint analysis worker failed.", exc_info=True)


class AITuneSignals(QObject):
    progress_msg = Signal(str)
    finished = Signal(object)
    error_msg = Signal(str)


class AITuneWorker(QRunnable):
    def __init__(
        self,
        technique,
        filepath,
        polymer,
        rounds=5,
        submodule_id=None,
        workspace_context=None,
        ai_settings=None,
    ):
        super().__init__()
        self.signals = AITuneSignals()
        self.technique = technique
        self.filepath = filepath
        self.polymer = polymer
        self.rounds = rounds
        self.submodule_id = submodule_id
        self.workspace_context = workspace_context or {}
        self.ai_settings = dict(ai_settings or {})
        self._cancel_event = threading.Event()

    def cancel(self):
        self._cancel_event.set()

    def run(self):
        main_window_module = _main_window_module()
        try:
            from polynexus.orchestrator import ParameterOrchestrator

            def progress(event):
                if self._cancel_event.is_set():
                    return
                score = event.get("after_r_squared", event.get("before_r_squared", 0.0))
                try:
                    score_text = f"{float(score):.3f}"
                except Exception:
                    score_text = str(score)
                    main_window_module.logger.warning(
                        "Failed to format AI tuning score for progress update.",
                        exc_info=True,
                    )
                self.signals.progress_msg.emit(
                    tr("AI_TUNING_PROGRESS_ROUND", event.get("round_num"), score_text)
                )

            report = ParameterOrchestrator(
                technique=self.technique,
                data_file=self.filepath,
                polymer_name=self.polymer,
                max_rounds=self.rounds,
                progress_callback=progress,
                submodule_override=self.submodule_id,
                workspace_context=self.workspace_context,
                llm_settings=self.ai_settings,
            ).run()
            if not self._cancel_event.is_set():
                self.signals.finished.emit(report)
        except Exception as exc:
            if not self._cancel_event.is_set():
                self.signals.error_msg.emit(
                    tr("AI_TUNING_FAILED", exc, main_window_module.traceback.format_exc())
                )
            main_window_module.logger.warning("AI tuning worker failed.", exc_info=True)
