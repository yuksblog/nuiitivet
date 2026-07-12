class Hct:
    hue: float
    chroma: float
    tone: float

    @staticmethod
    def from_int(argb: int) -> Hct: ...
    @staticmethod
    def from_hct(hue: float, chroma: float, tone: float) -> Hct: ...
    def to_int(self) -> int: ...
