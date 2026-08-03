from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
)

from .i18n import tr
from .widgets.saxs_tensile_axis_editor import SAXSTensileAxisEditor


class MainWindowConfigPanelMixin:
    @staticmethod
    def _main_window_module():
        from . import main_window as main_window_module

        return main_window_module

    @classmethod
    def _message_box_class(cls):
        return cls._main_window_module().QMessageBox

    @classmethod
    def _list_config_presets_fn(cls):
        return cls._main_window_module().list_config_presets

    @classmethod
    def _load_config_preset_fn(cls):
        return cls._main_window_module().load_config_preset

    @classmethod
    def _save_config_preset_fn(cls):
        return cls._main_window_module().save_config_preset

    @classmethod
    def _delete_config_preset_fn(cls):
        return cls._main_window_module().delete_config_preset

    def _update_config_panel(self):
        text_muted = self._main_window_module().C_TEXT_MUTED

        while self._config_form.rowCount() > 0:
            self._config_form.removeRow(0)
        submodule_id = getattr(self, "_current_submodule_id", "")

        if not submodule_id:
            lbl = QLabel(tr("CONFIG_SELECT_SUBMODULE"))
            lbl.setStyleSheet(f"color: {text_muted}; padding: 8px;")
            self._config_form.addRow(lbl)
            self._refresh_config_preset_controls()
            return

        from ..core.submodule_registry import list_all_submodules

        schema = {}

        for mod in list_all_submodules():
            if mod["id"] == submodule_id:
                schema = mod.get("config_schema", {})
                break

        if not schema:
            lbl = QLabel(tr("CONFIG_NO_SUBMODULE_CONFIG"))
            lbl.setStyleSheet(f"color: {text_muted}; padding: 8px;")
            self._config_form.addRow(lbl)
            self._refresh_config_preset_controls()
            return

        for key, spec in schema.items():
            self._add_config_field(key, spec)

        calibration_schema = self._calibration_config_schema()
        calibration_hint = self._calibration_hint_text()
        if calibration_schema and calibration_hint:
            lbl = QLabel(calibration_hint)
            lbl.setWordWrap(True)
            lbl.setProperty("config_hint_key", f"{self._current_technique}_calibration")
            lbl.setStyleSheet(f"color: {text_muted}; padding: 6px 0 10px 0;")
            self._config_form.addRow(lbl)

        for key, spec in calibration_schema.items():
            self._add_config_field(key, spec)

        mask_schema = self._mask_config_schema()
        mask_hint = self._mask_hint_text()
        if mask_hint and (
            mask_schema
            or str(getattr(self, "_current_technique", "") or "").strip().lower() == "waxs"
        ):
            lbl = QLabel(mask_hint)
            lbl.setWordWrap(True)
            lbl.setProperty("config_hint_key", f"{self._current_technique}_mask")
            lbl.setStyleSheet(f"color: {text_muted}; padding: 6px 0 10px 0;")
            self._config_form.addRow(lbl)

        for key, spec in mask_schema.items():
            self._add_config_field(key, spec)

        if mask_schema:
            summary_label = QLabel()
            summary_label.setWordWrap(True)
            summary_label.setProperty("config_hint_key", f"{self._current_technique}_mask_summary")
            summary_label.setStyleSheet(f"color: {text_muted}; padding: 0 0 8px 0;")
            self._config_form.addRow(summary_label)
            self._refresh_mask_summary_label()

        self._refresh_config_preset_controls()

    def _add_config_field(self, key, spec):
        field_type = spec.get("type", "string")
        label = spec.get("label", key)

        if field_type == "saxs_tensile_axis":
            widget = SAXSTensileAxisEditor()
        elif field_type == "choice":
            widget = QComboBox()
            widget.addItems(spec.get("options", []))
            default_value = spec.get("default", "")
            if default_value in spec.get("options", []):
                widget.setCurrentText(default_value)
        elif field_type == "int":
            widget = QSpinBox()
            widget.setRange(spec.get("min", 0), spec.get("max", 100))
            widget.setValue(spec.get("default", 0))
        elif field_type == "float":
            widget = QDoubleSpinBox()
            widget.setRange(spec.get("min", 0.0), spec.get("max", 1000.0))
            widget.setValue(spec.get("default", 1.0))
            widget.setDecimals(spec.get("decimals", 2))

            step = spec.get("step")
            if isinstance(step, (int, float)):
                widget.setSingleStep(float(step))
        elif field_type == "bool":
            widget = QCheckBox()
            widget.setChecked(spec.get("default", False))
            if label:
                widget.setText(label)
            label = ""
        else:
            widget = QLineEdit()
            widget.setText(str(spec.get("default", "")))

        if label:
            self._config_form.addRow(f"{label}:", widget)
        else:
            self._config_form.addRow(widget)

        widget.setProperty("config_key", key)
        self._connect_config_widget_signals(widget)
        return widget

    def _connect_config_widget_signals(self, widget):
        if isinstance(widget, QComboBox):
            widget.currentIndexChanged.connect(self._on_config_widget_changed)
        elif isinstance(widget, QDoubleSpinBox):
            widget.valueChanged.connect(self._on_config_widget_changed)
        elif isinstance(widget, QSpinBox):
            widget.valueChanged.connect(self._on_config_widget_changed)
        elif isinstance(widget, QCheckBox):
            widget.checkStateChanged.connect(self._on_config_widget_changed)
        elif isinstance(widget, QLineEdit):
            widget.textChanged.connect(self._on_config_widget_changed)

    def _on_config_widget_changed(self, *_args):
        self._refresh_mask_summary_label()

    def _calibration_config_schema(self):
        technique = str(getattr(self, "_current_technique", "") or "").strip().lower()
        if technique == "saxs":
            return {
                "crystallinity": {"type": "string", "default": "", "label": tr("CONFIG_SAXS_REFERENCE_CRYSTALLINITY")},
                "T_melt_expected": {"type": "string", "default": "", "label": tr("CONFIG_SAXS_EXPECTED_MELT")},
                "wavelength_m": {"type": "float", "default": 1.541891e-10, "min": 1e-12, "max": 1e-8, "decimals": 12, "step": 1e-11, "label": tr("CONFIG_SAXS_WAVELENGTH")},
                "pixel_size_m": {"type": "float", "default": 75e-6, "min": 1e-7, "max": 1e-2, "decimals": 6, "step": 1e-6, "label": tr("CONFIG_SAXS_PIXEL_SIZE")},
                "sdd_m": {"type": "float", "default": 0.450, "min": 0.01, "max": 10.0, "decimals": 4, "step": 0.01, "label": tr("CONFIG_SAXS_SDD")},
                "beam_center_x": {"type": "float", "default": 255.43, "min": 0.0, "max": 10000.0, "decimals": 2, "step": 1.0, "label": tr("CONFIG_SAXS_BEAM_CENTER_X")},
                "beam_center_y": {"type": "float", "default": 549.73, "min": 0.0, "max": 10000.0, "decimals": 2, "step": 1.0, "label": tr("CONFIG_SAXS_BEAM_CENTER_Y")},
                "poni_file": {"type": "string", "default": "", "label": tr("CONFIG_SAXS_PONI_FILE")},
            }
        if technique == "waxs":
            return {
                "wavelength_A": {"type": "float", "default": 1.5406, "min": 0.1, "max": 5.0, "decimals": 4, "step": 0.0001, "label": tr("CONFIG_WAXS_WAVELENGTH")},
                "two_theta_offset": {"type": "float", "default": 0.0, "min": -1.0, "max": 1.0, "decimals": 4, "step": 0.01, "label": tr("CONFIG_WAXS_TWO_THETA_OFFSET")},
            }
        return {}

    def _mask_config_schema(self):
        technique = str(getattr(self, "_current_technique", "") or "").strip().lower()
        if technique == "saxs":
            return {
                "auto_detect_beamstop": {"type": "bool", "default": True, "label": tr("CONFIG_SAXS_AUTO_DETECT_BEAMSTOP")},
                "beamstop_pollution_threshold": {"type": "float", "default": 100.0, "min": 5.0, "max": 5000.0, "decimals": 1, "step": 5.0, "label": tr("CONFIG_SAXS_BEAMSTOP_THRESHOLD")},
                "dummy_val": {"type": "float", "default": -1.5, "min": -1e6, "max": 1e6, "decimals": 3, "step": 0.1, "label": tr("CONFIG_SAXS_DUMMY_VALUE")},
                "ddummy": {"type": "float", "default": 0.6, "min": 0.0, "max": 1e4, "decimals": 3, "step": 0.1, "label": tr("CONFIG_SAXS_DDUMMY")},
            }
        return {}

    def _calibration_hint_text(self):
        technique = str(getattr(self, "_current_technique", "") or "").strip().lower()
        if technique == "saxs":
            return tr("CONFIG_CALIBRATION_HINT_SAXS")
        if technique == "waxs":
            return tr("CONFIG_CALIBRATION_HINT_WAXS")
        return ""

    def _mask_hint_text(self):
        technique = str(getattr(self, "_current_technique", "") or "").strip().lower()
        if technique == "saxs":
            return tr("CONFIG_MASK_HINT_SAXS")
        if technique == "waxs":
            return tr("CONFIG_MASK_HINT_WAXS")
        return ""

    def _build_run_config(self):
        config = None

        if self._current_technique == "dsc":
            from polynexus.core.dsc_engine.config import DSCConfig

            config = DSCConfig()

            if hasattr(self, "_dsc_dhm0_input"):
                dhm0 = self._dsc_dhm0_input.value()
                if dhm0 > 0:
                    config.user_DHm0 = dhm0

            if hasattr(self, "_dsc_mass_input"):
                config.mass_mg = self._dsc_mass_input.value()

        elif self._current_technique == "saxs":
            from polynexus.core.saxs_engine.config import SAXSConfig

            config = SAXSConfig()
            current_file = str(self._current_filepath or "").strip()
            current_technique = str(getattr(self, "_current_technique", "") or "").strip().lower()
            current_submodule = str(getattr(self, "_current_submodule_id", "") or "").strip()
            current_input_mode = str(getattr(self, "_current_input_mode", "") or "").strip().lower()
            sample_id = str(getattr(self, "_current_sample_id", "") or "").strip()
            batch_id = str(getattr(self, "_current_batch_id", "") or "").strip()
            batch_label = str(getattr(self, "_current_batch_label", "") or "").strip()
            sample_name = str(getattr(self, "_current_sample_name", "") or "").strip()
            context = {
                "file_path": current_file,
                "source_name": Path(current_file).name if current_file else "",
                "technique": current_technique,
                "submodule": current_submodule,
                "input_mode": current_input_mode,
                "sample_id": sample_id,
                "sample_name": sample_name,
                "batch_id": batch_id,
                "batch_label": batch_label,
            }
            if sample_id or batch_id:
                context["sample"] = {
                    "sample_id": sample_id,
                    "sample_name": sample_name,
                }
                context["batch"] = {
                    "batch_id": batch_id,
                    "batch_label": batch_label,
                    "file_path": current_file,
                }
            if batch_id:
                try:
                    db = self._ensure_sample_db()
                    batch = db.get_batch(batch_id)
                    if isinstance(batch, dict) and batch:
                        condition_values = batch.get("condition_values")
                        if isinstance(condition_values, dict) and condition_values:
                            context["condition_values"] = dict(condition_values)
                        context["batch"].update(
                            {
                                "condition_type": str(batch.get("condition_type", "") or ""),
                                "condition_values": dict(condition_values or {})
                                if isinstance(condition_values, dict)
                                else {},
                            }
                        )
                except Exception:
                    self._main_window_module().logger.warning(
                        "Failed to load sample batch context for SAXS config.",
                        exc_info=True,
                    )
            if sample_id:
                try:
                    db = self._ensure_sample_db()
                    sample = db.get_sample(sample_id)
                    if isinstance(sample, dict) and sample:
                        sample_meta = sample.get("metadata")
                        if isinstance(sample_meta, dict) and sample_meta:
                            context["sample"]["metadata"] = dict(sample_meta)
                except Exception:
                    self._main_window_module().logger.warning(
                        "Failed to load sample metadata for SAXS config.",
                        exc_info=True,
                    )
            config.condition_context = context

        elif self._current_technique == "waxs":
            from polynexus.core.waxs_engine.config import WAXSConfig

            config = WAXSConfig()

        panel_values = self._collect_config_panel_values()

        if panel_values:
            if config is None:
                config = panel_values
            else:
                if self._current_technique == "saxs":
                    from polynexus.core.saxs_config_binding import (
                        apply_saxs_config_panel_values,
                    )

                    apply_saxs_config_panel_values(config, panel_values)
                else:
                    for key, value in panel_values.items():
                        if hasattr(config, key):
                            setattr(config, key, value)

        return config

    def _build_config_for_technique(self, technique):
        text_muted = self._main_window_module().C_TEXT_MUTED

        while self._config_form.rowCount() > 0:
            self._config_form.removeRow(0)

        if technique == "dsc":
            tg = QComboBox()
            tg.addItems(["half_height", "inflection", "onset", "fictive"])
            self._config_form.addRow(tr("CONFIG_DSC_TG_METHOD"), tg)

            bl = QComboBox()
            bl.addItems(["auto", "linear", "tangential", "polynomial", "spline"])
            self._config_form.addRow(tr("CONFIG_DSC_BASELINE"), bl)

            self._dsc_dhm0_input = QDoubleSpinBox()
            self._dsc_dhm0_input.setRange(0, 999)
            self._dsc_dhm0_input.setValue(230)
            self._dsc_dhm0_input.setSuffix(" J/g")
            self._dsc_dhm0_input.setToolTip(tr("DSC_DHM0_TOOLTIP"))
            self._config_form.addRow(tr("CONFIG_DSC_HM0"), self._dsc_dhm0_input)

            self._dsc_mass_input = QDoubleSpinBox()
            self._dsc_mass_input.setRange(0.01, 999)
            self._dsc_mass_input.setValue(1.0)
            self._dsc_mass_input.setSuffix(" mg")
            self._dsc_mass_input.setDecimals(3)
            self._config_form.addRow(tr("CONFIG_DSC_SAMPLE_MASS"), self._dsc_mass_input)
        elif technique == "waxs":
            pf = QComboBox()
            pf.addItems(["pseudo_voigt", "gaussian", "lorentzian", "pearson_vii"])
            self._config_form.addRow(tr("CONFIG_WAXS_PEAK_FUNCTION"), pf)

            bg = QComboBox()
            bg.addItems(["polynomial", "spline", "chebyshev", "linear"])
            self._config_form.addRow(tr("CONFIG_WAXS_BACKGROUND"), bg)

            am = QComboBox()
            am.addItems(["spline", "polynomial", "manual"])
            self._config_form.addRow(tr("CONFIG_WAXS_AMORPHOUS"), am)
        elif technique == "saxs":
            im = QComboBox()
            im.addItems(["pyFAI", "manual"])
            self._config_form.addRow(tr("CONFIG_SAXS_INTEGRATION"), im)

            bs = QComboBox()
            bs.addItems(["subtract", "normalize", "none"])
            self._config_form.addRow(tr("CONFIG_SAXS_BACKGROUND"), bs)
        else:
            lbl = QLabel(tr("CONFIG_BASIC_ONLY"))
            lbl.setStyleSheet(f"color: {text_muted}; padding: 8px;")
            self._config_form.addRow(lbl)

        self._refresh_config_preset_controls()

    def _current_config_widget_keys(self):
        keys = []

        for row in range(self._config_form.rowCount()):
            item = self._config_form.itemAt(row, QFormLayout.FieldRole)
            if item is None:
                item = self._config_form.itemAt(row, QFormLayout.SpanningRole)
            widget = item.widget() if item is not None else None
            if widget is None:
                continue
            config_keys = getattr(widget, "config_keys", None)
            if callable(config_keys):
                keys.extend(str(key) for key in config_keys())
                continue
            key = widget.property("config_key")
            if key:
                keys.append(str(key))

        return keys

    def _config_widget_by_key(self, target_key):
        key = str(target_key or "").strip()
        if not key:
            return None

        for row in range(self._config_form.rowCount()):
            item = self._config_form.itemAt(row, QFormLayout.FieldRole)
            if item is None:
                item = self._config_form.itemAt(row, QFormLayout.SpanningRole)
            widget = item.widget() if item is not None else None
            if widget is not None and widget.property("config_key") == key:
                return widget
        return None

    def _config_hint_widget_by_key(self, hint_key):
        key = str(hint_key or "").strip()
        if not key:
            return None

        for row in range(self._config_form.rowCount()):
            item = self._config_form.itemAt(row, QFormLayout.SpanningRole)
            widget = item.widget() if item is not None else None
            if widget is not None and widget.property("config_hint_key") == key:
                return widget
        return None

    def _current_config_preset_scope(self):
        technique = str(getattr(self, "_current_technique", "") or "").strip().lower()
        submodule = str(getattr(self, "_current_submodule_id", "") or "").strip()

        if not technique or not submodule:
            return None
        if technique in {"joint", "samples"}:
            return None
        if not self._current_config_widget_keys():
            return None
        return technique, submodule

    def _current_config_preset_name(self):
        combo = getattr(self, "_config_preset_combo", None)
        if combo is None:
            return ""
        return str(combo.currentText() or "").strip()

    def _set_config_preset_placeholder(self, text):
        combo = getattr(self, "_config_preset_combo", None)
        if combo is None:
            return
        line_edit = combo.lineEdit()
        if line_edit is not None:
            line_edit.setPlaceholderText(text)

    def _on_config_preset_name_changed(self, _text):
        self._update_config_preset_action_state()

    def _update_config_preset_action_state(self, names=None):
        combo = getattr(self, "_config_preset_combo", None)
        if combo is None:
            return

        scope = self._current_config_preset_scope()
        has_scope = scope is not None
        if names is None and has_scope:
            names = self._list_config_presets_fn()(*scope)
        elif names is None:
            names = []

        current_name = self._current_config_preset_name()
        has_existing = has_scope and bool(current_name) and current_name in names

        combo.setEnabled(has_scope)
        if hasattr(self, "_btn_config_preset_save"):
            self._btn_config_preset_save.setEnabled(has_scope)
        if hasattr(self, "_btn_config_preset_load"):
            self._btn_config_preset_load.setEnabled(has_existing)
        if hasattr(self, "_btn_config_preset_delete"):
            self._btn_config_preset_delete.setEnabled(has_existing)
        self._refresh_recent_calibration_button()

    def _refresh_config_preset_controls(self):
        combo = getattr(self, "_config_preset_combo", None)
        if combo is None:
            return

        scope = self._current_config_preset_scope()
        names = self._list_config_presets_fn()(*scope) if scope is not None else []
        current_text = self._current_config_preset_name()

        combo.blockSignals(True)
        combo.clear()
        if names:
            combo.addItems(names)
        if current_text:
            combo.setEditText(current_text)
        elif names:
            combo.setCurrentIndex(0)
        combo.blockSignals(False)

        self._update_config_preset_action_state(names=names)

        placeholder_key = (
            "CONFIG_PRESET_NAME_PLACEHOLDER"
            if scope is not None else "CONFIG_PRESET_DISABLED_HINT"
        )
        self._set_config_preset_placeholder(tr(placeholder_key))

    def _on_save_config_preset(self):
        scope = self._current_config_preset_scope()
        if scope is None:
            self._message_box_class().warning(self, tr("CONFIG_PRESET_TITLE"), tr("CONFIG_PRESET_SCOPE_REQUIRED"))
            return

        preset_name = self._current_config_preset_name()
        if not preset_name:
            self._message_box_class().warning(self, tr("CONFIG_PRESET_TITLE"), tr("CONFIG_PRESET_NAME_REQUIRED"))
            return

        values = self._collect_config_panel_values()
        if not values:
            self._message_box_class().warning(self, tr("CONFIG_PRESET_TITLE"), tr("CONFIG_PRESET_EMPTY_PANEL"))
            return

        existing = self._load_config_preset_fn()(scope[0], scope[1], preset_name)
        message_box = self._message_box_class()
        if existing is not None:
            reply = message_box.question(
                self,
                tr("CONFIG_PRESET_TITLE"),
                tr("CONFIG_PRESET_OVERWRITE", preset_name),
                message_box.Yes | message_box.No,
                message_box.No,
            )
            if reply != message_box.Yes:
                return

        self._save_config_preset_fn()(scope[0], scope[1], preset_name, values)
        self._save_recent_calibration()
        self._refresh_config_preset_controls()
        self._config_preset_combo.setEditText(preset_name)
        self.log(tr("LOG_CONFIG_PRESET_SAVED", preset_name))

    def _on_load_config_preset(self):
        scope = self._current_config_preset_scope()
        if scope is None:
            self._message_box_class().warning(self, tr("CONFIG_PRESET_TITLE"), tr("CONFIG_PRESET_SCOPE_REQUIRED"))
            return

        preset_name = self._current_config_preset_name()
        if not preset_name:
            self._message_box_class().warning(self, tr("CONFIG_PRESET_TITLE"), tr("CONFIG_PRESET_NAME_REQUIRED"))
            return

        values = self._load_config_preset_fn()(scope[0], scope[1], preset_name)
        if values is None:
            self._message_box_class().warning(self, tr("CONFIG_PRESET_TITLE"), tr("CONFIG_PRESET_MISSING", preset_name))
            self._refresh_config_preset_controls()
            return

        current_keys = set(self._current_config_widget_keys())
        compatible_values = {key: value for key, value in values.items() if key in current_keys}
        if not compatible_values:
            self._message_box_class().warning(
                self,
                tr("CONFIG_PRESET_TITLE"),
                tr("CONFIG_PRESET_INCOMPATIBLE", preset_name),
            )
            return

        self._apply_best_config(compatible_values)
        self.log(tr("LOG_CONFIG_PRESET_LOADED", preset_name))

    def _on_delete_config_preset(self):
        scope = self._current_config_preset_scope()
        if scope is None:
            self._message_box_class().warning(self, tr("CONFIG_PRESET_TITLE"), tr("CONFIG_PRESET_SCOPE_REQUIRED"))
            return

        preset_name = self._current_config_preset_name()
        if not preset_name:
            self._message_box_class().warning(self, tr("CONFIG_PRESET_TITLE"), tr("CONFIG_PRESET_NAME_REQUIRED"))
            return

        existing = self._load_config_preset_fn()(scope[0], scope[1], preset_name)
        if existing is None:
            self._message_box_class().warning(self, tr("CONFIG_PRESET_TITLE"), tr("CONFIG_PRESET_MISSING", preset_name))
            self._refresh_config_preset_controls()
            return

        message_box = self._message_box_class()
        reply = message_box.question(
            self,
            tr("CONFIG_PRESET_TITLE"),
            tr("CONFIG_PRESET_DELETE_CONFIRM", preset_name),
            message_box.Yes | message_box.No,
            message_box.No,
        )
        if reply != message_box.Yes:
            return

        self._delete_config_preset_fn()(scope[0], scope[1], preset_name)
        self._refresh_config_preset_controls()
        self._config_preset_combo.setEditText("")
        self.log(tr("LOG_CONFIG_PRESET_DELETED", preset_name))

    def _collect_config_panel_values(self):
        values = {}

        for row in range(self._config_form.rowCount()):
            item = self._config_form.itemAt(row, QFormLayout.FieldRole)
            if item is None:
                item = self._config_form.itemAt(row, QFormLayout.SpanningRole)
            widget = item.widget() if item is not None else None
            if widget is None:
                continue
            values_fn = getattr(widget, "config_values", None)
            if callable(values_fn):
                values.update(values_fn())
                continue

            key = widget.property("config_key")
            if not key:
                continue

            if isinstance(widget, QComboBox):
                values[key] = widget.currentText()
            elif isinstance(widget, QDoubleSpinBox):
                values[key] = widget.value()
            elif isinstance(widget, QSpinBox):
                values[key] = widget.value()
            elif isinstance(widget, QCheckBox):
                values[key] = widget.isChecked()
            elif isinstance(widget, QLineEdit):
                values[key] = widget.text()

        return values
