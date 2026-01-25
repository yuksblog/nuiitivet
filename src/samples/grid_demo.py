"""Grid sample demonstrating explicit row/column placement."""

from __future__ import annotations

from nuiitivet.layout.grid import Grid, GridItem
from nuiitivet.material import Text
from nuiitivet.material.app import MaterialApp
from nuiitivet.material.card import FilledCard
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.widgeting.widget import ComposableWidget, Widget


def _card(label: str, width=Sizing.flex(1), height=Sizing.flex(1)) -> FilledCard:
    return FilledCard(
        Text(label),
        padding=12,
        alignment="center",
        width=width,
        height=height,
    )


class GridDemo(ComposableWidget):

    def build(self) -> Widget:
        # Header: 全幅使うので column=[0, 1]
        header = GridItem(_card("Header"), row=0, column=[0, 1])

        # Sidebar: 幅200pxを指定し、列設定"auto"により列幅が200pxになる
        # 高さはメイン+フッター部分を埋めるため row=[1, 2]
        sidebar = GridItem(_card("Sidebar\n(Width Auto)", width=200), row=[1, 2], column=0)

        # Main: width/heightともにflex(1)でセルを埋める
        content = GridItem(_card("Main content"), row=1, column=1)

        # Footer: 高さ100pxを指定し、行設定"auto"により行高が100pxになる
        footer = GridItem(_card("Footer\n(Height Auto)", height=100), row=2, column=1)

        return Grid(
            # 行: [ヘッダー60px, メイン(残り全部), フッター(自動)]
            rows=[60, Sizing.flex(1), "auto"],
            # 列: [サイドバー(自動), メイン(残り全部)]
            columns=["auto", Sizing.flex(1)],
            row_gap=12,
            column_gap=12,
            padding=12,
            children=[header, sidebar, content, footer],
        )


if __name__ == "__main__":
    demo = GridDemo()
    # ドキュメントに合わせて 400x400
    app = MaterialApp(content=demo, width=400, height=400)
    try:
        app.run()
    except Exception:
        try:
            # Generate image for docs
            app.render_to_png("docs/assets/layout_grid_app.png")
            print("Rendered docs/assets/layout_grid_app.png")
        except Exception as e:
            print(f"Failed to run or render: {e}")
