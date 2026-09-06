"""Observable: Basic API

Demonstrates:
- Creating Observables with various value types
- Getting and setting values
- Subscribing and unsubscribing
- Custom comparison functions
"""

import nuiitivet.material as nv


class UserRecord:
    def __init__(self, uid: int, name: str) -> None:
        self.uid = uid
        self.name = name


def compare_users(a: UserRecord | None, b: UserRecord | None) -> bool:
    """Compare users by uid only; name changes alone do not trigger notifications."""
    if a is None or b is None:
        return a is b
    return a.uid == b.uid


class BasicApiApp(nv.ComposableWidget):
    """Showcases creating, reading, updating, subscribing, and custom compare."""

    def __init__(self) -> None:
        super().__init__()

        # --- Creating Observables ---
        self.name = nv.Observable("Alice")
        self.age = nv.Observable(20)
        self.items: nv.Observable[list[str]] = nv.Observable([])

        # Custom comparison 1: always notify even when the value is unchanged
        self.noise = nv.Observable(0, compare=lambda a, b: False)
        self._noise_write_count = nv.Observable(0)
        self._noise_notify_count = self.noise.scan(lambda n, _: n + 1, initial=0)

        # Custom comparison 2: user identity determined by uid only
        self.user: nv.Observable[UserRecord] = nv.Observable(UserRecord(1, "Alice"), compare=compare_users)
        self._rename_write_count = nv.Observable(0)
        self._user_notify_count = self.user.scan(lambda n, _: n + 1, initial=0)

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

    def build(self) -> nv.Widget:
        return nv.Box(
            padding=24,
            child=nv.Column(
                gap=16,
                children=[
                    nv.Text("Observable: Basic API"),
                    # Getting / setting
                    nv.Text(self.age_label),
                    nv.Text(self.items_label),
                    nv.Row(
                        gap=8,
                        children=[
                            nv.Button("Birthday (+1)", on_click=self._birthday, style=nv.ButtonStyle.filled()),
                            nv.Button("Add item", on_click=self._add_item, style=nv.ButtonStyle.outlined()),
                        ],
                    ),
                    # subscribe / unsubscribe (check console for output)
                    nv.Button(
                        "Unsubscribe age log (check console)",
                        on_click=self._unsubscribe_age,
                        style=nv.ButtonStyle.text(),
                    ),
                    # Custom comparison 1: always notify
                    # compare=lambda a,b: False なので同じ値でも必ず通知される
                    nv.Text(self.noise_write_label),
                    nv.Text(self.noise_notify_label),
                    nv.Button(
                        "Set same noise value (written = notified)",
                        on_click=self._tick_noise,
                        style=nv.ButtonStyle.outlined(),
                    ),
                    # Custom comparison 2: compare by uid
                    # uid が同じなら通知されない → ラベルも更新されない
                    nv.Text(self.user_label),
                    nv.Text(self.rename_write_label),
                    nv.Text(self.user_notify_label),
                    nv.Row(
                        gap=8,
                        children=[
                            nv.Button(
                                "Rename (writes++ / notifications unchanged)",
                                on_click=self._rename_user,
                                style=nv.ButtonStyle.outlined(),
                            ),
                            nv.Button(
                                "Change uid (writes++ / notifications++)",
                                on_click=self._change_user_id,
                                style=nv.ButtonStyle.filled(),
                            ),
                        ],
                    ),
                ],
            ),
        )


def main() -> None:
    app = nv.App(nv.Window(content=BasicApiApp()))
    app.run()


if __name__ == "__main__":
    main()
