"""Shopping Cart Sample - Observable Phase 1

Demonstrates:
- .map() for simple transformations
- .combine().compute() for combining multiple observables
- Observable.compute() for complex calculations
- Basic reactive patterns
"""

from nuiitivet.observable import Observable, combine
from nuiitivet.material.app import MaterialApp
from nuiitivet.material import Text
from nuiitivet.widgeting.widget import ComposableWidget, Widget
from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.material.buttons import FilledButton, OutlinedButton
from nuiitivet.widgets.box import Box
from nuiitivet.material.styles.text_style import TextStyle


class ShoppingCartViewModel:
    """Shopping cart with reactive price calculations"""

    # Define observables as class attributes (descriptors)
    price = Observable(1000)
    quantity = Observable(1)
    discount_rate = Observable(0.1)  # 10% discount
    tax_rate = Observable(0.1)  # 10% tax

    def __init__(self):
        # Simple transformation using .map()
        self.formatted_price = self.price.map(lambda p: f"¥{p:,}")

        # Quantity display
        self.quantity_display = self.quantity.map(lambda q: f"{q} items")

        # Combining two observables
        self.subtotal = self.price.combine(self.quantity).compute(lambda p, q: p * q)
        self.formatted_subtotal = self.subtotal.map(lambda st: f"¥{st:,}")

        # Combining three observables
        self.discounted = combine(self.subtotal, self.discount_rate, self.tax_rate).compute(
            lambda st, dr, tr: int(st * (1 - dr) * (1 + tr))
        )
        self.formatted_discounted = self.discounted.map(lambda d: f"¥{d:,}")

        # Complex calculation with Observable.compute()
        self.summary = Observable.compute(
            lambda: (
                f"Price: ¥{self.price.value:,} x {self.quantity.value} items\n"
                f"Subtotal: ¥{self.subtotal.value:,}\n"
                f"Discount: -¥{int(self.subtotal.value * self.discount_rate.value):,} "
                f"({int(self.discount_rate.value * 100)}%)\n"
                f"Tax incl.: ¥{self.discounted.value:,}"
            )
        )

    def increase_quantity(self):
        self.quantity.value += 1

    def decrease_quantity(self):
        if self.quantity.value > 1:
            self.quantity.value -= 1

    def increase_price(self):
        self.price.value += 100

    def decrease_price(self):
        if self.price.value > 100:
            self.price.value -= 100

    def set_discount(self, rate: float):
        self.discount_rate.value = rate


class ShoppingCartApp(ComposableWidget):
    def __init__(self):
        super().__init__()
        self.viewmodel = ShoppingCartViewModel()

    def build(self) -> Widget:
        vm = self.viewmodel

        return Box(
            padding=20,
            child=Column(
                gap=20,
                children=[
                    # Title
                    Text(
                        "Shopping Cart",
                    ),
                    # Price control
                    Column(
                        gap=8,
                        children=[
                            Text("Unit Price:"),
                            Row(
                                gap=10,
                                children=[
                                    OutlinedButton("-100", on_click=lambda: vm.decrease_price()),
                                    Text(vm.formatted_price),
                                    OutlinedButton("+100", on_click=lambda: vm.increase_price()),
                                ],
                            ),
                        ],
                    ),
                    # Quantity control
                    Column(
                        gap=8,
                        children=[
                            Text("Quantity:"),
                            Row(
                                gap=10,
                                children=[
                                    OutlinedButton("-", on_click=lambda: vm.decrease_quantity()),
                                    Text(
                                        vm.quantity_display,
                                    ),
                                    OutlinedButton("+", on_click=lambda: vm.increase_quantity()),
                                ],
                            ),
                        ],
                    ),
                    # Discount buttons
                    Column(
                        gap=8,
                        children=[
                            Text("Discount Rate:"),
                            Row(
                                gap=10,
                                children=[
                                    FilledButton("0%", on_click=lambda: vm.set_discount(0.0)),
                                    FilledButton("10%", on_click=lambda: vm.set_discount(0.1)),
                                    FilledButton("20%", on_click=lambda: vm.set_discount(0.2)),
                                    FilledButton("30%", on_click=lambda: vm.set_discount(0.3)),
                                ],
                            ),
                        ],
                    ),
                    # Summary (using Observable.compute)
                    Box(
                        padding=15,
                        background_color=(240, 240, 240, 255),
                        child=Column(
                            gap=5,
                            children=[
                                Text("Summary"),
                                Text(vm.summary),
                            ],
                        ),
                    ),
                    # Final total
                    Row(
                        gap=10,
                        children=[
                            Text("Total:"),
                            Text(vm.formatted_discounted, style=TextStyle(color=(220, 50, 50, 255))),
                        ],
                    ),
                ],
            ),
        )


if __name__ == "__main__":
    widget = ShoppingCartApp()
    app = MaterialApp(content=widget)
    try:
        app.run()
    except Exception:
        print("Shopping cart demo requires pyglet/skia to run.")
