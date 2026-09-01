"""Build hook that bundles the repository's ``skills/`` tree into the wheel.

setuptools package-data cannot reference files outside a package directory, so
a custom ``build_py`` copies the repo-root ``skills/`` into
``nuiitivet/_skills_data/`` in the build tree. At runtime,
``python -m nuiitivet.skills install`` copies them from there into a Claude
Code skills directory. All project metadata stays in ``pyproject.toml``.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py


class BuildPyWithSkills(build_py):
    """``build_py`` that also ships ``skills/`` as ``nuiitivet._skills_data``."""

    def run(self) -> None:
        super().run()
        source = Path(__file__).resolve().parent / "skills"
        target = Path(self.build_lib) / "nuiitivet" / "_skills_data"
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(
            source,
            target,
            ignore=shutil.ignore_patterns("__pycache__", "*.py[cod]"),
        )


setup(cmdclass={"build_py": BuildPyWithSkills})
