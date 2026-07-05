
"""
PolyNexus structured logging module.

Provides a unified logging facility with:
  - INFO / WARNING / ERROR / DEBUG levels
  - Per-run log files in the output directory
  - Qt-signal-compatible handler for GUI live display
  - Thread-safe operation for AnalysisWorker / BatchWorker

Usage (CLI):
    from polynexus.utils.logger import PolyNexusLogger
    logger = PolyNexusLogger.get()
    with logger.run_context("saxs", "output/"):
        logger.info("Starting analysis...")
        # ... engine.run_pipeline() ...

Usage (GUI):
    from polynexus.utils.logger import PolyNexusLogger
    logger = PolyNexusLogger.get()
    logger.attach_qt_signal(self.log_signal)  # QThread Signal(str)
    with logger.run_context("waxs", "output/"):
        ...
"""

import logging
import logging.handlers
import os
import sys
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable


# ---------------------------------------------------------------------------
#  Qt signal handler (optional PySide6 dependency)
# ---------------------------------------------------------------------------

class QtLogHandler(logging.Handler):
    """Logging handler that emits each record via a Qt Signal.

    Attach to a PolyNexusLogger with::

        logger.attach_qt_signal(self.log_signal)  # Signal(str)
    """

    def __init__(self, signal=None):
        super().__init__()
        self._signal = signal
        self.setLevel(logging.DEBUG)
        self.setFormatter(logging.Formatter("%(levelname)-5s %(message)s"))

    def emit(self, record: logging.LogRecord):
        if self._signal is not None:
            try:
                msg = self.format(record)
                self._signal.emit(msg)
            except Exception:
                self.handleError(record)

    def set_signal(self, signal):
        self._signal = signal


# ---------------------------------------------------------------------------
#  PolyNexusLogger
# ---------------------------------------------------------------------------

