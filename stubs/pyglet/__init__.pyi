# Minimal pyglet stub for mypy
from typing import Any

# Expose a permissive attribute importer to silence missing-imports
def __getattr__(name: str) -> Any: ...

# Common submodules that may be imported in the codebase; mark as Any
window: Any
app: Any
resource: Any
media: Any
clock: Any
version: str
