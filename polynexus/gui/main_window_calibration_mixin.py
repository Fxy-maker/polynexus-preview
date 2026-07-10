from __future__ import annotations

import json

from .i18n import tr


class MainWindowCalibrationMixin:
    @staticmethod
    def _main_window_module():
        from . import main_window as main_window_module

        return main_window_module

    @classmethod
    def _logger(cls):
        return cls._main_window_module().logger

    @classmethod
    def _message_box_class(cls):
        return cls._main_window_module().QMessageBox

    @classmethod
    def _path_class(cls):
        return cls._main_window_module().Path

    def _current_mask_summary_text(self):
        technique = str(getattr(self, "_current_technique", "") or "").strip().lower()
        if technique != "saxs":
            return ""

        auto_detect_widget = self._config_widget_by_key("auto_detect_beamstop")
        threshold_widget = self._config_widget_by_key("beamstop_pollution_threshold")
        dummy_widget = self._config_widget_by_key("dummy_val")
        ddummy_widget = self._config_widget_by_key("ddummy")
        if not all([auto_detect_widget, threshold_widget, dummy_widget, ddummy_widget]):
            return ""

        auto_detect = bool(auto_detect_widget.isChecked()) if hasattr(auto_detect_widget, "isChecked") else False
        try:
            threshold = float(threshold_widget.value())
        except Exception:
            threshold = 0.0
        try:
            dummy_val = float(dummy_widget.value())
        except Exception:
            dummy_val = 0.0
        try:
            ddummy = float(ddummy_widget.value())
        except Exception:
            ddummy = 0.0

        return tr(
            "CONFIG_MASK_SUMMARY_SAXS",
            tr("COMMON_ON") if auto_detect else tr("COMMON_OFF"),
            f"{threshold:.1f}",
            f"{dummy_val:.3f}",
            f"{ddummy:.3f}",
        )

    def _refresh_mask_summary_label(self):
        label = self._config_hint_widget_by_key(f"{self._current_technique}_mask_summary")
        if label is None:
            return
        summary = self._current_mask_summary_text()
        label.setText(summary)
        label.setVisible(bool(summary))

    def _current_calibration_scope(self):
        technique = str(getattr(self, "_current_technique", "") or "").strip().lower()
        submodule = str(getattr(self, "_current_submodule_id", "") or "").strip()
        calibration_keys = set(self._calibration_config_schema().keys())
        if technique not in {"saxs", "waxs"}:
            return None
        if not submodule or not calibration_keys:
            return None
        return technique, submodule

    def _calibration_settings_key(self, technique, submodule):
        return f"recent_calibration/{technique}/{submodule}"

    def _current_calibration_scope_label(self):
        scope = self._current_calibration_scope()
        if scope is None:
            return ""
        technique, submodule = scope
        technique_label = self._history_technique_text(technique)
        submodule_label = self._history_submodule_text(submodule) or submodule
        return f"{technique_label} / {submodule_label}"

    def _collect_calibration_panel_values(self):
        calibration_keys = set(self._calibration_config_schema().keys())
        if not calibration_keys:
            return {}
        values = self._collect_config_panel_values()
        return {key: value for key, value in values.items() if key in calibration_keys}

    def _compatible_recent_calibration_values(self, values):
        if not isinstance(values, dict):
            return {}, []
        calibration_keys = set(self._calibration_config_schema().keys())
        compatible = {key: value for key, value in values.items() if key in calibration_keys}
        ignored = sorted(str(key) for key in values.keys() if key not in calibration_keys)
        return compatible, ignored

    def _refresh_recent_calibration_button(self):
        button = getattr(self, "_btn_config_recent_calibration", None)
        save_button = getattr(self, "_btn_config_recent_calibration_save", None)
        if button is None and save_button is None:
            return

        scope_label = self._current_calibration_scope_label()
        values = self._load_recent_calibration()
        has_scope = bool(scope_label)
        has_values = isinstance(values, dict) and bool(values)

        if save_button is not None:
            save_button.setEnabled(has_scope)
            if has_scope:
                save_button.setToolTip(tr("CONFIG_RECENT_CALIBRATION_SAVE_TOOLTIP", scope_label))
            else:
                save_button.setToolTip(tr("CONFIG_RECENT_CALIBRATION_TOOLTIP_DISABLED"))

        if button is not None:
            button.setEnabled(has_values)
            if has_values and scope_label:
                button.setToolTip(tr("CONFIG_RECENT_CALIBRATION_TOOLTIP_READY", scope_label))
            elif has_scope:
                button.setToolTip(tr("CONFIG_RECENT_CALIBRATION_TOOLTIP_MISSING", scope_label))
            else:
                button.setToolTip(tr("CONFIG_RECENT_CALIBRATION_TOOLTIP_DISABLED"))

    def _save_recent_calibration(self):
        scope = self._current_calibration_scope()
        if scope is None:
            return

        values = self._collect_calibration_panel_values()
        if not values:
            return
        self._settings.setValue(
            self._calibration_settings_key(scope[0], scope[1]),
            json.dumps(values, ensure_ascii=False),
        )
        self._refresh_recent_calibration_button()

    def _load_recent_calibration(self):
        scope = self._current_calibration_scope()
        if scope is None:
            return None

        raw = self._settings.value(self._calibration_settings_key(scope[0], scope[1]), "")
        if not raw:
            return None
        try:
            values = json.loads(raw)
        except Exception:
            self._logger().warning("Failed to load recent calibration values from settings.", exc_info=True)
            return None
        return values if isinstance(values, dict) else None

    def _validate_calibration_inputs(self):
        if str(getattr(self, "_current_technique", "") or "").strip().lower() != "saxs":
            return True

        config = self._build_run_config()
        poni_file = str(getattr(config, "poni_file", "") or "").strip()
        if not poni_file:
            return True

        if self._path_class()(poni_file).expanduser().exists():
            return True

        self._message_box_class().warning(
            self,
            tr("CALIBRATION_PONI_MISSING_TITLE"),
            tr("CALIBRATION_PONI_MISSING_DETAIL", poni_file),
        )
        self.log(tr("CALIBRATION_PONI_MISSING_LOG", poni_file))
        return False

    def _validate_mask_inputs(self):
        if str(getattr(self, "_current_technique", "") or "").strip().lower() != "saxs":
            return True

        config = self._build_run_config()

        threshold = float(getattr(config, "beamstop_pollution_threshold", 100.0) or 0.0)
        if threshold < 20.0:
            self._message_box_class().warning(
                self,
                tr("MASK_CONFIG_WARNING_TITLE"),
                tr("MASK_BEAMSTOP_THRESHOLD_TOO_LOW", f"{threshold:.1f}"),
            )
            self.log(tr("MASK_BEAMSTOP_THRESHOLD_TOO_LOW_LOG", f"{threshold:.1f}"))
            return False

        ddummy = float(getattr(config, "ddummy", 0.0) or 0.0)
        if ddummy > 5.0:
            self._message_box_class().warning(
                self,
                tr("MASK_CONFIG_WARNING_TITLE"),
                tr("MASK_DDUMMY_TOO_LARGE", f"{ddummy:.3f}"),
            )
            self.log(tr("MASK_DDUMMY_TOO_LARGE_LOG", f"{ddummy:.3f}"))
            return False

        return True

    def _on_apply_recent_calibration(self):
        values = self._load_recent_calibration()
        if not values:
            self._message_box_class().warning(
                self,
                tr("CONFIG_RECENT_CALIBRATION_TITLE"),
                tr("CONFIG_RECENT_CALIBRATION_MISSING"),
            )
            return

        compatible_values, ignored_keys = self._compatible_recent_calibration_values(values)
        if not compatible_values:
            self._message_box_class().warning(
                self,
                tr("CONFIG_RECENT_CALIBRATION_TITLE"),
                tr("CONFIG_RECENT_CALIBRATION_INCOMPATIBLE"),
            )
            self.log(
                tr(
                    "LOG_RECENT_CALIBRATION_INCOMPATIBLE",
                    self._current_calibration_scope_label() or "-",
                )
            )
            return

        self._apply_best_config(compatible_values)
        self.log(tr("LOG_RECENT_CALIBRATION_APPLIED"))
        if ignored_keys:
            self.log(tr("LOG_RECENT_CALIBRATION_PARTIAL", ", ".join(ignored_keys)))

    def _on_save_recent_calibration(self):
        scope = self._current_calibration_scope()
        if scope is None:
            self._message_box_class().warning(
                self,
                tr("CONFIG_RECENT_CALIBRATION_TITLE"),
                tr("CONFIG_RECENT_CALIBRATION_SCOPE_REQUIRED"),
            )
            return

        values = self._collect_calibration_panel_values()
        if not values:
            self._message_box_class().warning(
                self,
                tr("CONFIG_RECENT_CALIBRATION_TITLE"),
                tr("CONFIG_RECENT_CALIBRATION_EMPTY"),
            )
            return

        self._save_recent_calibration()
        self.log(tr("LOG_RECENT_CALIBRATION_SAVED", self._current_calibration_scope_label() or "-"))
