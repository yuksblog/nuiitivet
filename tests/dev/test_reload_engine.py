"""A save patches def bodies in place, and re-executes a module with its importers for any other edit.

The project under test is the shape that breaks under "reload everything": a
model module whose service is made once and lives on, a styles module of
constants, and a view module that imports both and is rebuilt after every save.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Iterator

import pytest

from nuiitivet.dev.reloader import Reloader

MODEL = '''\
import enum


class Axis(enum.Enum):
    X = "x"


class AxisService:
    def __init__(self) -> None:
        self.positions = {Axis.X: 0}

    def position(self, axis: Axis) -> int:
        return self.positions[axis]
'''

STYLES = '''\
ACCENT = "red"
'''

VIEW = '''\
from hr_app.model import Axis, AxisService
from hr_app.styles import ACCENT


class AxisViewModel:
    def __init__(self, service: AxisService) -> None:
        self.text = f"{ACCENT} {service.position(Axis.X)}"


def make():
    service = AxisService()
    return service, (lambda: AxisViewModel(service))
'''


class Project:
    """A package on disk and on ``sys.path``, with the reloader watching it."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.reloader = Reloader(root)

    def write(self, name: str, source: str) -> None:
        path = self.root / "hr_app" / name
        path.parent.mkdir(exist_ok=True)
        path.write_text(source, encoding="utf-8")

    def edit(self, name: str, old: str, new: str) -> None:
        path = self.root / "hr_app" / name
        source = path.read_text(encoding="utf-8")
        assert old in source
        path.write_text(source.replace(old, new), encoding="utf-8")

    def load(self, name: str) -> Any:
        """Import a module of the package and put what is loaded on record, as the startup does."""
        module: ModuleType = importlib.import_module(f"hr_app.{name}")
        self.reloader.track()
        return module


@pytest.fixture
def project(tmp_path: Path) -> Iterator[Project]:
    made = Project(tmp_path)
    made.write("__init__.py", "")
    made.write("model.py", MODEL)
    made.write("styles.py", STYLES)
    made.write("view.py", VIEW)
    sys.path.insert(0, str(tmp_path))
    try:
        yield made
    finally:
        sys.path.remove(str(tmp_path))
        for name in [name for name in sys.modules if name == "hr_app" or name.startswith("hr_app.")]:
            del sys.modules[name]


def test_a_body_edit_in_the_view_leaves_the_service_alive(project: Project) -> None:
    view = project.load("view")
    model = project.load("model")
    service, factory = view.make()
    axis_x = model.Axis.X

    project.edit("view.py", 'f"{ACCENT} {service', 'f"{ACCENT} at {service')
    result = project.reloader.reload()

    assert result.changed == ["hr_app.view"]
    assert result.patched == ["hr_app.view"]
    assert result.reloaded == []
    assert factory().text == "red at 0"
    assert isinstance(service, model.AxisService)
    assert model.Axis.X is axis_x


def test_a_body_edit_in_the_model_reaches_the_living_service(project: Project) -> None:
    view = project.load("view")
    model = project.load("model")
    service, factory = view.make()

    project.edit("model.py", "return self.positions[axis]", "return self.positions[axis] + 100")
    result = project.reloader.reload()

    assert result.patched == ["hr_app.model"]
    assert service.position(model.Axis.X) == 100
    assert factory().text == "red 100"


def test_an_edit_outside_a_body_reexecutes_the_module_and_its_importers_only(project: Project) -> None:
    view = project.load("view")
    model = project.load("model")
    service, factory = view.make()
    service_class = model.AxisService

    project.edit("styles.py", '"red"', '"blue"')
    result = project.reloader.reload()

    assert result.patched == []
    assert result.reloaded == ["hr_app.styles", "hr_app.view"]
    assert result.edited == ["hr_app.styles"]
    assert factory().text == "blue 0"
    assert model.AxisService is service_class


def test_an_added_enum_member_reexecutes_the_model_and_hands_over_its_old_classes(project: Project) -> None:
    view = project.load("view")
    model = project.load("model")
    service, _factory = view.make()
    old_service_class = model.AxisService

    project.edit("model.py", '    X = "x"\n', '    X = "x"\n    Y = "y"\n')
    result = project.reloader.reload()

    assert result.reloaded == ["hr_app.model", "hr_app.view"]
    assert result.edited == ["hr_app.model"]
    assert [member.name for member in model.Axis] == ["X", "Y"]
    assert old_service_class in [ref() for ref in result.replaced["hr_app.model"]]
    assert type(service) is old_service_class


def test_a_changed_signature_reexecutes_the_module(project: Project) -> None:
    project.load("view")
    model = project.load("model")

    project.edit("model.py", "(self, axis: Axis) -> int:", "(self, axis: Axis, scale: int = 2) -> int:")
    result = project.reloader.reload()

    assert "hr_app.model" in result.reloaded
    assert model.AxisService().position(model.Axis.X) == 0


