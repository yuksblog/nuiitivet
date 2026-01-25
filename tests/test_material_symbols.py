from nuiitivet.material.symbols import Symbols


def test_symbols_from_name_returns_symbol() -> None:
    symbol = Symbols.from_name("home")
    assert symbol is not None
    assert symbol.name == "home"
    assert symbol.glyph() == "\ue9b2"


def test_symbols_glyph_for_handles_unknowns() -> None:
    assert Symbols.glyph_for("home") == "\ue9b2"
    assert Symbols.glyph_for("_not_a_symbol_") is None
    assert Symbols.from_name(None) is None
