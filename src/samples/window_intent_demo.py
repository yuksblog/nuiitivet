"""Demo of intent-based window control."""

from nuiitivet.material import App
from nuiitivet.material.buttons import Button
from nuiitivet.material.text import Text
from nuiitivet.layout.column import Column
from nuiitivet.widgeting.widget import ComposableWidget
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
from nuiitivet.material import ButtonStyle


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
                Button(
                    label="Full Screen",
                    on_click=lambda: App.of(self).dispatch(FullScreenIntent()),
                    style=ButtonStyle.filled()),
                Button(
                    label="Maximize Window",
                    on_click=lambda: App.of(self).dispatch(MaximizeWindowIntent()),
                    style=ButtonStyle.filled()),
                Button(
                    label="Minimize Window",
                    on_click=lambda: App.of(self).dispatch(MinimizeWindowIntent()),
                    style=ButtonStyle.filled()),
                Button(
                    label="Minimize & Restore (1s)",
                    on_click=lambda: self._minimize_and_restore(),
                    style=ButtonStyle.filled()),
                Button(
                    label="Restore Window",
                    on_click=lambda: App.of(self).dispatch(RestoreWindowIntent()),
                    style=ButtonStyle.filled()),
                Button(
                    label="Center Window",
                    on_click=lambda: App.of(self).dispatch(CenterWindowIntent()),
                    style=ButtonStyle.filled()),
                Button(
                    label="Move to (100, 100)",
                    on_click=lambda: App.of(self).dispatch(MoveWindowIntent(x=100, y=100)),
                    style=ButtonStyle.filled()),
                Button(
                    label="Resize to (800, 600)",
                    on_click=lambda: App.of(self).dispatch(ResizeWindowIntent(width=800, height=600)),
                    style=ButtonStyle.filled()),
                Button(
                    label="Close Window",
                    on_click=lambda: App.of(self).dispatch(CloseWindowIntent()),
                    style=ButtonStyle.filled()),
                Button(
                    label="Exit App",
                    on_click=lambda: App.of(self).dispatch(ExitAppIntent()),
                    style=ButtonStyle.filled()),
            ],
            padding=10,
            gap=10,
            cross_alignment="center",
        )


def main():
    app = App(content=WindowDemo())
    app.run()


if __name__ == "__main__":
    main()
