from nuiitivet.material.app import MaterialApp
from nuiitivet.material.text_fields import FilledTextField, OutlinedTextField
from nuiitivet.layout.container import Container
from nuiitivet.layout.column import Column


def main():
    # Filled TextField with Label and Leading Icon
    tf_filled = FilledTextField(
        value="",
        label="Username",
        leading_icon="person",
        trailing_icon="cancel",
        width=300,
        padding=10,
    )

    # Outlined TextField with Label
    tf_outlined = OutlinedTextField(
        value="",
        label="Password",
        leading_icon="lock",
        width=300,
        padding=10,
    )

    # Error State
    tf_error = OutlinedTextField(
        value="Invalid Input",
        label="Email",
        error_text="Invalid email address",
        width=300,
        padding=10,
    )

    root = Container(
        child=Column(children=[tf_filled, tf_outlined, tf_error], gap=20), width=400, height=400, padding=20
    )
    app = MaterialApp(root)
    app.run()


if __name__ == "__main__":
    main()
