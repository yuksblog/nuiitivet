from __future__ import annotations
import nuiitivet as nv
import nuiitivet.material as md

import argparse


class CounterApp(nv.ComposableWidget):
    count = nv.Observable(0)

    def increment(self) -> None:
        self.count.value += 1

    def build(self):
        return nv.Column(
            [
                md.Text(self.count),
                md.FilledButton(
                    "Increment",
                    on_click=self.increment,
                ),
            ],
            gap=20,
            padding=20,
        )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="README CounterApp sample")
    parser.add_argument("--png", type=str, default="", help="Render to PNG instead of opening a window")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    app = md.MaterialApp(content=CounterApp(), title_bar=nv.DefaultTitleBar(title="Counter Demo"))

    if args.png:
        app.render_to_png(args.png)
        print(f"Rendered {args.png}")
        return

    app.run()


if __name__ == "__main__":
    main()
