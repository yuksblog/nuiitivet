import nuiitivet as nv
import nuiitivet.material as md


def main(png: str = ""):
    # ユーザー登録フォーム
    form = nv.Column(
        children=[
            # 1行目: 名前（横並び）
            nv.Row(
                children=[
                    md.FilledTextField(label="First Name"),
                    md.FilledTextField(label="Last Name"),
                ],
                gap=8,
            ),
            # 2行目: 住所
            md.FilledTextField(label="Address", width=nv.Sizing.flex(1)),
            # 3行目: ボタン（横並び）
            nv.Row(
                children=[
                    md.TextButton("Cancel"),
                    md.FilledButton("Register"),
                ],
                gap=12,
            ),
        ],
        gap=16,
        padding=16,
        cross_alignment="center",
    )

    app = md.MaterialApp(
        content=form,
        title_bar=nv.DefaultTitleBar(title="nv.Row/nv.Column Combination"),
        width="auto",
    )
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
