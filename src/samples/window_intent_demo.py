"""Demo of intent-based window control."""

from nuiitivet.material.app import MaterialApp
from nuiitivet.material.buttons import FilledButton
from nuiitivet.material.text import Text
from nuiitivet.layout.column import Column
from nuiitivet.widgeting.widget import ComposableWidget
from nuiitivet.runtime.app import App
from nuiitivet.observable import runtime
from nuiitivet.runtime.intents import (
    ExitAppIntent,
    CenterWindowIntent,
    MaximizeWindowIntent,
    MinimizeWindowIntent,
    RestoreWindowIntent,
    FullScreenIntent,
    CloseWindowIntent,
    MoveWindowIntent,
    ResizeWindowIntent,
)


class WindowDemo(ComposableWidget):
    def _minimize_and_restore(self):
        app = App.of(self)
        app.dispatch(MinimizeWindowIntent())

        def restore(_dt):
            app.dispatch(RestoreWindowIntent())

        runtime.clock.schedule_once(restore, 1.0)

    def build(self):
        return Column(
            children=[
                Text("Window Control Demo"),
                FilledButton(
                    label="Full Screen",
                    on_click=lambda: App.of(self).dispatch(FullScreenIntent()),
                ),
                FilledButton(
                    label="Maximize Window",
                    on_click=lambda: App.of(self).dispatch(MaximizeWindowIntent()),
                ),
                FilledButton(
                    label="Minimize Window",
                    on_click=lambda: App.of(self).dispatch(MinimizeWindowIntent()),
                ),
                FilledButton(
                    label="Minimize & Restore (1s)",
                    on_click=lambda: self._minimize_and_restore(),
                ),
                FilledButton(
                    label="Restore Window",
                    on_click=lambda: App.of(self).dispatch(RestoreWindowIntent()),
                ),
                FilledButton(
                    label="Center Window",
                    on_click=lambda: App.of(self).dispatch(CenterWindowIntent()),
                ),
                FilledButton(
                    label="Move to (100, 100)",
                    on_click=lambda: App.of(self).dispatch(MoveWindowIntent(x=100, y=100)),
                ),
                FilledButton(
                    label="Resize to (800, 600)",
                    on_click=lambda: App.of(self).dispatch(ResizeWindowIntent(width=800, height=600)),
                ),
                FilledButton(
                    label="Close Window",
                    on_click=lambda: App.of(self).dispatch(CloseWindowIntent()),
                ),
                FilledButton(
                    label="Exit App",
                    on_click=lambda: App.of(self).dispatch(ExitAppIntent()),
                ),
            ],
            padding=10,
            gap=10,
            cross_alignment="center",
        )


def main():
    app = MaterialApp(content=WindowDemo())
    app.run()


if __name__ == "__main__":
    main()
