import nuiitivet
from nuiitivet.material.app import MaterialApp
from nuiitivet.material.text import Text
from nuiitivet.material.styles.text_style import TextStyle
from nuiitivet.layout.column import Column
import nuiitivet as nv


def main():
    # Set default font family globally (This API is now available at top-level)
    nuiitivet.set_default_font_family("Hiragino Sans")

    # Text with default font fallback (should work if system has Japanese fonts)
    text1 = Text("こんにちは、世界！ (Default Fallback)", style=TextStyle(font_size=24))

    # Text with explicit font family (if installed)
    text2 = Text("日本語フォント指定 (Hiragino Sans)", style=TextStyle(font_size=24, font_family="Hiragino Sans"))

    column = Column(
        children=[text1, text2],
        gap=20,
        padding=20,
        cross_alignment="center",
    )

    # Use MaterialApp which sets up the proper theme and window
    app = MaterialApp(
        content=column,
        width=600,
        height=400,
        title_bar=nv.DefaultTitleBar(title="Japanese Text Demo"),
    )

    app.run()


if __name__ == "__main__":
    main()
