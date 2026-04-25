from nuiitivet.material import App
from nuiitivet.material import Checkbox, Text
from nuiitivet.material.text_fields import TextField
from nuiitivet.layout.container import Container
from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.material.styles.text_field_style import TextFieldStyle


def main():
    # Filled TextField with Label and Leading Icon
    tf_filled = TextField(
        value="",
        label="Username",
        leading_icon="person",
        trailing_icon="cancel",
        width=300,
        padding=10,
    )

    # Outlined TextField with Label
    tf_outlined = TextField(
        value="",
        label="Password",
        leading_icon="lock",
        obscure_text=True,
        width=300,
        padding=10,
        style=TextFieldStyle.outlined(),
    )

    def _toggle_obscure(checked: bool | None) -> None:
        tf_outlined.obscure_text = bool(checked)

    obscure_toggle = Row(
        gap=8,
        children=[
            Checkbox(checked=True, on_toggle=_toggle_obscure),
            Text("Obscure password text"),
        ],
    )

    # Error State
    tf_error = TextField(
        value="Invalid Input",
        label="Email",
        supporting_text="Invalid email address",
        is_error=True,
        width=300,
        padding=10,
        style=TextFieldStyle.outlined(),
    )

    root = Container(
        child=Column(children=[tf_filled, tf_outlined, obscure_toggle, tf_error], gap=20),
        width=400,
        height=400,
        padding=20,
    )
    app = App(root)
    app.run()


if __name__ == "__main__":
    main()
