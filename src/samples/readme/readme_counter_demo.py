from __future__ import annotations
import nuiitivet as nv
import nuiitivet.material as md

import argparse


class MultiCounterApp(nv.ComposableWidget):
    count_a = nv.Observable(0)
    count_b = nv.Observable(0)

    def __init__(self) -> None:
        super().__init__()

        self.total = self.count_a.combine(self.count_b).compute(lambda a, b: a + b)

    def increment_a(self) -> None:
        self.count_a.value += 1

    def increment_b(self) -> None:
        self.count_b.value += 1

    def build(self):
        return nv.Column(
            [
                # Counter A
                nv.Row(
                    [
                        md.Text(self.count_a),
                        md.FilledButton("+", on_click=self.increment_a),
                    ],
                    cross_alignment="center",
                    gap=12,
                ),
                # Counter B
                nv.Row(
                    [
                        md.Text(self.count_b),
                        md.FilledButton("+", on_click=self.increment_b),
                    ],
                    cross_alignment="center",
                    gap=12,
                ),
                # Total - 自動的に更新される！
                md.Text(self.total),
            ],
            gap=16,
            padding=20,
            cross_alignment="center",
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="README MultiCounterApp demo")
    parser.add_argument("--png", type=str, default="", help="Render to PNG instead of opening a window")
    args = parser.parse_args()

    app = md.MaterialApp(content=MultiCounterApp(), title_bar=nv.DefaultTitleBar(title="MultiCounter Demo"))

    if args.png:
        app.render_to_png(args.png)
        print(f"Rendered {args.png}")
    else:
        app.run()
