"""The catalog of the keep-alive demo, in a file of its own.

``app.py`` loads it once in ``main()``. A save to ``app.py`` leaves this file
alone, so the catalog stays current whatever ``app.py`` changes.
"""

import time


class Catalog:
    """A list of products that is slow to load."""

    def __init__(self) -> None:
        time.sleep(1.0)  # stand-in for reading a large file
        self.loaded_at = time.strftime("%H:%M:%S")
        self.products = ["Kettle", "Teapot", "Tea strainer", "Coffee mill"]

    def search(self, word: str) -> list[str]:
        return [name for name in self.products if word.lower() in name.lower()]
