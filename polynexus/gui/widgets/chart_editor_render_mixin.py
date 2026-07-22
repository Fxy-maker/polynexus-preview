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

    def _schedule_text_render(self, *_):
        timer = getattr(self, "_text_render_timer", None)
        if timer is None:
            self._render()
            return
        timer.start()

    def _fit_figure_to_live_canvas(self, figure) -> None:
        canvas = getattr(self, "_canvas", None)
        if figure is None or canvas is None:
            return
        width = int(canvas.width())
        height = int(canvas.height())
        if width <= 0 or height <= 0:
            return
        try:
            device_ratio = float(canvas.devicePixelRatioF() or 1.0)
        except (AttributeError, TypeError, ValueError):
            device_ratio = 1.0
        device_ratio = max(1.0, device_ratio)
        dpi = float(getattr(figure, "dpi", self._dpi) or self._dpi)
        # Qt reports widget dimensions in logical pixels while Matplotlib's
        # Agg buffer is sized in device pixels.  At 150%/200% Windows scale,
        # using the logical dimensions directly leaves the figure at only
        # 2/3 or 1/2 of the canvas and makes the chart appear to shrink when
        # an interaction rebuilds it.
        figure.set_size_inches(
            width * device_ratio / dpi,
            height * device_ratio / dpi,
            forward=False,
        )

    def _render(self, *_):
        if self._fig_generator is None:
            if self._generated_document_mode:
                if self._show_generated_figure_document():
                    figure_changed = getattr(self, "figure_changed", None)
                    if figure_changed is not None:
                        figure_changed.emit()
                    return
            if self._static_file_mode:
                if not self._refresh_static_annotation_canvas_preview():
                    self._show_style_preview_figure()
                mark_dirty = getattr(self, "_mark_editor_dirty", None)
                if callable(mark_dirty):
                    mark_dirty()
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
        if self._grid_on:
            ax.grid(
                True,
                alpha=self._grid_alpha,
                linestyle="--",
                linewidth=0.5,
            )
        else:
            ax.grid(False)
        for spine in ax.spines.values():
            spine.set_linewidth(0.8)

        import matplotlib.pyplot as plt

        old = self._canvas.figure
        self._fit_figure_to_live_canvas(fig)
        self._canvas.figure = fig
        self._figure = fig
        self._connect_canvas_interaction_events()
        self._canvas.draw()
        if old:
            plt.close(old)
        self.figure_changed.emit()
