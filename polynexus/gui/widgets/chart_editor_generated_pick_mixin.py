from __future__ import annotations


class ChartEditorGeneratedPickMixin:
    def _on_generated_pick_event(self, event):
        if self._generated_handle_drag_state:
            return
        if not self._generated_document_mode:
            return
        self._remember_generated_pointer_event(event)
        gui_event_id = self._generated_gui_event_id(event)
        if gui_event_id is not None:
            self._last_generated_pick_gui_event_id = gui_event_id
        candidate_ids = self._figure_render_adapter.object_ids_for_pick_event(event)
        if not candidate_ids:
            object_id = self._figure_render_adapter.object_id_for_pick_event(event)
            if object_id:
                self._clear_selected_generated_line_handle_context()
                self._clear_selected_generated_plot_series_handle_context()
                self._selection_cycle_hint_active = False
                self._select_generated_object(object_id, "canvas")
            return
        self._clear_selected_generated_line_handle_context()
        self._clear_selected_generated_plot_series_handle_context()
        self._select_generated_object_from_candidates(
            candidate_ids,
            getattr(event, "mouseevent", None),
        )

    def _generated_pick_signature(self, event, candidate_ids):
        mouseevent = getattr(event, "mouseevent", event)
        if mouseevent is None:
            return tuple(candidate_ids)
        return (
            round(float(getattr(mouseevent, "x", 0.0) or 0.0), 1),
            round(float(getattr(mouseevent, "y", 0.0) or 0.0), 1),
            tuple(candidate_ids),
        )

    def _select_generated_object_from_candidates(self, candidate_ids, mouseevent):
        candidate_ids = [
            str(candidate_id or "")
            for candidate_id in list(candidate_ids or [])
            if str(candidate_id or "")
        ]
        if not candidate_ids:
            return ""
        pick_signature = self._generated_pick_signature(mouseevent, candidate_ids)
        if (
            pick_signature == self._last_generated_pick_signature
            and candidate_ids == self._last_generated_pick_candidates
            and self._selected_figure_object_id in candidate_ids
        ):
            current_index = candidate_ids.index(self._selected_figure_object_id)
            object_id = candidate_ids[(current_index + 1) % len(candidate_ids)]
        else:
            object_id = candidate_ids[0]
        self._last_generated_pick_signature = pick_signature
        self._last_generated_pick_candidates = list(candidate_ids)
        overlap_cycle_hint_active = len(candidate_ids) > 1
        previous_object_id = str(self._selected_figure_object_id or "")
        previous_cycle_hint_active = bool(self._selection_cycle_hint_active)
        self._selection_cycle_hint_active = overlap_cycle_hint_active
        self._select_generated_object(object_id, "canvas")
        if (
            object_id == previous_object_id
            and previous_cycle_hint_active != overlap_cycle_hint_active
        ):
            figure_object = self._generated_figure_object_by_id(object_id)
            if figure_object:
                self._set_generated_selection_status(figure_object)
        return object_id

    def _generated_object_uses_select_only_press(self, object_id):
        figure_object = self._generated_figure_object_by_id(object_id)
        if not figure_object:
            return False
        object_type = str(figure_object.get("type", "") or "")
        if object_type == "highlight":
            return True
        if object_type != "plot_series":
            return False
        chart_kind = str(figure_object.get("chart_kind", "") or "")
        return chart_kind in {"heatmap", "bar", "barh", "image_grid"}

    def _generated_gui_event_id(self, event):
        mouseevent = getattr(event, "mouseevent", event)
        gui_event = getattr(mouseevent, "guiEvent", None)
        if gui_event is None:
            return None
        return id(gui_event)

    def _cycle_generated_selection_after_click(self, drag_state):
        if not isinstance(drag_state, dict) or drag_state.get("dirty"):
            return False
        object_id = str(drag_state.get("object_id", "") or "")
        selected_before_press = str(drag_state.get("selected_before_press", "") or "")
        candidate_ids = [
            str(candidate_id or "")
            for candidate_id in list(drag_state.get("overlap_candidate_ids", []) or [])
            if str(candidate_id or "")
        ]
        if len(candidate_ids) < 2 or not object_id or selected_before_press != object_id:
            return False
        if object_id not in candidate_ids:
            return False
        current_object_id = str(self._selected_figure_object_id or "") or object_id
        if current_object_id not in candidate_ids:
            current_object_id = object_id
        current_index = candidate_ids.index(current_object_id)
        next_object_id = candidate_ids[(current_index + 1) % len(candidate_ids)]
        if not next_object_id or next_object_id == current_object_id:
            return False
        self._selection_cycle_hint_active = True
        self._select_generated_object(next_object_id, "canvas")
        return True
