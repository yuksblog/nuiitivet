from __future__ import annotations

from nuiitivet.widgeting.widget import ComposableWidget, Widget
from nuiitivet.layout.column import Column
from nuiitivet.widgets.text import TextBase as Text


class _PartialScopeWidget(ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self.left_value = 0
        self.right_value = 0
        self.left_builds = 0
        self.right_builds = 0
        self._left_scope: str | None = None
        self._right_scope: str | None = None

    def build(self) -> Widget:
        with self.scope("left") as handle:
            self._left_scope = handle.id
            left = self.render_scope_with_handle(handle, self._build_left)
        with self.scope("right") as handle:
            self._right_scope = handle.id
            right = self.render_scope_with_handle(handle, self._build_right)
        return Column([left, right], gap=4)

    def _build_left(self) -> Widget:
        self.left_builds += 1
        return Text(f"left:{self.left_value}")

    def _build_right(self) -> Widget:
        self.right_builds += 1
        return Text(f"right:{self.right_value}")

    def bump_left(self) -> None:
        self.left_value += 1
        if self._left_scope:
            self.invalidate_scope_id(self._left_scope)

    def bump_right(self) -> None:
        self.right_value += 1
        if self._right_scope:
            self.invalidate_scope_id(self._right_scope)

    def bump_both(self) -> None:
        self.left_value += 1
        self.right_value += 1
        if self._left_scope:
            self.invalidate_scope_id(self._left_scope)
        if self._right_scope:
            self.invalidate_scope_id(self._right_scope)


def test_scope_invalidation_targets_single_fragment() -> None:
    widget = _PartialScopeWidget()
    widget.rebuild()
    assert widget.left_builds == 1
    assert widget.right_builds == 1
    layout_token = widget.layout_cache_token

    widget.bump_left()

    assert widget.left_builds == 2
    assert widget.right_builds == 1
    assert widget.layout_cache_token == layout_token


def test_scope_invalidation_handles_secondary_fragment() -> None:
    widget = _PartialScopeWidget()
    widget.rebuild()
    widget.bump_right()
    assert widget.left_builds == 1
    assert widget.right_builds == 2


def test_scope_invalidation_can_update_both_fragments() -> None:
    widget = _PartialScopeWidget()
    widget.rebuild()
    widget.bump_both()
    assert widget.left_builds == 2
    assert widget.right_builds == 2
