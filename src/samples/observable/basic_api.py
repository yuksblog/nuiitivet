"""Observable: Basic API

Demonstrates:
- Creating Observables with various value types
- Getting and setting values
- Subscribing and unsubscribing
- Custom comparison functions
"""

from nuiitivet.observable import Observable
from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.material import App, Text, ButtonStyle
from nuiitivet.material.buttons import Button
from nuiitivet.widgeting.widget import ComposableWidget, Widget
from nuiitivet.widgets.box import Box


class UserRecord:
    def __init__(self, uid: int, name: str) -> None:
        self.uid = uid
        self.name = name


def compare_users(a: UserRecord | None, b: UserRecord | None) -> bool:
    """Compare users by uid only; name changes alone do not trigger notifications."""
    if a is None or b is None:
        return a is b
    return a.uid == b.uid


class BasicApiApp(ComposableWidget):
    """Showcases creating, reading, updating, subscribing, and custom compare."""

    def __init__(self) -> None:
        super().__init__()

        # --- Creating Observables ---
        self.name = Observable("Alice")
        self.age = Observable(20)
        self.items: Observable[list[str]] = Observable([])

        # Custom comparison 1: always notify even when the value is unchanged
        self.noise = Observable(0, compare=lambda a, b: False)
        self._noise_write_count = Observable(0)
        self._noise_notify_count = Observable(0)
        self.noise.subscribe(lambda _: setattr(self._noise_notify_count, "value", self._noise_notify_count.value + 1))

        # Custom comparison 2: user identity determined by uid only
        self.user: Observable[UserRecord] = Observable(UserRecord(1, "Alice"), compare=compare_users)
        self._rename_write_count = Observable(0)
        self._user_notify_count = Observable(0)
        self.user.subscribe(lambda _: setattr(self._user_notify_count, "value", self._user_notify_count.value + 1))

        # --- Derived display labels ---
        self.age_label = self.age.map(lambda a: f"Age: {a}")
        self.items_label = self.items.map(lambda lst: f"Items: {lst}")
        # noise value は常に 0 のまま。書き込み回数と通知回数を並べて対比する。
        self.noise_write_label = self._noise_write_count.map(lambda n: f"Noise: written {n}x")
        self.noise_notify_label = self._noise_notify_count.map(lambda n: f"Noise: notified {n}x  (value always 0)")
        # user_label は通知が来たときだけ更新される。rename_write_count と対比する。
        self.user_label = self.user.map(lambda u: f"User (last notified): uid={u.uid}  name={u.name}")
        self.rename_write_label = self._rename_write_count.map(lambda n: f"Name writes: {n}x")
        self.user_notify_label = self._user_notify_count.map(lambda n: f"User notifications: {n}x")

        # --- Subscribing ---
        # The returned Disposable keeps the subscription alive while held.
        self._age_sub = self.age.subscribe(lambda v: print(f"[subscribe] age changed -> {v}"))

    # --- Getting and setting values via methods (value = ...) ---

    def _birthday(self) -> None:
        self.age.value += 1

    def _add_item(self) -> None:
        self.items.value = self.items.value + [f"item{len(self.items.value) + 1}"]

    def _tick_noise(self) -> None:
        # Assign the same value; compare=lambda a,b: False guarantees notification.
        self.noise.value = self.noise.value
        self._noise_write_count.value += 1

    def _rename_user(self) -> None:
        # uid stays the same → compare_users returns True → no notification, _value not updated.
        u = self.user.value
        self.user.value = UserRecord(u.uid, "Bob" if u.name == "Alice" else "Alice")
        self._rename_write_count.value += 1

    def _change_user_id(self) -> None:
        # uid changes → compare_users returns False → notification fires
        u = self.user.value
        self.user.value = UserRecord(u.uid + 1, u.name)
        print(f"[change_user_id] user id changed to {self.user.value.uid} (name={self.user.value.name})")

    # --- Unsubscribing ---

    def _unsubscribe_age(self) -> None:
        self._age_sub.dispose()

    def build(self) -> Widget:
        return Box(
            padding=24,
            child=Column(
                gap=16,
                children=[
                    Text("Observable: Basic API"),
                    # Getting / setting
                    Text(self.age_label),
                    Text(self.items_label),
                    Row(
                        gap=8,
                        children=[
                            Button("Birthday (+1)", on_click=self._birthday, style=ButtonStyle.filled()),
                            Button("Add item", on_click=self._add_item, style=ButtonStyle.outlined()),
                        ],
                    ),
                    # subscribe / unsubscribe (check console for output)
                    Button(
                        "Unsubscribe age log (check console)",
                        on_click=self._unsubscribe_age,
                        style=ButtonStyle.text(),
                    ),
                    # Custom comparison 1: always notify
                    # compare=lambda a,b: False なので同じ値でも必ず通知される
                    Text(self.noise_write_label),
                    Text(self.noise_notify_label),
                    Button(
                        "Set same noise value (written = notified)",
                        on_click=self._tick_noise,
                        style=ButtonStyle.outlined(),
                    ),
                    # Custom comparison 2: compare by uid
                    # uid が同じなら通知されない → ラベルも更新されない
                    Text(self.user_label),
                    Text(self.rename_write_label),
                    Text(self.user_notify_label),
                    Row(
                        gap=8,
                        children=[
                            Button(
                                "Rename (writes++ / notifications unchanged)",
                                on_click=self._rename_user,
                                style=ButtonStyle.outlined(),
                            ),
                            Button(
                                "Change uid (writes++ / notifications++)",
                                on_click=self._change_user_id,
                                style=ButtonStyle.filled(),
                            ),
                        ],
                    ),
                ],
            ),
        )


if __name__ == "__main__":
    widget = BasicApiApp()
    app = App(content=widget)
    try:
        app.run()
    except Exception:
        print("Basic API demo requires pyglet/skia to run.")