def test_a_save_that_does_not_compile_applies_nothing(project: Project) -> None:
    view = project.load("view")
    project.load("model")
    service, factory = view.make()

    project.edit("view.py", 'f"{ACCENT} {service', 'f"{ACCENT} at {service')
    project.edit("styles.py", '"red"', '"blue')
    with pytest.raises(SyntaxError):
        project.reloader.reload()

    assert project.reloader.last.changed == ["hr_app.styles", "hr_app.view"]
    assert factory().text == "red 0"

    project.edit("styles.py", '"blue', '"blue"')
    project.reloader.reload()
    assert factory().text == "blue at 0"


def test_a_module_that_raised_is_reexecuted_on_the_next_save_even_when_reverted(project: Project) -> None:
    project.load("view")
    styles = project.load("styles")

    project.edit("styles.py", '"red"', "undefined_name")
    with pytest.raises(NameError):
        project.reloader.reload()

    project.edit("styles.py", "undefined_name", '"red"')
    result = project.reloader.reload()

    assert result.reloaded == ["hr_app.styles", "hr_app.view"]
    assert styles.ACCENT == "red"


def test_a_save_that_changes_no_text_does_nothing(project: Project) -> None:
    project.load("view")

    project.write("view.py", VIEW)
    result = project.reloader.reload()

    assert (result.changed, result.patched, result.reloaded) == ([], [], [])


def test_a_module_imported_after_startup_is_on_record_from_the_next_poll(project: Project) -> None:
    project.load("styles")
    view = importlib.import_module("hr_app.view")
    model = sys.modules["hr_app.model"]
    service, factory = view.make()
    project.reloader.track()  # the watcher's poll

    project.edit("view.py", 'f"{ACCENT} {service', 'f"{ACCENT} at {service')
    result = project.reloader.reload()

    assert result.patched == ["hr_app.view"]
    assert result.reloaded == []
    assert isinstance(service, model.AxisService)
    assert factory().text == "red at 0"


def test_a_module_saved_before_it_was_put_on_record_is_reexecuted(project: Project) -> None:
    project.load("styles")
    view = importlib.import_module("hr_app.view")
    _service, factory = view.make()

    project.edit("view.py", 'f"{ACCENT} {service', 'f"{ACCENT} at {service')
    result = project.reloader.reload()

    assert result.patched == []
    assert result.reloaded == ["hr_app.view"]
    assert factory().text == "red at 0"


def test_a_module_imported_after_startup_and_not_saved_is_left_alone(project: Project) -> None:
    project.load("styles")
    importlib.import_module("hr_app.view")

    result = project.reloader.reload()

    assert (result.changed, result.patched, result.reloaded) == ([], [], [])


def test_an_edit_that_changes_what_a_body_closes_over_reexecutes_the_module(project: Project) -> None:
    project.write(
        "closure.py",
        "def outer():\n    kept = 1\n    other = 2\n\n    def inner():\n        return kept\n\n    return inner\n",
    )
    closure = project.load("closure")
    inner = closure.outer()

    project.edit("closure.py", "        return kept\n", "        return kept + other\n")
    result = project.reloader.reload()

    assert result.patched == []
    assert result.reloaded == ["hr_app.closure"]
    assert inner() == 1
    assert closure.outer()() == 3


def test_a_patched_module_that_imports_a_refused_one_is_reexecuted_and_not_listed_as_patched(
    project: Project,
) -> None:
    project.write(
        "closure.py",
        "def outer():\n    kept = 1\n    other = 2\n\n    def inner():\n        return kept\n\n    return inner\n",
    )
    project.write("user.py", "from hr_app.closure import outer\n\n\ndef use():\n    return outer()() + 0\n")
    closure = project.load("closure")
    user = project.load("user")
    inner = closure.outer()  # a living closure the edited body does not fit

    project.edit("closure.py", "        return kept\n", "        return kept + other\n")
    project.edit("user.py", "return outer()() + 0", "return outer()() + 10")
    result = project.reloader.reload()

    assert inner() == 1
    assert result.patched == []
    assert result.reloaded == ["hr_app.closure", "hr_app.user"]
    assert user.use() == 13


def test_a_named_factory_is_refetched_and_a_lambda_is_kept(project: Project) -> None:
    view = project.load("view")
    _service, factory = view.make()

    project.edit("styles.py", '"red"', '"blue"')

    assert project.reloader.reload(old_factory=view.make).new_factory is sys.modules["hr_app.view"].make
    project.edit("styles.py", '"blue"', '"green"')
    assert project.reloader.reload(old_factory=factory).new_factory is None
