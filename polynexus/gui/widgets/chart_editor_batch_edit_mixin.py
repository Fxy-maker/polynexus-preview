"""Batch object actions routed through the canonical edit session."""

from __future__ import annotations

from ...core.figure_edit_commands import (
    AlignObjectsCommand,
    DistributeObjectsCommand,
    GroupObjectsCommand,
    UngroupObjectsCommand,
)


class ChartEditorBatchEditMixin:
    def _sync_batch_action_buttons(self) -> None:
        enabled = len(self._selected_batch_object_ids()) >= 2
        for name in (
            "_btn_annotation_align_left",
            "_btn_annotation_align_center",
            "_btn_annotation_align_right",
            "_btn_annotation_align_top",
            "_btn_annotation_align_middle",
            "_btn_annotation_align_bottom",
            "_btn_annotation_distribute_horizontal",
            "_btn_annotation_distribute_vertical",
            "_btn_annotation_group",
            "_btn_annotation_ungroup",
        ):
            button = getattr(self, name, None)
            if button is not None:
                button.setEnabled(enabled)

    def _selected_batch_object_ids(self) -> tuple[str, ...]:
        selected = tuple(
            str(value or "").strip()
            for value in getattr(self, "_selected_figure_object_ids", ())
            if str(value or "").strip()
        )
        if len(selected) >= 2:
            return selected
        object_id = str(getattr(self, "_selected_figure_object_id", "") or "").strip()
        return (object_id,) if object_id else ()

    def _batch_result_changed(self, result) -> bool:
        changed = bool(getattr(result, "changed", False))
        if changed:
            refresh = getattr(self, "_refresh_object_list", None)
            if callable(refresh):
                refresh(str(getattr(self, "_selected_figure_object_id", "") or ""))
        return changed

    def _align_selected_objects(self, mode: str) -> bool:
        object_ids = self._selected_batch_object_ids()
        if len(object_ids) < 2:
            return False
        result = self._execute_edit(AlignObjectsCommand(object_ids, mode))
        return self._batch_result_changed(result)

    def _group_selected_objects(self) -> bool:
        object_ids = self._selected_batch_object_ids()
        if len(object_ids) < 2:
            return False
        result = self._execute_edit(GroupObjectsCommand(object_ids))
        return self._batch_result_changed(result)

    def _distribute_selected_objects(self, mode: str) -> bool:
        object_ids = self._selected_batch_object_ids()
        if len(object_ids) < 3:
            return False
        result = self._execute_edit(DistributeObjectsCommand(object_ids, mode))
        return self._batch_result_changed(result)

    def _ungroup_selected_objects(self) -> bool:
        object_ids = self._selected_batch_object_ids()
        if len(object_ids) < 2:
            return False
        result = self._execute_edit(UngroupObjectsCommand(object_ids))
        return self._batch_result_changed(result)


__all__ = ["ChartEditorBatchEditMixin"]
