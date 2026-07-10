from __future__ import annotations

import matplotlib


class ChartEditorRenderMixin:
    @staticmethod
    def _chart_editor_module():
        from . import chart_editor as chart_editor_module

        return chart_editor_module

    @classmethod
    def _logger(cls):
        return cls._chart_editor_module().logger

    def _render(self, *_):
        if self._fig_generator is None:
            if self._generated_document_mode:
                if self._show_generated_figure_document():
                    return
            if self._static_file_mode:
                if not self._refresh_static_annotation_canvas_preview():
                    self._show_style_preview_figure()
            return
        self._render_generator_figure()

    @matplotlib.rc_context()
    def _render_generator_figure(self):
        chart_editor_module = self._chart_editor_module()
        chart_editor_module._apply_sci_style(font_size=8.0)

        fig = chart_editor_module.Figure(
            figsize=self._fig_size,
            dpi=self._dpi,
            facecolor=self._bg_color,
        )
        ax = fig.add_subplot(111)
        try:
            self._fig_generator(ax, *self._fig_args, **self._fig_kwargs)
        except Exception as exc:
            import sys as _sys

            _sys.stderr.write(f"ChartEditor render failed: {exc}\n")
            self._logger().warning("Chart editor render failed.", exc_info=True)

        for i, line in enumerate(ax.lines):
            line.set_color(self._current_colours[i % len(self._current_colours)])
            line.set_linewidth(self._line_width)

        for i, coll in enumerate(ax.collections):
            try:
                coll.set_color(self._current_colours[i % len(self._current_colours)])
            except Exception:
                try:
                    coll.set_edgecolor(self._current_colours[i % len(self._current_colours)])
                except Exception:
                    self._logger().warning("Chart editor collection recolor failed.", exc_info=True)

        for i, patch in enumerate(ax.patches):
            try:
                patch.set_facecolor(self._current_colours[i % len(self._current_colours)])
            except Exception:
                self._logger().warning("Chart editor patch recolor failed.", exc_info=True)

        for container in ax.containers:
            try:
                for child in container.get_children():
                    child.set_color(self._current_colours[0])
                    child.set_linewidth(self._line_width)
            except Exception:
                self._logger().warning("Chart editor errorbar recolor failed.", exc_info=True)

        for txt in ax.texts:
            try:
                txt.set_fontsize(max(6, self._label_size - 2))
            except Exception:
                self._logger().warning("Chart editor text resize failed.", exc_info=True)

        legend = ax.get_legend()
        if legend is not None:
            try:
                for leg_text in legend.get_texts():
                    leg_text.set_fontsize(self._tick_size)
            except Exception:
                self._logger().warning("Chart editor legend resize failed.", exc_info=True)

        title = self._title_edit.text()
        if title:
            ax.set_title(title, fontsize=self._title_size, fontweight="bold")

        xlabel = self._xlabel_edit.text()
        if xlabel:
            ax.set_xlabel(xlabel, fontsize=self._label_size)

        ylabel = self._ylabel_edit.text()
        if ylabel:
            ax.set_ylabel(ylabel, fontsize=self._label_size)

        ax.tick_params(labelsize=self._tick_size)
        ax.grid(
            self._grid_on,
            alpha=self._grid_alpha,
            linestyle="--",
            linewidth=0.5,
        )
        for spine in ax.spines.values():
            spine.set_linewidth(0.8)

        import matplotlib.pyplot as plt

        old = self._canvas.figure
        self._canvas.figure = fig
        self._figure = fig
        self._connect_canvas_interaction_events()
        self._canvas.draw()
        if old:
            plt.close(old)
        self.figure_changed.emit()
