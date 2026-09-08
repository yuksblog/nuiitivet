import nuiitivet.material as nv


def build_root() -> nv.Widget:
    form = nv.Column(
        children=[
            # 1行目: 名前（横並び）
            nv.Row(
                children=[
                    nv.TextField(label="First Name"),
                    nv.TextField(label="Last Name"),
                ],
                gap=8,
            ),
            # 2行目: 住所
            nv.TextField(label="Address", width="wt"),
            # 3行目: ボタン（横並び）
            nv.Row(
                children=[
                    nv.Button("Cancel", style=nv.ButtonStyle.text()),
                    nv.Button("Register", style=nv.ButtonStyle.filled()),
                ],
                gap=12,
            ),
        ],
        gap=16,
        padding=16,
        cross_alignment="center",
    )
    return form


def main(png: str = ""):
    # ユーザー登録フォーム

    app = nv.App(nv.Window(content=build_root, title="nv.Row/nv.Column Combination", width="auto"))
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
