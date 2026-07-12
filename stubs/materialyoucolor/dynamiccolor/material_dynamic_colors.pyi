from typing import List

from materialyoucolor.dynamiccolor.dynamic_color import DynamicColor
from materialyoucolor.dynamiccolor.dynamic_scheme import SpecVersion

class MaterialDynamicColors:
    def __init__(self, spec: SpecVersion = ...) -> None: ...
    @property
    def all_colors(self) -> List[DynamicColor]: ...

    # Roles are exposed as camelCase attributes named after the M3 color roles
    # (`primary`, `onSurface`, ...), which nuiitivet reaches via `getattr`.
    def __getattr__(self, name: str) -> DynamicColor: ...
