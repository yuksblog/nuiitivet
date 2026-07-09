"""Observable: Operators

Demonstrates:
- .map() for 1:1 transformations
- .combine(other).compute(fn) for two Observables
- combine(a, b, ...).compute(fn) for three or more Observables
- Observable.compute(fn) for complex / conditional dependency graphs
"""

import nuiitivet.material as nv


class PriceModel:
    """Reactive price model showcasing all operator forms."""

    def __init__(self) -> None:
        self.price = nv.Observable(100)
        self.quantity = nv.Observable(2)
        self.discount = nv.Observable(0.1)

        # .map() — 1:1 transformation
        self.is_bulk = self.quantity.map(lambda q: q >= 5)

        # .combine(other).compute(fn) — exactly two sources
        self.subtotal = self.price.combine(self.quantity).compute(lambda p, q: p * q)

        # combine(a, b, ...).compute(fn) — three sources
        self.total = nv.combine(self.price, self.quantity, self.discount).compute(lambda p, q, d: int(p * q * (1 - d)))

        # Observable.compute(fn) — conditional / dynamic dependencies
        self.display = nv.Observable.compute(
            lambda: (
                f"¥{self.total.value:,} (bulk discount applied)" if self.is_bulk.value else f"¥{self.total.value:,}"
            )
        )


class OperatorsApp(nv.ComposableWidget):
    """Interactive demo for all operator types."""

    def __init__(self) -> None:
        super().__init__()
        self.model = PriceModel()

    def build(self) -> nv.Widget:
        m = self.model
        return nv.Box(
            padding=24,
            child=nv.Column(
                gap=16,
                children=[
                    nv.Text("Observable: Operators"),
                    nv.Text(m.price.map(lambda p: f"Unit price : ¥{p:,}")),
                    nv.Text(m.quantity.map(lambda q: f"Quantity   : {q}")),
                    nv.Text(m.discount.map(lambda d: f"Discount   : {int(d * 100)}%")),
                    nv.Text(m.subtotal.map(lambda s: f"Subtotal   : ¥{s:,}")),
                    nv.Text(m.display),
                    nv.Text(m.is_bulk.map(lambda b: "Bulk order: YES" if b else "Bulk order: NO")),
                    nv.Row(
                        gap=12,
                        children=[
                            nv.Button(
                                "Price +10",
                                on_click=lambda: setattr(m.price, "value", m.price.value + 10),
                                style=nv.ButtonStyle.filled(),
                            ),
                            nv.Button(
                                "Qty +1",
                                on_click=lambda: setattr(m.quantity, "value", m.quantity.value + 1),
                                style=nv.ButtonStyle.filled(),
                            ),
                        ],
                    ),
                    nv.Row(
                        gap=12,
                        children=[
                            nv.Button(
                                "Discount 0%",
                                on_click=lambda: setattr(m.discount, "value", 0.0),
                                style=nv.ButtonStyle.outlined(),
                            ),
                            nv.Button(
                                "Discount 10%",
                                on_click=lambda: setattr(m.discount, "value", 0.1),
                                style=nv.ButtonStyle.outlined(),
                            ),
                            nv.Button(
                                "Discount 20%",
                                on_click=lambda: setattr(m.discount, "value", 0.2),
                                style=nv.ButtonStyle.outlined(),
                            ),
                        ],
                    ),
                ],
            ),
        )


if __name__ == "__main__":
    widget = OperatorsApp()
    app = nv.App(content=widget)
    try:
        app.run()
    except Exception:
        print("Operators demo requires pyglet/skia to run.")
