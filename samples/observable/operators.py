"""Observable: Operators

Demonstrates:
- .map() for 1:1 transformations
- .combine(other).compute(fn) for two Observables
- combine(a, b, ...).compute(fn) for three or more Observables
- Observable.compute(fn) for complex / conditional dependency graphs
"""

from nuiitivet.observable import Observable, combine
from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.material import App, Text, ButtonStyle
from nuiitivet.material.buttons import Button
from nuiitivet.widgeting.widget import ComposableWidget, Widget
from nuiitivet.widgets.box import Box


class PriceModel:
    """Reactive price model showcasing all operator forms."""

    def __init__(self) -> None:
        self.price = Observable(100)
        self.quantity = Observable(2)
        self.discount = Observable(0.1)

        # .map() — 1:1 transformation
        self.is_bulk = self.quantity.map(lambda q: q >= 5)

        # .combine(other).compute(fn) — exactly two sources
        self.subtotal = self.price.combine(self.quantity).compute(lambda p, q: p * q)

        # combine(a, b, ...).compute(fn) — three sources
        self.total = combine(self.price, self.quantity, self.discount).compute(lambda p, q, d: int(p * q * (1 - d)))

        # Observable.compute(fn) — conditional / dynamic dependencies
        self.display = Observable.compute(
            lambda: (
                f"¥{self.total.value:,} (bulk discount applied)" if self.is_bulk.value else f"¥{self.total.value:,}"
            )
        )


class OperatorsApp(ComposableWidget):
    """Interactive demo for all operator types."""

    def __init__(self) -> None:
        super().__init__()
        self.model = PriceModel()

    def build(self) -> Widget:
        m = self.model
        return Box(
            padding=24,
            child=Column(
                gap=16,
                children=[
                    Text("Observable: Operators"),
                    Text(m.price.map(lambda p: f"Unit price : ¥{p:,}")),
                    Text(m.quantity.map(lambda q: f"Quantity   : {q}")),
                    Text(m.discount.map(lambda d: f"Discount   : {int(d * 100)}%")),
                    Text(m.subtotal.map(lambda s: f"Subtotal   : ¥{s:,}")),
                    Text(m.display),
                    Text(m.is_bulk.map(lambda b: "Bulk order: YES" if b else "Bulk order: NO")),
                    Row(
                        gap=12,
                        children=[
                            Button(
                                "Price +10",
                                on_click=lambda: setattr(m.price, "value", m.price.value + 10),
                                style=ButtonStyle.filled(),
                            ),
                            Button(
                                "Qty +1",
                                on_click=lambda: setattr(m.quantity, "value", m.quantity.value + 1),
                                style=ButtonStyle.filled(),
                            ),
                        ],
                    ),
                    Row(
                        gap=12,
                        children=[
                            Button(
                                "Discount 0%",
                                on_click=lambda: setattr(m.discount, "value", 0.0),
                                style=ButtonStyle.outlined(),
                            ),
                            Button(
                                "Discount 10%",
                                on_click=lambda: setattr(m.discount, "value", 0.1),
                                style=ButtonStyle.outlined(),
                            ),
                            Button(
                                "Discount 20%",
                                on_click=lambda: setattr(m.discount, "value", 0.2),
                                style=ButtonStyle.outlined(),
                            ),
                        ],
                    ),
                ],
            ),
        )


if __name__ == "__main__":
    widget = OperatorsApp()
    app = App(content=widget)
    try:
        app.run()
    except Exception:
        print("Operators demo requires pyglet/skia to run.")
