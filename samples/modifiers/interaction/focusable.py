import nuiitivet.material as nv


def _format_modifier_keys(modifier_keys: int) -> str:
    """Render a modifier-key bitmask as a human-readable string like 'CTRL|SHIFT'."""
    names = []
    if modifier_keys & nv.MOD_SHIFT:
        names.append("SHIFT")
    if modifier_keys & nv.MOD_CTRL:
        names.append("CTRL")
    if modifier_keys & nv.MOD_ALT:
        names.append("ALT")
    if modifier_keys & nv.MOD_META:
        names.append("META")
    return "|".join(names) if names else "-"


class FocusDemo(nv.ComposableWidget):
    def __init__(self, label: str):
        super().__init__()
        self.label = label
        self.is_focused = nv.Observable(False)
        # Last observed key event, shown live in the widget so behavior is
        # visible without watching the console.
        self.last_event = nv.Observable("(no key yet)")

    def _set_focused(self, focused: bool, source) -> None:
        # ``on_focus_change`` is invoked as ``(focused, source)``; ``source`` is a
        # FocusSource enum (KEYBOARD / POINTER).
        self.is_focused.value = focused
        print(f"[{self.label}] focus_change   focused={focused} source={getattr(source, 'value', source)}")

    def _on_key(self, key: str, modifier_keys: int) -> bool:
        mods = _format_modifier_keys(modifier_keys)
        print(f"[{self.label}] key_DOWN       key={key!r:<10} mods={mods}")
        self.last_event.value = f"DOWN {key} [{mods}]"
        return True

    def _on_key_up(self, key: str, modifier_keys: int) -> bool:
        mods = _format_modifier_keys(modifier_keys)
        print(f"[{self.label}] key_UP         key={key!r:<10} mods={mods}")
        self.last_event.value = f"UP {key} [{mods}]"
        return True

    def build(self):
        border_color = self.is_focused.map(lambda f: "#2196F3" if f else "#00000000")

        return nv.Container(
            width=280,
            height=64,
            child=nv.Column(
                children=[
                    nv.Text(self.label),
                    nv.Text(self.last_event),
                ],
                gap=4,
            ),
            alignment="center",
        ).modifier(
            nv.background("#E0E0E0")
            | nv.corner_radius(8)
            | nv.border(color=border_color, width=2)
            | nv.focusable(
                on_focus_change=self._set_focused,
                on_key=self._on_key,
                on_key_up=self._on_key_up,
            )
        )


def main(png: str = ""):
    print("=" * 68)
    print("Focusable key-event demo (#310)")
    print("  1. Press Tab to focus a field (watch focus_change).")
    print("  2. Type letters / arrows -> key_DOWN then key_UP for each.")
    print("  3. Hold Shift/Ctrl/Alt/Cmd while typing -> mods shows the mask.")
    print("  4. Press & release Escape -> back-navigation, no phantom DOWN.")
    print("  5. Cmd/Alt+Tab away and back -> mask is cleared on deactivate.")
    print("=" * 68)

    content = nv.Column(
        children=[FocusDemo("field-1"), FocusDemo("field-2")],
        gap=16,
        padding=16,
    )

    app = nv.App(nv.Window(content=content, title="Focusable Modifier"))
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
