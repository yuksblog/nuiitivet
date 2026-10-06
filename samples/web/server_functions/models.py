"""Types the app and the server exchange. Both sides import this module."""

from dataclasses import dataclass


@dataclass
class Report:
    scanned: int
    matches: list[str]
