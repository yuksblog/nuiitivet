"""The same app on the desktop and in a browser.

Run on the desktop:   python app.py
Run in a browser:     python -m nuiitivet.web run app.py
"""

import nuiitivet.material as nv


class Counter(nv.ComposableWidget):
    count = nv.Observable(0)

    def build(self) -> nv.Widget:
        return nv.Box(
            padding=24,
            child=nv.Column(
                gap=12,
                children=[
                    nv.Text(self.count.map(lambda n: f"Clicked {n} times")),
                    nv.Button("Click", on_click=self.clicked, style=nv.ButtonStyle.filled()),
                ],
            ),
        )

    def clicked(self) -> None:
        self.count.value += 1


def main() -> None:
    nv.App(nv.Window(content=Counter, title="Hello", width=320, height=200)).run()


if __name__ == "__main__":
    main()
