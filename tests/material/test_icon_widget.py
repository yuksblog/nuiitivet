from nuiitivet.material.icon import Icon


def test_icon_preferred_size_square():
    ic = Icon("home", size=32)
    assert ic.preferred_size() == (32, 32)


def test_icon_build_returns_self():
    ic = Icon("menu")
    assert not hasattr(ic, "build")
