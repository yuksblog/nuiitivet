import sys
from collections import deque


def inspect_overlay_and_text(btn, resolve_color):
    try:
        st = getattr(btn, "_style")
    except Exception:
        st = None
    print("style attribute:", st)
    ov_entry = None
    try:
        ov_entry = btn._resolve_overlay_entry()
    except Exception as e:
        print("resolve overlay entry error", e)
    print("overlay entry:", ov_entry)
    if ov_entry and ov_entry[0] is not None:
        try:
            ov_color = resolve_color((ov_entry[0], ov_entry[1]))
        except Exception as e:
            ov_color = f"err:{e}"
    else:
        ov_color = None
    child = btn.children[0] if getattr(btn, "children", None) else None
    child_color = None
    try:
        if child is not None and hasattr(child, "color"):
            child_color = resolve_color(child.color)
    except Exception as e:
        child_color = f"err:{e}"
    print("resolved overlay color (skia/rgba or tuple):", ov_color)
    print("resolved child color (skia/rgba or tuple):", child_color)


def main() -> None:
    # Ensure project src on sys.path for local imports
    if "src" not in sys.path:
        sys.path.insert(0, "src")

    # Local imports that rely on adjusted sys.path
    from samples.my_widget import MyWidgetModel, MyWidget
    from nuiitivet.material.buttons import FilledButton, ElevatedButton, FilledTonalButton
    from nuiitivet.runtime.pointer import PointerEvent, PointerEventType
    from nuiitivet.theme import manager as theme_manager
    from nuiitivet.theme.resolver import resolve_color_to_rgba
    from nuiitivet.rendering.skia import rgba_to_skia_color, get_skia

    def resolve_color(val):
        """Compatibility helper for the debug script: resolve to RGBA then
        convert to a skia color if skia is available; otherwise return the
        RGBA tuple."""
        rgba = resolve_color_to_rgba(val)
        if rgba is None:
            return None
        if get_skia() is not None:
            try:
                return rgba_to_skia_color(rgba)
            except Exception:
                return rgba
        return rgba

    model = MyWidgetModel()
    widget = MyWidget(model)
    root = widget.build()

    def find_first(btn_types):
        q = deque([root])
        while q:
            node = q.popleft()
            try:
                children = getattr(node, "children_snapshot", lambda: getattr(node, "children", []))()
            except Exception:
                try:
                    children = getattr(node, "children", [])
                except Exception:
                    children = []
            for c in children:
                q.append(c)
            for t in btn_types:
                if isinstance(node, t):
                    return node
        return None

    target = find_first([FilledButton, ElevatedButton, FilledTonalButton])
    print("Target button found:", type(target).__name__ if target else None)

    print("Current theme mode:", theme_manager.current.mode)
    inspect_overlay_and_text(target, resolve_color)
    target.on_pointer_event(PointerEvent.mouse_event(1, PointerEventType.ENTER, 0, 0))
    print("after mouse_enter hover flag:", getattr(target, "_hover", None))
    inspect_overlay_and_text(target, resolve_color)
    target.on_pointer_event(PointerEvent.mouse_event(1, PointerEventType.PRESS, 0, 0))
    print("after mouse_press pressed flag:", getattr(target, "_pressed", None))
    inspect_overlay_and_text(target, resolve_color)
    target.on_pointer_event(PointerEvent.mouse_event(1, PointerEventType.RELEASE, 0, 0))
    print("after mouse_release pressed flag:", getattr(target, "_pressed", None))
    inspect_overlay_and_text(target, resolve_color)


if __name__ == "__main__":
    main()
