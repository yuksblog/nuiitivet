"""Material Widgets - TextField input filters and commit-time normalization.

An Observable passed as ``value`` is the field's value: it is displayed, and
what the user types is written back into it. ``input_filter`` decides what may
be typed in the first place, and ``on_focus_change`` finishes the value once
the user leaves the field.
"""

from __future__ import annotations

import nuiitivet.material as nv


class Form(nv.ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self.pin = nv.Observable("")
        self.rate = nv.Observable("")
        self.code = nv.Observable("")
        # Derived, so nothing has to be kept in sync by hand: the fields write
        # into the Observables and this recomputes.
        self.summary = nv.combine(self.pin, self.rate, self.code).compute(
            lambda pin, rate, code: f"pin={pin!r} rate={rate!r} code={code!r}"
        )

    def _finish_rate(self, focused: bool, source: nv.FocusSource) -> None:
        """Turn a typeable value into a finished one, once the user leaves.

        ``"1."`` has to be typeable or the ``.`` could never be entered, so the
        filter accepts it and the rounding happens here instead. This belongs
        to focus rather than to ``on_submit``: leaving the field is what
        finishes a value, and pressing Enter is a request to *act* on it.
        """
        if focused:
            return
        self.rate.value = f"{float(self.rate.value or 0):.2f}"

    def build(self) -> nv.Widget:
        return nv.Container(
            padding=24,
            child=nv.Column(
                gap=16,
                cross_alignment="start",
                children=[
                    nv.TextField(
                        value=self.pin,
                        label="PIN (4 digits)",
                        input_filter=nv.digits_only() | nv.max_length(4),
                        width=320,
                        style=nv.TextFieldStyle.outlined(),
                    ),
                    nv.TextField(
                        value=self.rate,
                        label="Rate (one decimal point)",
                        input_filter=nv.matching(r"[0-9]*\.?[0-9]*"),
                        on_focus_change=self._finish_rate,
                        supporting_text="Rounded to 2 decimals when you leave the field",
                        width=320,
                        style=nv.TextFieldStyle.outlined(),
                    ),
                    nv.TextField(
                        value=self.code,
                        label="Code (upper-cased, no spaces)",
                        input_filter=nv.deny(r"\s") | (lambda s: s.upper()),
                        width=320,
                        style=nv.TextFieldStyle.outlined(),
                    ),
                    nv.Text(self.summary),
                ],
            ),
        )


def main(png_path: str = "") -> None:
    app = nv.App(
        content=Form(),
        title="TextField input filters",
        width=440,
        height=380,
    )
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
