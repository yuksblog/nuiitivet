"""Test padding support for Column and Row layouts."""

from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.widgets.text import TextBase as Text


def test_column_default_padding():
    """Column should have default padding of 0."""
    col = Column([Text("A"), Text("B")])
    assert col.padding == (0, 0, 0, 0)


def test_column_with_int_padding():
    """Column should accept int padding (all sides)."""
    col = Column([Text("A")], padding=10)
    assert col.padding == (10, 10, 10, 10)


def test_column_with_tuple_padding():
    """Column should accept (h, v) and (l, t, r, b) padding."""
    col1 = Column([Text("A")], padding=(10, 20))
    assert col1.padding == (10, 20, 10, 20)
    col2 = Column([Text("A")], padding=(5, 10, 15, 20))
    assert col2.padding == (5, 10, 15, 20)


def test_column_preferred_size_includes_padding():
    """Column preferred_size should include padding."""
    col = Column([Text("A")], padding=10)
    w, h = col.preferred_size()
    assert w > 0
    assert h > 0
    col_no_pad = Column([Text("A")], padding=0)
    w0, h0 = col_no_pad.preferred_size()
    assert w == w0 + 20
    assert h == h0 + 20


def test_column_spacing_and_padding():
    """Column should handle both spacing and padding correctly."""
    col = Column([Text("A"), Text("B")], gap=5, padding=10)
    w, h = col.preferred_size()
    assert w > 0
    assert h > 0
    assert col.padding == (10, 10, 10, 10)


def test_row_default_padding():
    """Row should have default padding of 0."""
    row = Row([Text("A"), Text("B")])
    assert row.padding == (0, 0, 0, 0)


def test_row_with_int_padding():
    """Row should accept int padding (all sides)."""
    row = Row([Text("A")], padding=10)
    assert row.padding == (10, 10, 10, 10)


def test_row_with_tuple_padding():
    """Row should accept (h, v) and (l, t, r, b) padding."""
    row1 = Row([Text("A")], padding=(10, 20))
    assert row1.padding == (10, 20, 10, 20)
    row2 = Row([Text("A")], padding=(5, 10, 15, 20))
    assert row2.padding == (5, 10, 15, 20)


def test_row_preferred_size_includes_padding():
    """Row preferred_size should include padding."""
    row = Row([Text("A")], padding=10)
    w, h = row.preferred_size()
    assert w > 0
    assert h > 0
    row_no_pad = Row([Text("A")], padding=0)
    w0, h0 = row_no_pad.preferred_size()
    assert w == w0 + 20
    assert h == h0 + 20


def test_row_spacing_and_padding():
    """Row should handle both spacing and padding correctly."""
    row = Row([Text("A"), Text("B")], gap=5, padding=10)
    w, h = row.preferred_size()
    assert w > 0
    assert h > 0
    assert row.padding == (10, 10, 10, 10)


def test_column_content_rect():
    """Column should use content_rect for child layout."""
    col = Column([Text("A")], padding=10)
    cx, cy, cw, ch = col.content_rect(0, 0, 100, 100)
    assert cx == 10
    assert cy == 10
    assert cw == 80
    assert ch == 80


def test_row_content_rect():
    """Row should use content_rect for child layout."""
    row = Row([Text("A")], padding=10)
    cx, cy, cw, ch = row.content_rect(0, 0, 100, 100)
    assert cx == 10
    assert cy == 10
    assert cw == 80
    assert ch == 80


def test_column_asymmetric_padding():
    """Column should handle asymmetric padding correctly."""
    col = Column([Text("A")], padding=(5, 10, 15, 20))
    w, h = col.preferred_size()
    col_no_pad = Column([Text("A")], padding=0)
    w0, h0 = col_no_pad.preferred_size()
    assert w == w0 + 20
    assert h == h0 + 30


def test_row_asymmetric_padding():
    """Row should handle asymmetric padding correctly."""
    row = Row([Text("A")], padding=(5, 10, 15, 20))
    w, h = row.preferred_size()
    row_no_pad = Row([Text("A")], padding=0)
    w0, h0 = row_no_pad.preferred_size()
    assert w == w0 + 20
    assert h == h0 + 30
