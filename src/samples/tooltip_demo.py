"""Tooltip demo for Material Tooltip/RichTooltip and tooltip() modifier.

Issue #82 verification guide
------------------------------
4) Coexistence with existing handler
   - "Click me + tooltip" ボタンをクリックすると "click count: N" が更新されること
   - ツールチップも通常通り表示されること (on_press が上書きされていない)

5) Listener cleanup on unmount/remount
   - "Toggle tooltip" ボタンで tooltip() の付け外しを繰り返す
   - ホバーで開く回数が 1 回だけ (N 回繰り返しても重複しない)
   - アンマウント後はツールチップが表示されないこと
"""

from __future__ import annotations

from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.material import RichTooltip, Text, Tooltip
from nuiitivet.material import App
from nuiitivet.material.buttons import IconButton, Button
from nuiitivet.material.styles.text_style import TextStyle
from nuiitivet.modifiers import tooltip
from nuiitivet.observable import Observable
from nuiitivet.widgets.box import Box
from nuiitivet.widgeting.widget import ComposableWidget, Widget
from nuiitivet.material import ButtonStyle


class TooltipDemo(ComposableWidget):
    """Demo screen for tooltip widgets and tooltip modifier behavior."""

    last_action: Observable[str] = Observable("none")
    # Issue #82 – section 4
    click_count: Observable[int] = Observable(0)

    def _set_action(self, action_name: str) -> None:
        self.last_action.value = action_name

    def _on_click_coexist(self) -> None:
        self.click_count.value += 1

    def build(self) -> Widget:
        plain_targets = Row(
            children=[
                IconButton("home").modifier(tooltip(Tooltip("Home"))),
                IconButton("favorite").modifier(tooltip(Tooltip("Favorite"))),
                IconButton("settings").modifier(tooltip(Tooltip("Settings"))),
            ],
            gap=12,
            cross_alignment="center",
        )

        rich_content = RichTooltip(
            "You can pin this item for quick access.",
            subhead="Pin to top",
            action_label="Pin",
            on_action_click=lambda: self._set_action("pin"),
            action_label_2="Dismiss",
            on_action_click_2=lambda: self._set_action("dismiss"),
        )

        rich_target = Button("Hover me", style=ButtonStyle.filled()).modifier(
            tooltip(
                rich_content,
                delay=0.2,
                dismiss_delay=1.2,
                alignment="top-center",
                anchor="bottom-center",
                offset=(0.0, -8.0),
            )
        )

        custom_target = Button("Bottom-right tooltip", style=ButtonStyle.outlined()).modifier(
            tooltip(
                Tooltip("Custom placement", style=TooltipStyleCustom.bottom_hint()),
                delay=0.0,
                dismiss_delay=0.5,
                alignment="bottom-right",
                anchor="top-right",
                offset=(0.0, 6.0),
            )
        )

        # --- Issue #82 – Section 4: coexistence with on_click ---
        coexist_btn = Button(
            "Click me + tooltip",
            style=ButtonStyle.filled(),
            on_click=self._on_click_coexist,
        ).modifier(tooltip(Tooltip("Tooltip coexists with on_click"), delay=0.0))

        return Box(
            child=Column(
                children=[
                    Text("Tooltip Demo", style=TextStyle(font_size=24)),
                    Text("1) Plain tooltip on icon buttons"),
                    plain_targets,
                    Text("2) Rich tooltip with action callbacks"),
                    rich_target,
                    Text(self.last_action.map(lambda value: f"Last rich action: {value}")),
                    Text("3) Custom timing and placement"),
                    custom_target,
                    Text("Desktop: hover/focus to open. Touch: long-press to open."),
                    Text("─" * 40),
                    Text("4) [Issue #82] Coexistence with existing on_click handler"),
                    Text("   → Click the button and confirm the count increments"),
                    coexist_btn,
                    Text(self.click_count.map(lambda n: f"   click count: {n}")),
                ],
                gap=12,
                cross_alignment="start",
            ),
            padding=24,
            background_color=(245, 247, 250, 255),
        )


class TooltipStyleCustom:
    """Small helper style factory used only in this demo."""

    @staticmethod
    def bottom_hint():
        from nuiitivet.material.styles.tooltip_style import TooltipStyle

        return TooltipStyle.standard().copy_with(corner_radius=8)


if __name__ == "__main__":
    app = App(content=TooltipDemo(), width=760, height=700)
    app.run()
