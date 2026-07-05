"""PolyNexus settings dialog: language, theme, and AI connection settings."""

from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QWidget,
    QVBoxLayout,
)
from PySide6.QtCore import Qt

from llm.config import (
    AI_PROVIDER_DEEPSEEK,
    AI_PROVIDER_OPENAI,
    default_ai_settings,
    load_ai_settings,
    normalize_ai_provider,
    normalize_ai_settings,
    provider_defaults,
    provider_label,
    save_ai_settings,
    create_llm_client,
)

from ..i18n import get_language, set_language, tr
from ..theme import ThemeEngine


class SettingsDialog(QDialog):
    """Application settings dialog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("SETTINGS_TITLE"))
        self.setMinimumWidth(560)
        self.setModal(True)

        self._theme_engine = ThemeEngine.instance()
        self._ai_settings = default_ai_settings()
        self._ai_provider_defaults = provider_defaults(AI_PROVIDER_DEEPSEEK)
        self._setup_ui()
        self._load_current_values()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        lang_group = QGroupBox(tr("SETTINGS_LANGUAGE"))
        lang_layout = QFormLayout(lang_group)
        self._lang_combo = QComboBox()
        self._lang_combo.addItem(tr("SETTINGS_LANG_ZH"), "zh")
        self._lang_combo.addItem(tr("SETTINGS_LANG_EN"), "en")
        lang_layout.addRow(tr("SETTINGS_LANGUAGE") + ":", self._lang_combo)
        layout.addWidget(lang_group)

        theme_group = QGroupBox(tr("SETTINGS_THEME"))
        theme_layout = QFormLayout(theme_group)
        self._theme_combo = QComboBox()
        self._theme_combo.addItem(tr("SETTINGS_THEME_DARK"), "dark")
        self._theme_combo.addItem(tr("SETTINGS_THEME_LIGHT"), "light")
        theme_layout.addRow(tr("SETTINGS_THEME") + ":", self._theme_combo)
        layout.addWidget(theme_group)

        ai_group = QGroupBox(tr("SETTINGS_AI"))
        ai_layout = QFormLayout(ai_group)

        self._ai_provider_combo = QComboBox()
        self._ai_provider_combo.addItem(provider_label(AI_PROVIDER_DEEPSEEK), AI_PROVIDER_DEEPSEEK)
        self._ai_provider_combo.addItem(provider_label(AI_PROVIDER_OPENAI), AI_PROVIDER_OPENAI)
        self._ai_provider_combo.currentIndexChanged.connect(self._sync_ai_defaults)
        ai_layout.addRow(tr("SETTINGS_AI_PROVIDER") + ":", self._ai_provider_combo)

        self._ai_api_key_edit = QLineEdit()
        self._ai_api_key_edit.setEchoMode(QLineEdit.Password)
        self._ai_api_key_edit.setClearButtonEnabled(True)
        ai_layout.addRow(tr("SETTINGS_AI_API_KEY") + ":", self._ai_api_key_edit)

        self._ai_base_url_edit = QLineEdit()
        self._ai_base_url_edit.setClearButtonEnabled(True)
        ai_layout.addRow(tr("SETTINGS_AI_BASE_URL") + ":", self._ai_base_url_edit)

        self._ai_model_edit = QLineEdit()
        self._ai_model_edit.setClearButtonEnabled(True)
        ai_layout.addRow(tr("SETTINGS_AI_MODEL") + ":", self._ai_model_edit)

        self._ai_allow_mock_check = QCheckBox(tr("SETTINGS_AI_ALLOW_MOCK"))
        ai_layout.addRow("", self._ai_allow_mock_check)

        ai_button_row = QWidget()
        ai_button_row_layout = QHBoxLayout(ai_button_row)
        ai_button_row_layout.setContentsMargins(0, 0, 0, 0)
        self._btn_test_ai = QPushButton(tr("SETTINGS_AI_TEST"))
        self._btn_test_ai.clicked.connect(self._on_test_connection)
        ai_button_row_layout.addWidget(self._btn_test_ai)
        ai_button_row_layout.addStretch()
        ai_layout.addRow("", ai_button_row)

        layout.addWidget(ai_group)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self._btn_reset = QPushButton(tr("SETTINGS_RESET"))
        self._btn_reset.clicked.connect(self._on_reset)
        btn_layout.addWidget(self._btn_reset)

        self._btn_close = QPushButton(tr("SETTINGS_CLOSE"))
        self._btn_close.clicked.connect(self._on_apply_and_close)
        self._btn_close.setDefault(True)
        btn_layout.addWidget(self._btn_close)

        layout.addLayout(btn_layout)

    def _load_current_values(self):
        lang_idx = self._lang_combo.findData(get_language())
        if lang_idx >= 0:
            self._lang_combo.setCurrentIndex(lang_idx)

        theme_idx = self._theme_combo.findData(self._theme_engine.current)
        if theme_idx >= 0:
            self._theme_combo.setCurrentIndex(theme_idx)

        self._ai_settings = load_ai_settings(getattr(self.parent(), "_settings", None)) if self.parent() else default_ai_settings()
        provider_key = normalize_ai_provider(self._ai_settings.get("provider"))
        provider_idx = self._ai_provider_combo.findData(provider_key)
        if provider_idx >= 0:
            self._ai_provider_combo.setCurrentIndex(provider_idx)
        self._ai_provider_defaults = provider_defaults(provider_key)
        self._ai_api_key_edit.setText(str(self._ai_settings.get("api_key", "") or ""))
        self._ai_base_url_edit.setText(str(self._ai_settings.get("base_url", "") or ""))
        self._ai_model_edit.setText(str(self._ai_settings.get("model", "") or ""))
        self._ai_allow_mock_check.setChecked(bool(self._ai_settings.get("allow_mock", True)))

    def _sync_ai_defaults(self, *_args):
        provider = normalize_ai_provider(self._ai_provider_combo.currentData())
        new_defaults = provider_defaults(provider)
        old_defaults = getattr(self, "_ai_provider_defaults", default_ai_settings())

        base_url = self._ai_base_url_edit.text().strip()
        if not base_url or base_url == old_defaults.get("base_url", ""):
            self._ai_base_url_edit.setText(new_defaults["base_url"])

        model = self._ai_model_edit.text().strip()
        if not model or model == old_defaults.get("model", ""):
            self._ai_model_edit.setText(new_defaults["model"])

        self._ai_provider_defaults = new_defaults

    def _collect_ai_settings(self):
        return normalize_ai_settings(
            provider=self._ai_provider_combo.currentData(),
            api_key=self._ai_api_key_edit.text(),
            base_url=self._ai_base_url_edit.text(),
            model=self._ai_model_edit.text(),
            allow_mock=self._ai_allow_mock_check.isChecked(),
        )

    def _on_apply_and_close(self):
        new_lang = self._lang_combo.currentData()
        if new_lang != get_language():
            set_language(new_lang)
            if self.parent():
                try:
                    self.parent()._retranslate_ui()
                except AttributeError:
                    pass

        new_theme = self._theme_combo.currentData()
        if new_theme != self._theme_engine.current:
            self._theme_engine.switch(new_theme)

        parent_settings = getattr(self.parent(), "_settings", None)
        if parent_settings is not None:
            save_ai_settings(parent_settings, self._collect_ai_settings())

        self.accept()

    def _on_test_connection(self):
        ai_settings = self._collect_ai_settings()
        client = create_llm_client(ai_settings, timeout=10, allow_mock=False)
        provider_text = provider_label(ai_settings.get("provider"))
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            client.chat(
                "Connection test. Reply with OK only.",
                system="You are a connection test. Reply with OK only.",
            )
        except Exception as exc:
            QMessageBox.warning(
                self,
                tr("SETTINGS_TITLE"),
                tr("SETTINGS_AI_TEST_FAIL", provider_text, exc),
            )
        else:
            QMessageBox.information(
                self,
                tr("SETTINGS_TITLE"),
                tr(
                    "SETTINGS_AI_TEST_OK",
                    provider_text,
                    ai_settings.get("model", ""),
                    ai_settings.get("base_url", ""),
                ),
            )
        finally:
            QApplication.restoreOverrideCursor()

    def _on_reset(self):
        reply = QMessageBox.question(
            self,
            tr("SETTINGS_RESET"),
            tr("SETTINGS_RESET_CONFIRM"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        self._lang_combo.setCurrentIndex(self._lang_combo.findData("en"))
        self._theme_combo.setCurrentIndex(self._theme_combo.findData("dark"))

        default_provider_idx = self._ai_provider_combo.findData(AI_PROVIDER_DEEPSEEK)
        if default_provider_idx >= 0:
            self._ai_provider_combo.setCurrentIndex(default_provider_idx)
        defaults = provider_defaults(AI_PROVIDER_DEEPSEEK)
        self._ai_provider_defaults = defaults
        self._ai_api_key_edit.clear()
        self._ai_base_url_edit.setText(defaults["base_url"])
        self._ai_model_edit.setText(defaults["model"])
        self._ai_allow_mock_check.setChecked(True)
