"""Long-lived plot state coordinator and scene diff propagation."""

from __future__ import annotations

from types import MappingProxyType
from dataclasses import dataclass
from typing import Mapping

from .commands import CommandResult, CommandStack, PlotState
from .layout import LayoutResolver
from .scene import RenderScene, SceneDiagnostic, SceneDiff


@dataclass(frozen=True)
class SceneUpdate:
    ok: bool
    state: PlotState
    scene: RenderScene
    diff: SceneDiff
    diagnostics: tuple[SceneDiagnostic, ...] = ()
    command_result: CommandResult | None = None


class FigureSession:
    def __init__(self, state: PlotState, resolver: LayoutResolver):
        self._commands = CommandStack(state)
        self._resolver = resolver
        dependency_index: dict[str, set[str]] = {}
        for binding in state.document.bindings:
            for reference in binding.columns:
                dependency_index.setdefault(reference.column_id, set()).add(binding.object_id)
        self._dependency_index = MappingProxyType(
            {
                column_id: tuple(sorted(object_ids))
                for column_id, object_ids in dependency_index.items()
            }
        )
        result = resolver.resolve(state.document, state.worksheet.current)
        if not result.ok or result.scene is None:
            raise ValueError(f"cannot initialize figure session: {result.diagnostics}")
        self._scene = result.scene

    @property
    def state(self) -> PlotState:
        return self._commands.current

    @property
    def scene(self) -> RenderScene:
        return self._scene

    @property
    def dependency_index(self) -> Mapping[str, tuple[str, ...]]:
        """Return the immutable worksheet-column to graph-object index."""

        return self._dependency_index

    def execute(self, command) -> SceneUpdate:
        result = self._commands.prepare(command)
        resolution = self._resolver.resolve_incremental(
            result.state.document,
            result.state.worksheet.current,
            self._scene,
            result.affected_object_ids,
            data_changed=bool(result.affected_data_ids),
        )
        if not resolution.ok or resolution.scene is None:
            return SceneUpdate(
                ok=False,
                state=self.state,
                scene=self._scene,
                diff=SceneDiff.empty(),
                diagnostics=resolution.diagnostics,
            )
        diff = SceneDiff.between(self._scene, resolution.scene)
        self._commands.commit(command, result)
        self._scene = resolution.scene
        return SceneUpdate(
            ok=True,
            state=self.state,
            scene=self._scene,
            diff=diff,
            command_result=result,
        )

    def undo(self) -> SceneUpdate:
        self._commands.undo()
        return self._refresh_after_history_change()

    def redo(self) -> SceneUpdate:
        self._commands.redo()
        return self._refresh_after_history_change()

    def _refresh_after_history_change(self) -> SceneUpdate:
        resolution = self._resolver.resolve(
            self.state.document,
            self.state.worksheet.current,
        )
        if not resolution.ok or resolution.scene is None:
            return SceneUpdate(False, self.state, self._scene, SceneDiff.empty(), resolution.diagnostics)
        diff = SceneDiff.between(self._scene, resolution.scene)
        self._scene = resolution.scene
        return SceneUpdate(True, self.state, self._scene, diff)
