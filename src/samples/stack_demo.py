from nuiitivet.material.app import MaterialApp
from nuiitivet.layout.stack import Stack
from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.material import Text
from nuiitivet.modifiers import background, border


def ColoredBox(text, color, w=50, h=50):
    return Container(width=w, height=h, child=Text(text), alignment="center").modifier(
        background(color) | border("black", 1)
    )


def main():
    # 1. Basic Stack (Default alignment: top-left)
    # 単純な重ね合わせ。後から追加したものが上に描画される。
    basic_stack = Stack(
        children=[
            ColoredBox("1", "#FFCDD2", 100, 100),
            ColoredBox("2", "#C8E6C9", 80, 80),
            ColoredBox("3", "#BBDEFB", 60, 60),
        ]
    )

    # 2. Alignment Demo (Smart Children Pattern)
    # Stack 自体は単純に重ねるだけ。
    # 子要素を Container(width="100%", height="100%") で包み、
    # Container の alignment プロパティを使って配置を制御する。
    alignment_stack = Stack(
        width=300,
        height=200,
        children=[
            # 背景 (全体)
            Container(width="100%", height="100%").modifier(background("#EEEEEE")),
            # Top-Left
            Container(width="100%", height="100%", alignment="top-left", child=ColoredBox("TL", "#FF8A80")),
            # Center
            Container(width="100%", height="100%", alignment="center", child=ColoredBox("C", "#B9F6CA")),
            # Bottom-Right
            Container(width="100%", height="100%", alignment="bottom-right", child=ColoredBox("BR", "#82B1FF")),
        ],
    )

    # 3. Background Expansion
    # 背景画像を模したコンテナと、手前のコンテンツ
    # Stack の alignment を使って、手前のコンテンツを中央に配置するパターン
    bg_stack = Stack(
        width=300,
        height=150,
        alignment="center",  # デフォルトのアライメントを指定
        children=[
            # 背景: 親サイズに追従
            Container(width="100%", height="100%").modifier(background("#E0F7FA")),
            # コンテンツ: 自身のサイズを持ち、Stack の alignment に従う
            Container(child=Text("Centered Content"), padding=20).modifier(background("white") | border("blue", 2)),
        ],
    )

    root = Column(
        padding=20,
        gap=20,
        children=[
            Text("1. Basic Stack (Overlap)"),
            basic_stack,
            Text("2. Alignment (Smart Children Pattern)"),
            alignment_stack,
            Text("3. Background Expansion"),
            bg_stack,
        ],
    )

    app = MaterialApp(root)
    app.run()


if __name__ == "__main__":
    main()
