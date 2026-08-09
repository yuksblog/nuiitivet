import nuiitivet.material as nv


class DetailsScreen(nv.ComposableWidget):
    def build(self):
        def go_back() -> None:
            nv.Navigator.of(self).pop()

        return nv.Box(
            background_color="#F5F7FF",
            width="wt",
            height="wt",
            child=nv.Column(
                padding=16,
                gap=12,
                children=[
                    nv.Text("Animated Details Screen"),
                    nv.Button("Back", on_click=go_back, style=nv.ButtonStyle.filled()),
                ],
            ),
        )


class HomeScreen(nv.ComposableWidget):
    def build(self):
        def navigate_with_custom_animation() -> None:
            custom_transition = nv.MaterialTransitions.page(
                enter=nv.FadeIn() | nv.SlideInVertically(initial_offset_y=50.0),
                exit_=nv.FadeOut() | nv.SlideOutVertically(target_offset_y=50.0),
            )
            route = nv.Route(
                builder=lambda: DetailsScreen(),
                transition_spec=custom_transition,
            )
            nv.Navigator.of(self).push(route)

        def navigate_instantly() -> None:
            route = nv.Route(
                builder=lambda: DetailsScreen(),
                transition_spec=nv.Transitions.empty(),
            )
            nv.Navigator.of(self).push(route)

        return nv.Column(
            padding=16,
            gap=12,
            children=[
                nv.Text("Home Screen"),
                nv.Button(
                    "Go to Details (Custom Animation)",
                    on_click=navigate_with_custom_animation,
                    style=nv.ButtonStyle.filled(),
                ),
                nv.Button("Go to Details (Instant)", on_click=navigate_instantly, style=nv.ButtonStyle.filled()),
            ],
        )


def main(png_path: str | None = None) -> None:
    app = nv.App(
        content=HomeScreen(),
        title="Navigation Route",
        width=400,
        height=300,
    )
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