class PolyNexusLogger:
    """Singleton logger for PolyNexus analysis runs.

    Features
    --------
    - Four levels: debug / info / warning / error
    - Per-run file handler writing to ``<output_dir>/<technique>_<timestamp>.log``
    - Optional console output (CLI mode)
    - Optional Qt-signal output (GUI mode)
    - Thread-safe (locking around handler add/remove)
    - Context-manager support for automatic setup / teardown

    Singleton access
    ----------------
        logger = PolyNexusLogger.get()
    """

    _instance: Optional["PolyNexusLogger"] = None
    _lock = threading.Lock()

    # ------------------------------------------------------------------
    #  Singleton
    # ------------------------------------------------------------------

    @classmethod
    def get(cls) -> "PolyNexusLogger":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    #  Construction
    # ------------------------------------------------------------------

    def __init__(self):
        if PolyNexusLogger._instance is not None:
            raise RuntimeError("Use PolyNexusLogger.get()")
        PolyNexusLogger._instance = self

        self._logger = logging.getLogger("polynexus")
        self._logger.setLevel(logging.DEBUG)
        self._logger.propagate = False

        self._file_handler: Optional[logging.FileHandler] = None
        self._console_handler: Optional[logging.StreamHandler] = None
        self._qt_handler: Optional[QtLogHandler] = None
        self._handler_lock = threading.Lock()
        self._current_output_dir: str = ""

        # Default: console only
        self.enable_console()

    # ------------------------------------------------------------------
    #  Public logging methods (mirrors stdlib logging levels)
    # ------------------------------------------------------------------

    def debug(self, msg: str, *args, **kwargs):
        self._logger.debug(msg, *args, **kwargs)

    def info(self, msg: str, *args, **kwargs):
        self._logger.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs):
        self._logger.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs):
        self._logger.error(msg, *args, **kwargs)

    def exception(self, msg: str, *args, **kwargs):
        """Log ERROR with traceback (call inside an except block)."""
        self._logger.exception(msg, *args, **kwargs)

    # ------------------------------------------------------------------
    #  Handler management
    # ------------------------------------------------------------------

    def enable_console(self, stream=None, level=logging.INFO):
        """Attach a console (stderr) handler for CLI output."""
        with self._handler_lock:
            self._remove_handler(self._console_handler)
            fmt = logging.Formatter(
                "[%(asctime)s] %(levelname)-5s %(name)s: %(message)s",
                datefmt="%H:%M:%S",
            )
            self._console_handler = logging.StreamHandler(stream or sys.stderr)
            self._console_handler.setLevel(level)
            self._console_handler.setFormatter(fmt)
            self._logger.addHandler(self._console_handler)

    def disable_console(self):
        with self._handler_lock:
            self._remove_handler(self._console_handler)
            self._console_handler = None

    def attach_qt_signal(self, signal):
        """Attach a Qt Signal(str) for live GUI log display.

        Parameters
        ----------
        signal : PySide6.QtCore.Signal
            e.g. ``Signal(str)`` from a QThread or QWidget.
        """
        with self._handler_lock:
            if self._qt_handler is not None:
                self._qt_handler.set_signal(signal)
            else:
                self._qt_handler = QtLogHandler(signal)
                self._logger.addHandler(self._qt_handler)

    def detach_qt_signal(self):
        with self._handler_lock:
            if self._qt_handler is not None:
                self._qt_handler.set_signal(None)

    # ------------------------------------------------------------------
    #  Run-scoped file logging
    # ------------------------------------------------------------------

    @contextmanager
    def run_context(self, technique: str, output_dir: str):
        """Context manager: setup file logging for one analysis run.

        Usage::

            with logger.run_context("saxs", "output/saxs_results"):
                logger.info("Starting ...")
                engine.run_pipeline(...)
                logger.info("Done.")

        On enter: creates ``<output_dir>/<technique>_<timestamp>.log``.
        On exit:  closes the file handler, retains console / Qt handlers.
        """
        self.setup_run(technique, output_dir)
        try:
            yield
        finally:
            self.teardown_run()

    def setup_run(self, technique: str, output_dir: str):
        """Open a per-run log file in *output_dir*.

        File name: ``<technique>_<YYYYMMDD_HHMMSS>.log``
        """
        with self._handler_lock:
            # Close previous file handler if any
            self._remove_handler(self._file_handler)

            # Ensure output directory exists
            out = Path(output_dir)
            out.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_path = out / f"{technique}_{timestamp}.log"
            self._current_output_dir = str(out)

            self._file_handler = logging.FileHandler(str(log_path), encoding="utf-8")
            self._file_handler.setLevel(logging.DEBUG)
            self._file_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s %(levelname)-8s %(name)s: %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            )
            self._logger.addHandler(self._file_handler)

            self._logger.info("=" * 60)
            self._logger.info(f"PolyNexus {technique.upper()} analysis started")
            self._logger.info(f"Log file: {log_path}")
            self._logger.info(f"Output directory: {output_dir}")
            self._logger.info("=" * 60)

    def teardown_run(self):
        """Close the per-run file handler."""
        with self._handler_lock:
            self._logger.info("=" * 60)
            self._logger.info("Analysis finished")
            self._logger.info("=" * 60)
            self._remove_handler(self._file_handler)
            self._file_handler = None

    @property
    def current_output_dir(self) -> str:
        return self._current_output_dir

    # ------------------------------------------------------------------
    #  Convenience: backward-compatible callable for engine.log_fn
    # ------------------------------------------------------------------

    def as_log_fn(self, prefix: str = "") -> Callable[[str], None]:
        """Return a callable suitable as ``engine.log_fn`` for old code.

        Each call is logged at INFO level.
        """
        def _log(msg: str):
            self.info(f"[{prefix}] {msg}" if prefix else msg)

        return _log

    # ------------------------------------------------------------------
    #  Internal
    # ------------------------------------------------------------------

    def _remove_handler(self, handler):
        if handler is not None:
            try:
                self._logger.removeHandler(handler)
            except Exception:
                pass
            try:
                handler.close()
            except Exception:
                pass


# ---------------------------------------------------------------------------
#  Module-level convenience
# ---------------------------------------------------------------------------

def get_logger() -> PolyNexusLogger:
    """Shorthand for ``PolyNexusLogger.get()``."""
    return PolyNexusLogger.get()
