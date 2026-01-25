"""will_pop demo.

Shows how to intercept Esc/back navigation on an edit screen.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import logging
from typing import Optional

from nuiitivet.common.logging_once import exception_once
from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.layout.row import Row
from nuiitivet.modifiers import will_pop
from nuiitivet.navigation import Navigator, PageRoute
from nuiitivet.observable import Observable
from nuiitivet.material.dialogs import AlertDialog
from nuiitivet.material.app import MaterialApp
from nuiitivet.material.overlay import MaterialOverlay
from nuiitivet.material.buttons import FilledButton, TextButton
from nuiitivet.material import Text
from nuiitivet.material.text_fields import OutlinedTextField
from nuiitivet.widgeting.widget import ComposableWidget, Widget


_logger = logging.getLogger(__name__)


class EditViewModel:
    text: Observable[str] = Observable("Hello")
    dirty: Observable[bool] = Observable(False)


@dataclass(frozen=True, slots=True)
class HomeIntent:
    pass


class HomeScreen(ComposableWidget):
    def build(self) -> Widget:
        def _open_editor() -> None:
            Navigator.root().push(PageRoute(builder=lambda: EditScreen()))

        return Container(
            padding=32,
            child=Column(
                children=[
                    Text("will_pop Demo"),
                    Text("Open the editor, type something, then press Esc."),
                    FilledButton("Open editor", on_click=_open_editor),
                ],
                gap=16,
                cross_alignment="start",
            ),
        )


class EditScreen(ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self.vm = EditViewModel()
        self._initial_text = str(self.vm.text.value)
        self._confirm_open: bool = False
        self._sub_disposable: Optional[object] = None

    def on_mount(self) -> None:
        super().on_mount()

        def _on_text_change(value: str) -> None:
            self.vm.dirty.value = bool(value != self._initial_text)

        try:
            self._sub_disposable = self.vm.text.subscribe(_on_text_change)
        except Exception:
            exception_once(_logger, "will_pop_demo_subscribe_exc", "Text subscription raised")
            self._sub_disposable = None

    def on_unmount(self) -> None:
        disp = self._sub_disposable
        self._sub_disposable = None
        if disp is None:
            super().on_unmount()
            return
        dispose = getattr(disp, "dispose", None)
        if callable(dispose):
            try:
                dispose()
            except Exception:
                exception_once(_logger, "will_pop_demo_dispose_exc", "Disposable.dispose raised")

        super().on_unmount()

    def _save(self) -> None:
        self._initial_text = str(self.vm.text.value)
        self.vm.dirty.value = False
        MaterialOverlay.root().snackbar("Saved")

    def _try_pop(self) -> None:
        Navigator.root().pop()

    def _on_will_pop(self) -> bool:
        if not bool(self.vm.dirty.value):
            return True

        if self._confirm_open:
            return False

        self._confirm_open = True

        def _cancel() -> None:
            self._confirm_open = False
            MaterialOverlay.root().close(None)

        def _discard() -> None:
            self._confirm_open = False
            self.vm.dirty.value = False
            MaterialOverlay.root().close(None)
            Navigator.root().pop()

        handle = MaterialOverlay.root().dialog(
            AlertDialog(
                title=Text("Discard changes?"),
                content=Text("You have unsaved changes."),
                actions=[
                    TextButton("Cancel", on_click=_cancel),
                    FilledButton("Discard", on_click=_discard),
                ],
            ),
            dismiss_on_outside_tap=False,
        )

        async def _watch_dismiss() -> None:
            try:
                await handle
            finally:
                self._confirm_open = False

        try:
            asyncio.create_task(_watch_dismiss())
        except Exception:
            self._confirm_open = False

        return False

    def build(self) -> Widget:
        content = Container(
            padding=24,
            child=Column(
                children=[
                    Text("Editor"),
                    Text(self.vm.dirty.map(lambda v: "Dirty" if v else "Clean")),
                    OutlinedTextField.two_way(
                        self.vm.text,
                        width=420,
                        height=52,
                        padding=10,
                    ),
                    Row(
                        children=[
                            TextButton("Back", on_click=self._try_pop),
                            FilledButton("Save", on_click=self._save),
                        ],
                        gap=12,
                    ),
                    Text("Tip: Press Esc to go back."),
                ],
                gap=16,
                cross_alignment="start",
            ),
        )
        return content.modifier(will_pop(on_will_pop=self._on_will_pop))


def main() -> None:
    MaterialApp.navigation(
        routes={
            HomeIntent: lambda _i: PageRoute(builder=HomeScreen),
        },
        initial_route=HomeIntent(),
        width=720,
        height=420,
    ).run()


if __name__ == "__main__":
    main()
