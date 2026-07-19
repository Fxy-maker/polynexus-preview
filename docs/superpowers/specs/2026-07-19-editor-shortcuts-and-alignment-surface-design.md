# Editor Shortcuts and Alignment Surface Design

Date: 2026-07-19
Status: approved for implementation under the active editor-improvement Goal

Tool shortcuts are attached to the Matplotlib canvas with widget scope, so
single-letter commands do not interfere with QLineEdit text entry. Save/export
shortcuts remain window-scoped. Alignment actions call the existing batch mixin
with the six normalized modes: left, center, right, top, middle, bottom.
