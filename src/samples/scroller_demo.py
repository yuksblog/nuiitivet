"""Scroller のサンプル: 基本的な使い方"""

from nuiitivet.material.app import MaterialApp
from nuiitivet.layout.column import Column
from nuiitivet.material.card import FilledCard
from nuiitivet.material.styles.card_style import CardStyle
from nuiitivet.layout.row import Row
from nuiitivet.layout.scroller import Scroller
from nuiitivet.scrolling import ScrollController
from nuiitivet.material import Text
from nuiitivet.scrolling import ScrollDirection
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.widgets.scrollbar import ScrollbarBehavior


def main():
    """基本的なスクロール可能なリストを表示"""
    items = []
    for i in range(100):
        items.append(
            FilledCard(
                child=Text(f"Item {i + 1}"),
                padding=12,
                style=CardStyle.filled().copy_with(
                    background=ColorRole.SURFACE_VARIANT if i % 2 == 0 else ColorRole.SURFACE
                ),
            )
        )
    vertical_scroller = Scroller(
        child=Column(items, gap=2),
        padding=8,
        scrollbar=ScrollbarBehavior(auto_hide=True),
        height=600,
    )
    cards = []
    for i in range(1, 21):
        cards.append(
            FilledCard(
                child=Text(f"Card {i:02} — swipe horizontally"),
                padding=(16, 24),
                style=CardStyle.filled().copy_with(
                    background=ColorRole.SURFACE_VARIANT if i % 2 == 0 else ColorRole.SURFACE
                ),
            )
        )
    horizontal_scroller = Scroller(
        child=Row(cards, gap=12),
        direction=ScrollDirection.HORIZONTAL,
        padding=(16, 16, 16, 32),
        scrollbar=ScrollbarBehavior(auto_hide=True),
        width=400,
    )
    root = Row(
        [vertical_scroller, horizontal_scroller],
        padding=16,
        gap=16,
        cross_alignment="center",
    )
    app = MaterialApp(root)
    app.run()


def main_auto_hide():
    """スクロールバー自動非表示のサンプル"""
    items = []
    for i in range(100):
        items.append(
            FilledCard(
                child=Text(f"Item {i + 1}"),
                padding=12,
                style=CardStyle.filled().copy_with(
                    background=ColorRole.SURFACE_VARIANT if i % 2 == 0 else ColorRole.SURFACE
                ),
            )
        )
    scroller = Scroller(
        child=Column(items, gap=2),
        padding=8,
        scrollbar=ScrollbarBehavior(auto_hide=True),
    )
    app = MaterialApp(scroller)
    app.run()


def main_with_controller():
    """ScrollControllerを使った外部制御のサンプル"""
    controller = ScrollController()

    def on_scroll_change(offset):
        if offset > 0:
            print(f"Scrolled to: {offset:.0f}px (max: {controller.max_extent:.0f}px)")

    controller.axis_state(controller.primary_axis).offset.subscribe(on_scroll_change)
    items = [Text(f"Item {i + 1}") for i in range(100)]
    scroller = Scroller(
        child=Column(items, gap=8),
        scroll_controller=controller,
        scrollbar=ScrollbarBehavior(auto_hide=True),
    )
    app = MaterialApp(scroller)
    import threading

    def auto_scroll():
        import time

        time.sleep(3)
        print("Auto scrolling to bottom...")
        controller.scroll_to_end()
        time.sleep(2)
        print("Auto scrolling to top...")
        controller.scroll_to_start()

    threading.Thread(target=auto_scroll, daemon=True).start()
    app.run()


def main_horizontal():
    """横方向スクロールのギャラリーサンプル"""
    cards = []
    for i in range(1, 21):
        cards.append(
            FilledCard(
                child=Text(f"Card {i:02} — swipe horizontally"),
                padding=(16, 24),
                style=CardStyle.filled().copy_with(
                    background=ColorRole.SURFACE_VARIANT if i % 2 == 0 else ColorRole.SURFACE
                ),
            )
        )
    scroller = Scroller(
        child=Row(cards, gap=12),
        direction=ScrollDirection.HORIZONTAL,
        padding=(16, 16, 16, 32),
        scrollbar=ScrollbarBehavior(auto_hide=True),
    )
    app = MaterialApp(scroller)
    app.run()


if __name__ == "__main__":
    main()
