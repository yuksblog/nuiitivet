"""
Observable Debounce & Throttle Demo

Demonstrates timing control with debounce and throttle:
- Debounce: Button clicks that execute after delay
- Throttle: Button clicks sampled at regular intervals
"""

from nuiitivet.material.app import MaterialApp
from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.observable import Observable
from nuiitivet.material import Text
from nuiitivet.widgeting.widget import ComposableWidget, Widget
from nuiitivet.material.buttons import FilledButton
from nuiitivet.widgets.box import Box
from nuiitivet.material.styles.text_style import TextStyle


class DebounceModel:
    """Model with debounced counter."""

    click_count = Observable(0)
    execute_count = Observable(0)

    def __init__(self):
        # Debounce: Execute 0.5s after last click
        self.debounced = self.click_count.debounce(0.5)
        self.debounced.subscribe(self._on_execute)

    def _on_execute(self, count: int):
        """Execute after debounce period."""
        self.execute_count.value += 1
        print(f"🔵 Debounce: Executed at click count {count}")

    def increment(self):
        """Increment click counter."""
        self.click_count.value += 1


class ThrottleModel:
    """Model with throttled counter."""

    click_count = Observable(0)
    execute_count = Observable(0)

    def __init__(self):
        # Throttle: Execute at most every 0.5s
        self.throttled = self.click_count.throttle(0.5)
        self.throttled.subscribe(self._on_execute)

    def _on_execute(self, count: int):
        """Execute during throttle window."""
        self.execute_count.value += 1
        print(f"🟢 Throttle: Executed at click count {count}")

    def increment(self):
        """Increment click counter."""
        self.click_count.value += 1


class DebounceThrottleDemo(ComposableWidget):
    """Demo widget showing debounce and throttle in action."""

    def __init__(self):
        super().__init__()

        self.debounce_model = DebounceModel()
        self.throttle_model = ThrottleModel()

        # Computed observables for display
        self.debounce_clicks = Observable.compute(lambda: f"Clicks: {self.debounce_model.click_count.value}")
        self.debounce_executes = Observable.compute(lambda: f"Executions: {self.debounce_model.execute_count.value}")
        self.debounce_saved = Observable.compute(
            lambda: f"Saved: {self.debounce_model.click_count.value - self.debounce_model.execute_count.value}"
        )

        self.throttle_clicks = Observable.compute(lambda: f"Clicks: {self.throttle_model.click_count.value}")
        self.throttle_executes = Observable.compute(lambda: f"Executions: {self.throttle_model.execute_count.value}")
        self.throttle_saved = Observable.compute(
            lambda: f"Saved: {self.throttle_model.click_count.value - self.throttle_model.execute_count.value}"
        )

        self.total_savings = Observable.compute(
            lambda: f"Total Saved: {(self.debounce_model.click_count.value - self.debounce_model.execute_count.value) + (self.throttle_model.click_count.value - self.throttle_model.execute_count.value)} operations"  # noqa: E501
        )

    def build(self) -> Widget:
        return Box(
            padding=20,
            child=Column(
                gap=20,
                children=[
                    # Title
                    Text("Observable: Debounce & Throttle Demo"),
                    # Debounce Section
                    Box(
                        padding=15,
                        background_color=(230, 240, 255, 255),
                        child=Column(
                            gap=15,
                            children=[
                                Text("🔵 Debounce Demo", style=TextStyle(color=(30, 80, 150, 255))),
                                Text(
                                    "Click button rapidly. Action executes 0.5s after last click.",
                                    style=TextStyle(color=(60, 60, 60, 255)),
                                ),
                                # Button
                                FilledButton(
                                    label="Click Me (Debounced)",
                                    on_click=lambda: self.debounce_model.increment(),
                                ),
                                # Statistics
                                Box(
                                    padding=10,
                                    background_color=(255, 255, 255, 255),
                                    child=Row(
                                        gap=20,
                                        children=[
                                            Text(self.debounce_clicks, style=TextStyle(color=(50, 50, 50, 255))),
                                            Text(self.debounce_executes, style=TextStyle(color=(200, 100, 0, 255))),
                                            Text(self.debounce_saved, style=TextStyle(color=(0, 150, 0, 255))),
                                        ],
                                    ),
                                ),
                            ],
                        ),
                    ),
                    # Throttle Section
                    Box(
                        padding=15,
                        background_color=(230, 255, 230, 255),
                        child=Column(
                            gap=15,
                            children=[
                                Text("🟢 Throttle Demo", style=TextStyle(color=(30, 120, 30, 255))),
                                Text(
                                    "Click button rapidly. Action executes at most every 0.5s.",
                                    style=TextStyle(color=(60, 60, 60, 255)),
                                ),
                                # Button
                                FilledButton(
                                    label="Click Me (Throttled)",
                                    on_click=lambda: self.throttle_model.increment(),
                                ),
                                # Statistics
                                Box(
                                    padding=10,
                                    background_color=(255, 255, 255, 255),
                                    child=Row(
                                        gap=20,
                                        children=[
                                            Text(self.throttle_clicks, style=TextStyle(color=(50, 50, 50, 255))),
                                            Text(self.throttle_executes, style=TextStyle(color=(200, 100, 0, 255))),
                                            Text(self.throttle_saved, style=TextStyle(color=(0, 150, 0, 255))),
                                        ],
                                    ),
                                ),
                            ],
                        ),
                    ),
                    # Performance Summary
                    Box(
                        padding=15,
                        background_color=(255, 245, 230, 255),
                        child=Column(
                            gap=10,
                            children=[
                                Text("📊 Performance Benefits", style=TextStyle(color=(150, 80, 0, 255))),
                                Text(
                                    "• Debounce: Reduces operations by waiting for activity to stop",
                                    style=TextStyle(color=(60, 60, 60, 255)),
                                ),
                                Text(
                                    "• Throttle: Limits operation frequency to prevent overload",
                                    style=TextStyle(color=(60, 60, 60, 255)),
                                ),
                                Text(self.total_savings, style=TextStyle(color=(0, 120, 0, 255))),
                            ],
                        ),
                    ),
                    # Instructions
                    Text(
                        "💡 Try clicking both buttons rapidly and watch the difference!",
                        style=TextStyle(color=(80, 80, 80, 255)),
                    ),
                ],
            ),
        )


if __name__ == "__main__":
    widget = DebounceThrottleDemo()
    app = MaterialApp(content=widget)
    app.run()
