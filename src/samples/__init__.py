"""Samples package for nuiitivet.

Adding this __init__ ensures tools like mypy treat `src/samples` as a package
and avoid duplicate-module diagnostics when running type checks.
"""

__all__ = ["my_widget", "theme_demo"]
