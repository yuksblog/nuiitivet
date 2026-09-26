"""
Sheet From an Intent

Shows how to open a side sheet from an intent registered on the window's overlay.
"""

from __future__ import annotations

from dataclasses import dataclass

import nuiitivet.material as nv


@dataclass(frozen=True)
class SettingsIntent:
    title: str


def build_settings_sheet(intent: SettingsIntent) -> nv.Widget:
    return nv.SideSheet(
        nv.Box(
            nv.Column(
                children=[nv.Text("Setting 1"), nv.Text("Setting 2")],
                gap=12,
                cross_alignment="start",
            ),
            padding=24,
        ),
        headline=intent.title,
    )


def build_overlay() -> nv.Overlay:
    return nv.Overlay(intents={SettingsIntent: build_settings_sheet})


class SheetIntentDemo(nv.ComposableWidget):
    def open_settings(self) -> None:
        nv.Overlay.of(self).side_sheet(SettingsIntent(title="Settings"), side="left")

    def build(self) -> nv.Widget:
        return nv.Container(
            alignment="center",
            child=nv.Button("Open Settings", on_click=self.open_settings, style=nv.ButtonStyle.filled()),
        )


def build_root() -> nv.Widget:
    return SheetIntentDemo()


def main() -> None:
    nv.App(nv.Window(content=build_root, overlay=build_overlay, width=640, height=400)).run()


if __name__ == "__main__":
    main()
