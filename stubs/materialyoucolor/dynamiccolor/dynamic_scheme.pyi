from typing import Literal

from materialyoucolor.dynamiccolor.variant import Variant
from materialyoucolor.hct.hct import Hct

SpecVersion = Literal["2021", "2025"]
Platform = Literal["phone", "watch"]

class DynamicScheme:
    source_color_hct: Hct
    variant: Variant
    contrast_level: float
    is_dark: bool
    spec_version: SpecVersion

    def __init__(
        self,
        source_color_hct: Hct,
        variant: Variant,
        contrast_level: float,
        is_dark: bool,
        platform: Platform = ...,
        spec_version: SpecVersion = ...,
    ) -> None: ...
