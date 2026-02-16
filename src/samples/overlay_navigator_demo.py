"""Overlay + Navigator Demo.

This demo combines:
- Navigator (push/pop + fade)
- Overlay (snackbar + dialog)

Run:
    uv run python -c "import sitecustomize; import samples.overlay_navigator_demo as m; m.main()"
"""

from __future__ import annotations

from dataclasses import dataclass

from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.modifiers import background
from nuiitivet.navigation import Navigator, PageRoute
from nuiitivet.material.dialogs import AlertDialog
from nuiitivet.material.app import MaterialApp
from nuiitivet.material.overlay import MaterialOverlay
from nuiitivet.material.buttons import FilledButton, TextButton
from nuiitivet.material.styles.button_style import ButtonStyle
from nuiitivet.material import Text, MaterialTransitions, FadeIn, ScaleIn, SlideOutVertically
from nuiitivet.widgeting.widget import ComposableWidget, Widget


@dataclass(frozen=True, slots=True)
class DetailsIntent:
    pass


@dataclass(frozen=True, slots=True)
class SettingsIntent:
    pass


@dataclass(frozen=True, slots=True)
class HelloDialogIntent:
    pass


@dataclass(frozen=True, slots=True)
class ConfirmResetDialogIntent:
    pass


@dataclass(frozen=True, slots=True)
class HomeIntent:
    pass


def _filled(label: str, *, on_click) -> FilledButton:
    return FilledButton(
        label,
        on_click=on_click,
        style=ButtonStyle(background="#6750A4", foreground="#FFFFFF"),
    )


class HomePage(ComposableWidget):
    def build(self) -> Widget:
        async def open_dialog() -> None:
            # Demonstrate custom transition: ScaleIn + FadeIn -> FadeOut + SlideDown
            transition = MaterialTransitions.dialog(
                enter=FadeIn() | ScaleIn(initial_scale=0.5),
                exit=SlideOutVertically(target_offset_y=50, duration=0.4),
            )
            result = await MaterialOverlay.root().dialog(HelloDialogIntent(), transition=transition)
            if result.value == "OK":
                MaterialOverlay.root().snackbar("Dialog confirmed (OK)")
            else:
                MaterialOverlay.root().snackbar("Dialog dismissed")

        def go_next() -> None:
            Navigator.of(self).push(DetailsIntent())

        return Container(
            padding=24,
            child=Column(
                gap=16,
                cross_alignment="start",
                children=[
                    Text("Overlay + Navigator Demo"),
                    Text("Home page"),
                    _filled("Show dialog (Overlay)", on_click=open_dialog),
                    _filled("Go to details (Navigator)", on_click=go_next),
                ],
            ),
        ).modifier(background("#E8F5E9"))


class DetailsPage(ComposableWidget):
    def build(self) -> Widget:
        def go_back() -> None:
            Navigator.of(self).pop()

        def show_snackbar() -> None:
            MaterialOverlay.root().snackbar("Snackbar from Details")

        def go_settings() -> None:
            Navigator.of(self).push(SettingsIntent())

        return Container(
            padding=24,
            child=Column(
                gap=16,
                cross_alignment="start",
                children=[
                    Text("Details page"),
                    TextButton("Back", on_click=go_back),
                    _filled("Show snackbar", on_click=show_snackbar),
                    _filled("Go to settings", on_click=go_settings),
                ],
            ),
        ).modifier(background("#E3F2FD"))


class SettingsPage(ComposableWidget):
    def build(self) -> Widget:
        def pop_to_details() -> None:
            Navigator.of(self).pop()

        async def confirm_reset() -> None:
            result = await MaterialOverlay.root().dialog(ConfirmResetDialogIntent())
            if result.value is True:
                MaterialOverlay.root().snackbar("Reset done")
            else:
                MaterialOverlay.root().snackbar("Cancelled")

        return Container(
            padding=24,
            child=Column(
                gap=16,
                cross_alignment="start",
                children=[
                    Text("Settings page"),
                    TextButton("Back", on_click=pop_to_details),
                    _filled("Confirm reset (Overlay)", on_click=confirm_reset),
                ],
            ),
        ).modifier(background("#FFF3E0"))


def main() -> None:
    def _build_hello_dialog(_intent: HelloDialogIntent) -> Widget:
        dialog: Widget

        def on_ok() -> None:
            MaterialOverlay.root().close("OK", target=dialog)

        dialog = AlertDialog(
            title="Hello",
            message="This dialog is rendered via Overlay (Intent).",
            actions=[_filled("OK", on_click=on_ok)],
        )
        return dialog

    def _build_confirm_reset_dialog(_intent: ConfirmResetDialogIntent) -> Widget:
        dialog: Widget

        def on_cancel() -> None:
            MaterialOverlay.root().close(False, target=dialog)

        def on_reset() -> None:
            MaterialOverlay.root().close(True, target=dialog)

        dialog = AlertDialog(
            title="Confirm",
            message="Reset settings?",
            actions=[
                TextButton("Cancel", on_click=on_cancel),
                _filled("Reset", on_click=on_reset),
            ],
        )
        return dialog

    MaterialApp.navigation(
        routes={
            HomeIntent: lambda _i: PageRoute(builder=HomePage),
            DetailsIntent: lambda _i: PageRoute(builder=DetailsPage),
            SettingsIntent: lambda _i: PageRoute(builder=SettingsPage),
        },
        initial_route=HomeIntent(),
        overlay_routes={
            HelloDialogIntent: _build_hello_dialog,
            ConfirmResetDialogIntent: _build_confirm_reset_dialog,
        },
        width=520,
        height=420,
    ).run()


if __name__ == "__main__":
    main()
