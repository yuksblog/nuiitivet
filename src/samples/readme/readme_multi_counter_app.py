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
                nv.Row(
                    [
                        md.Text(self.count_a),
                        md.FilledButton("+", on_click=self.increment_a),
                    ],
                    gap=12,
                ),
                nv.Row(
                    [
                        md.Text(self.count_b),
                        md.FilledButton("+", on_click=self.increment_b),
                    ],
                    gap=12,
                ),
                md.Text(self.total),
            ],
            gap=16,
            padding=20,
        )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="README MultiCounterApp sample")
    parser.add_argument("--png", type=str, default="", help="Render to PNG instead of opening a window")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    app = md.MaterialApp(content=MultiCounterApp())

    if args.png:
        app.render_to_png(args.png)
        print(f"Rendered {args.png}")
        return

    app.run()


if __name__ == "__main__":
    main()
