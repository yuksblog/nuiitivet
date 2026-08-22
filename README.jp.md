# Nuiitivet

![Nuiitivet showcase](docs/assets/readme_hero_showcase.gif)

**AI friendly Desktop UI framework for Python.**

[![PyPI version](https://img.shields.io/pypi/v/nuiitivet)](https://pypi.org/project/nuiitivet/)
[![Python versions](https://img.shields.io/pypi/pyversions/nuiitivet)](https://pypi.org/project/nuiitivet/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)

> **English README is [here](README.md).**

```python
login_form = nv.Column(
    [
        nv.TextField(value="", label="Username", width=300),
        nv.TextField(value="", label="Password", width=300),
        nv.Button("Login", on_click=lambda: print("Login clicked"), width=300),
    ],
    gap=20,
    padding=20,
)
```

![Login form](docs/assets/readme_login_form.png)

---

## Nuiitivet はどんなフレームワークか

LLM の登場で、アプリを作るハードルは下がりました。Nuiitivet は、**AI と組んでデスクトップアプリを作る**ことに特化したフレームワークです。

単にLLMにコードを書かせるだけでなく、人間とAIが一緒に作るための開発ループを提供します。
ホットリロード、デブブリッジ、インスペクトモード — これらを組み合わせることで、**書いたコードがすぐ画面になり、その画面についてあなたとアシスタントが会話でき、素早く修正できる**、という一周のループが実現します。
コードジャンプも組み込まれているので、AI が書いたコードをその場で読んで引き取ることもできます。

そして引き取ったコードが読めるものであるように、書き方は Flutter をはじめとする各フレームワークの書きやすいところを取り入れています。

また、デスクトップを前提にしているので、**ReactiveProperty ライクな状態管理**、**マルチスレッドと UI スレッドへのディスパッチ**、**実行ファイルにして配布する**、といったデスクトップ固有の問題への答えが揃っています。
ただし、デスクトップアプリに必要なものが全部揃っているわけではありません。足りていないものは [5. 現時点の制約](#5-現時点の制約) に正直に並べてあります。

---

## 1. AI と組んで作る

AI にコードを書かせること自体は、どのフレームワークでもできます。Nuiitivet が持っているのは、その先のループです。順に見ていきます。

すべて、開発用のランナーで起動したときに有効になります。

```bash
python -m nuiitivet.dev run app.py
```

### 1.1 ひとつの動くウィンドウを、二人で見る

保存するたびに、ウィンドウが**その場で**作り直されます。再起動はありません。そして `Observable` が持っている状態は**生き残ります** — 12 回クリックしてたどり着いた画面が、保存のたびに消えることはありません。

VSCode の **F5** デバッグセッションを張ったままでも、リロードは通ります。ブレークポイントは残ります。

### 1.2 アシスタントが、見て、操作できる

デブランナーは MCP サーバーを一緒に立ち上げます。アシスタントは動いているアプリに対して、こういうことができます。

- **見る** — ウィジェットツリー、その裏にある `Observable` の生の値、スクリーンショット
- **操作する** — クリック、入力、スクロール、キー送出。ターゲットは座標ではなく `key` / `label` で指定するので、レイアウトが変わっても壊れません
- **待つ** — 非同期処理の完了を、レースせずに待つ
- **読む** — リロードの成否、あなたが取った UI 操作、アプリのログと握り潰された例外

とくに効くのが「値は更新されたのに UI が変わらない」という類のバグです。ツリーと状態を**同じ形**で並べて取れるので、どちら側の問題かが一発で分かります。

### 1.3 あなたが「ここ」と指す

言葉で場所を指すのは難しい。とくに `key` も特徴的なテキストも持たない内側のウィジェットと、**何も描かれていない隙間**は、文章ではほぼ指せません。

`Ctrl+Shift+C`（macOS では `Cmd+Shift+C`）でインスペクトモードに入り、**クリックでウィジェットを、ドラッグで領域を**指定します。指定したものには番号バッジが付き、アシスタントにも同じ番号が見えます。「2 番目のやつを直して」が、そのまま通じます。

### 1.4 スキルが、流儀を守る

ここは正直に書きます。**AI は Nuiitivet を知りません。** 学習データに十分な量がないからです。しかも見た目が Flutter / SwiftUI / Compose / Rx に似ているので、放っておくと**他所の書き方を持ち込みます** — `SizedBox` で包もうとしたり、`setState` を探したり。

同梱の 2 つのスキルは、そのためにあります。

- **`nuiitivet-app`** — 書き方を Nuiitivet の流儀に保つ。リンタ同梱
- **`nuiitivet-debug`** — アプリの起動とデブブリッジの使い方を教える。スクリーンショットを浪費する前にツリーを見る、といった節約も含めて

ただ、教えたところで気に入らない結果は出ます。そのときの話が次です。

### 1.5 あなたが引き取る

インスペクトモード中の **`Ctrl+Click`** で、**そのウィジェットを組み立てているコードが、エディタで開きます。**

VS Code はそのまま動きます。他のエディタは URL スキームを渡してください。

```bash
python -m nuiitivet.dev run app.py --editor "cursor://file{file}:{line}:1"
```

これが Nuiitivet の考える「直感的」の、いまの姿です。AI に全部を任せるのでも、全部を手で書くのでもなく、**画面を見て、気になった場所を指して、そのままコードに降りて自分で直す。** 慣れた人ほど、説明するより直した方が速い場面があります。

そのためには、飛んだ先が読めるものである必要があります。

Flutter 風に書くと、装飾のためのネストが積み上がります。

```python
# ネストが深くなっていく
Padding(
    padding=EdgeInsets.all(12),
    child=SizedBox(
        width=200,
        child=Text("Hello"),
    ),
)
```

Nuiitivet では、パラメータです。

```python
nv.Text("Hello", padding=12, width=200)
```

装飾や振る舞いは、包むのではなく **modifier** として貼り付けます。`|` で自然につながります。

```python
nv.Button("OK").modifier(
    nv.tooltip("Submit") | nv.clickable(...) | nv.background("#2196F3")
)
```

![Modifier](docs/assets/readme_modifier.png)

そして `on_click()` のようなイベントハンドラは、宣言的ではなく**手続き的**に書きます。ダイアログを出して、結果で分岐して、という処理は、手続きとして書くのが自然だからです。

```python
def handle_increment(self):
    print(f"Current count: {self.count.value}")
    self.count.value += 1
    if self.count.value % 10 == 0:
        print("Milestone reached!")
```

**ロジックから UI へは宣言的に。UI からロジックへは手続き的に。**

この設計は元々、人間が書きやすいからという理由で選ばれたものです。AI と一緒に書くようになって、もう一つの意味が出てきました。**浅ければ、AI が書いたものをあなたがその場で把握できて、そのまま引き取れる。**

（AI 側の利点は、正直に言えば控えめです。同じ画面をより少ないトークンで表せることと、`padding=12` の書き換えがラッパーの追加より**書き換え面積が小さい**こと。それだけです。深いネストが AI に理解できないわけではありません。）

---

## 2. デスクトップアプリに特化する

ここからは、WPF や WinForms でデスクトップアプリを書いてきた人に向けた話です。

先に正直なところを書きます。**Nuiitivet はデスクトップ特化を目指していますが、まだその途中です。** ファイルダイアログもメニューバーもタスクトレイもありません（[5. 現時点の制約](#5-現時点の制約)に全部並べてあります）。

それでも「デスクトップに特化する」と言えるだけのものは、もう揃っていると考えています。

- **ReactiveProperty ライクな状態管理** — WPF で MVVM を書いてきた人が、そのまま持ち込める
- **マルチスレッドと UI スレッドへのディスパッチ** — 重い処理をローカルで走らせる、というデスクトップ固有の問題への答え
- **実行ファイルにして配れる**

順に説明します。

### 2.1 ReactiveProperty ライクな状態管理

`Observable` に値をセットすると、それに結び付いた UI が**勝手に**追従します。ウィジェットに値を押し込むコードを、あなたが書くことはありません。

```python
class CounterApp(nv.ComposableWidget):
    def __init__(self):
        super().__init__()
        self.count = nv.Observable(0)

    def increment(self):
        self.count.value += 1

    def build(self):
        return nv.Column(
            [
                nv.Text(self.count),          # 直接束ねる
                nv.Button("Increment", on_click=self.increment),
            ]
        )
```

![Counter](docs/assets/readme_counter.png)

`build()` の中に書くのは、UI の宣言だけです。状態と UI が食い違うことがないのは、**状態が UI の唯一の真実**だからです。ViewModel パターンを使えば、メソッド単位ではなくクラス単位で分離できます。**MVVM は、そのまま通じます。**

複数の値から導かれる状態は、計算式として宣言できます。WPF の `ReadOnlyReactiveProperty` に当たるものです。

```python
# total は「a + b」であると宣言する。a か b が変われば自動で再計算される
self.total = self.count_a.combine(self.count_b).compute(lambda a, b: a + b)
```

そして Rx 的なオペレータを挟んで、結果をそのまま UI に束ねられます。

```python
# 入力が 0.3 秒止まってから検索。打ち直されたら前の結果は捨てる
self.results = self.query.debounce(0.3).switch_map(self._search, initial=[])
```

`switch_map` に渡した関数は **UI スレッドの外**で走るので、検索中も画面は描き続けます。`build()` の側は、これが非同期だと知りません。ただの `Observable` として束ねるだけです。

`map` / `combine` / `compute` / `debounce` / `throttle` / `filter` / `switch_map` と、非同期・スレッド周りの詳細は [State Management ガイド](docs/guide/state-management/index.md) にまとめてあります。

### 2.2 重い処理は、あなたの機械で走る

これはデスクトップ固有の問題です。Web アプリなら重い処理はサーバーの中にいるので、そもそも起きません。10 万行の CSV 取り込みは、UI スレッドで走らせれば画面が固まり、ワーカースレッドで走らせれば今度は結果を UI スレッドに渡す必要が出てきます。

Nuiitivet では、**ワーカースレッドからの `Observable` への書き込みは、自動で UI スレッドに載せ替えられます。** マーシャリングのコードを手で書くことはありません。

進捗の報告、件数が判明するまでの不定進捗、`CancelToken` によるキャンセル、途中で画面を離れたとき、ワーカーが例外を投げたとき — 一通りの答えが揃っています（[Background Work](docs/guide/state-management/background_work.md)）。

### 2.3 実行ファイルにして配る

PyInstaller と Nuitka の手順を用意しています。Python の入っていない機械にも、実行ファイルひとつで配れます。

---

## 3. はじめる

### 3.1 動作要件

- Python 3.10 以上
- macOS / Windows / Linux

描画に使っている主なライブラリ: pyglet, PyOpenGL, skia-python, materialyoucolor
（サードパーティライセンスは [LICENSES/](LICENSES/) を参照してください）

### 3.2 インストール

```bash
pip install 'nuiitivet[mcp]'
```

uv なら、`[mcp]` は開発時だけあればよいので dev に分けます:

```bash
uv add nuiitivet
uv add --dev 'nuiitivet[mcp]'
```

`[mcp]` は[デブブリッジ](docs/guide/ai_pair_programming/dev_bridge_mcp.md)の MCP サーバーが使う追加依存です。アプリを動かすだけなら `nuiitivet` 単体で足りますが、AI と組んで開発するなら実質必須なので、最初から入れておくのがおすすめです。

### 3.3 最初のアプリ

- `import nuiitivet.material as nv` でデザインシステムごと読み込む
- `ComposableWidget` を継承して UI 部品を作る
- `App` に渡して起動する

```python
import nuiitivet.material as nv


class CounterApp(nv.ComposableWidget):
    def __init__(self):
        super().__init__()
        self.count = nv.Observable(0)

    def handle_increment(self):
        self.count.value += 1

    def build(self):
        return nv.Column(
            [
                nv.Text(self.count),
                nv.Button("Increment", on_click=self.handle_increment),
            ],
            gap=20,
            padding=20,
        )


def main():
    # クラスをそのまま渡す（ファクトリなので、ホットリロードが作り直せる）
    app = nv.App(content=CounterApp)
    app.run()


if __name__ == "__main__":
    main()
```

### 3.4 開発ループに入る

普通に `python app.py` でも動きますが、開発中はデブランナーを使ってください。ここまで書いてきたもの — ホットリロード、デブブリッジ、インスペクトモード、コードジャンプ — が全部これで有効になります。

```bash
python -m nuiitivet.dev run app.py
```

詳しくは [AI ペアプログラミング](docs/guide/ai_pair_programming/index.md) を参照してください。

## 4. ドキュメント

設計の詳細は **[ドキュメントサイト](https://yuksblog.github.io/nuiitivet/)** にあります。
動くサンプルは **[samples/](samples/)** に。この README に出てくるコードは [samples/readme/](samples/readme/) に実行可能な形で置いてあります。

### 中核となる概念

| ガイド | 内容 |
| --- | --- |
| [Layout](docs/guide/layout/index.md) | ウィジェットとパラメータで UI を組む |
| [State Management](docs/guide/state-management/index.md) | `Observable` によるリアクティブな状態管理 |
| [Modifiers](docs/guide/modifiers/index.md) | 装飾と振る舞いをウィジェットに貼り付ける |
| [UI Design System](docs/guide/design-system/index.md) | テーマとデザイントークン |

### 画面を作る

| ガイド | 内容 |
| --- | --- |
| [Overlay](docs/guide/overlay/index.md) | ダイアログ、ローディング、オーバーレイ |
| [Navigation](docs/guide/navigation/index.md) | 画面遷移とルーティング |
| [Window & Chrome](docs/guide/window/index.md) | ウィンドウのサイズ・位置と、自前で描くクローム |

### Material Design

| ガイド | 内容 |
| --- | --- |
| [Material App](docs/guide/design-system/material_app.md) | アプリの起点と構造 |
| [Material Theme](docs/guide/design-system/material_theme.md) | シードカラーから生成するカラースキーム |
| [Material Widgets](docs/guide/design-system/material_widgets.md) | 組み込みウィジェット一覧 |

### さらに先へ

| ガイド | 内容 |
| --- | --- |
| [Concurrency](docs/guide/concurrency.md) | 並行処理の選び方と、バックグラウンドからの安全な UI 更新 |
| [AI pair-programming](docs/guide/ai_pair_programming/index.md) | 開発ループ、デブブリッジ、スキル |
| [Packaging](docs/guide/packaging.md) | ユーザーに配布する |

## 5. 現時点の制約

制約には 2 種類あります。**設計に根ざしていて簡単には変わらないもの**と、**単にまだ作っていないもの**です。採用を検討するうえで意味が違うので、分けて書きます。

### 設計に根ざした制約

- **ディスプレイが必要です。** `App.run()` は OS のウィンドウを開くため、ディスプレイのない完全なヘッドレス環境では動きません。
- **GPU は推奨であって必須ではありません。** 既定では OpenGL / GPU コンテキストを使いますが、GPU がない環境やリモート環境では CPU ラスタライズにフォールバックします。明示的に選ぶこともできます（[Renderer Selection](docs/guide/window/renderer_selection.md)）。

### まだ作っていないもの

デスクトップ特化を名乗るには、これだけ足りていません。技術的に不可能なわけではなく、手が回っていないだけです。いずれも Issue に登録済みです。

- ファイルダイアログ（開く / 保存）
- OS からのファイルドロップ
- メニューバー
- デスクトップ通知
- タスクトレイアイコン
- マルチウィンドウ
- OS アクセシビリティ対応（スクリーンリーダーや VoiceOver への対応）

## 6. ライセンス

Apache License 2.0 です。詳細は [LICENSE](LICENSE) を参照してください。
