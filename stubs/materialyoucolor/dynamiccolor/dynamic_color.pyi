from materialyoucolor.dynamiccolor.dynamic_scheme import DynamicScheme
from materialyoucolor.hct.hct import Hct

class DynamicColor:
    name: str

    def get_argb(self, scheme: DynamicScheme) -> int: ...
    def get_hct(self, scheme: DynamicScheme) -> Hct: ...
