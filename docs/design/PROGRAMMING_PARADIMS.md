# Programming paradims

## 1. Basic Philosophy

nuiitivetの目的は、開発者にとって **「直感的であること (Intuitive)」** であることを重視している。
UI開発における「直感」とは、メンタルモデルとコードが一致している状態を指します。

この目的を達成するために、nuiitivetは単一のパラダイムに固執せず、バランスよく組み合わせるアプローチを採用します。

1. **宣言的UI**
    * WidgetツリーやModifierの構築は、宣言的に記述します。
    * *Why*: 「画面に何が表示されているか」という静的な構造は、宣言的な記述が最も直感的で可読性が高いため。

2. **Data Binding**
    * 状態と表示の同期は、Observableによるデータバインディングで、宣言的に記述します。
    * *Why*: 「データが変われば表示も変わる」という因果関係は、リアクティブな仕組みに任せるのが最も自然で、整合性を保ちやすいため。

3. **Event Handler**
    * ボタンクリック時などのイベント時の処理は、イベントハンドラ内で命令的に記述します。
    * *Why*: 「ユーザーが操作したら、次に何が起きるか」という時間の流れ（フロー）は、手続き的に記述するのが最も直感的で、デバッグも容易なため。

## 2. UIコンポーネントの制御 (UI Component Control)

UIコンポーネントの中には、宣言的（構造）と命令的（フロー）の境界線が曖昧なものが存在します。それぞれのケースに対する推奨アプローチを以下に示します。

### 2.1 ダイアログ (Dialog)

* **課題**: UI構造の一部だが、ユーザーとの「会話（フロー）」という時系列の性質を持つ。
* **解決策**: **宣言的定義 + 命令的表示 (Declarative Definition + Imperative Display)**
  * 定義はWidgetとして宣言的に行う。
  * 表示は `await` を用いて命令的に行い、結果を受け取る。

#### Dialog: 基本的な使い方 (View Only)

```python
# イベントハンドラ内で await を使用して結果を待つ
result = await Overlay.dialog(
    child=AlertDialog(
        title=Text("Confirm"),
        content=Text("Are you sure?"),
        actions=[
            TextButton("Yes", on_click=lambda: Overlay.pop(True)),
            TextButton("No", on_click=lambda: Overlay.pop(False)),
        ]
    )
)
if result:
    do_something()
```

#### Dialog: ViewModelで実施する場合

ViewModelは具体的なWidgetを知るべきではないため、IntentやServiceインターフェースを使用します。
`Overlay` はアプリのルートコンテンツとは独立したレイヤーとして定義し、`App` 初期化時に渡します。

##### 1. 標準のダイアログを使用する場合

フレームワークは標準的な Dialog Widget（`AlertDialog` 等）を提供し、標準 Dialog Intent をデフォルトで利用可能にする。

ViewModel は Widget を直接生成せず、`IOverlay` のような抽象インターフェースに対して Intent を発行する。
具体的な Widget の生成は View 層（`dialogs` の設定）に委譲されるため、利用側は標準的な見た目のダイアログを再利用できる。

```python
class MyViewModel:
    def __init__(self, overlay: IOverlay):
        self.overlay = overlay

    async def on_error(self, error_msg):
        await self.overlay.dialog(AlertDialogIntent(title="エラー", message=error_msg))
```

##### 2. カスタムダイアログを使用する場合

独自のレイアウトを持つダイアログを表示したい場合は、カスタムIntentを定義し、`Overlay` に登録します。

```python
# 1. Custom Intent (Data Class)
@dataclass
class ConfirmIntent:
    title: str
    message: str

# 2. App Initialization (Overlay Setup)
if __name__ == "__main__":
    # Overlayレイヤーの定義
    overlay = Overlay(
        # Intent を登録（標準 Intent はデフォルトで利用可能）
        dialogs={
            ConfirmIntent: lambda intent: DialogRoute(
                builder=lambda: AlertDialog(
                    title=Text(intent.title),
                    content=Text(intent.message),
                    actions=[
                        TextButton("OK", on_click=lambda: overlay.close(True)),
                        TextButton("Cancel", on_click=lambda: overlay.close(False))
                    ]
                ),
                barrier_dismissible=True,
                barrier_color=Colors.black54
            )
        }
    )
    # ... Appの起動処理 ...

# 3. ViewModel Usage
class MyViewModel:
    # ...
    async def on_delete(self):
        # カスタムIntentの使用
        if await self.overlay.dialog(ConfirmIntent("確認", "本当に削除しますか？")):
            self.delete_item()
```

このパターンにより、`Navigator` と `Overlay` の使い方が統一され、ViewModel の実装が一貫性のあるものになります。

### 2.2 スナックバー (Snackbar/Toast)

* **課題**: 一時的なフィードバックであり、UI構造というよりは「通知」。
* **解決策**: **命令的 Fire & Forget**
  * 結果を待つ必要がないため、単純なメソッド呼び出しとして扱う。

#### Snackbar: 基本的な使い方 (Material)

```python
MaterialOverlay.root().snackbar("Saved successfully!")
```

#### Snackbar: ViewModelで実施する場合

Material を前提とする場合、ViewModel は `MaterialOverlay`（もしくはそれに準ずる抽象）を受け取り、snackbar を発火できます。

```python
# ViewModel
class MyViewModel:
    def __init__(self, overlay: MaterialOverlay):
        self.overlay = overlay

    def on_save_complete(self):
        self.overlay.snackbar("Saved successfully!")
```

### 2.3 ツールチップ (Tooltip)

* **課題**: 一時的な表示だが、特定のUI要素に強く紐づく属性。
* **解決策**: **完全宣言的 (Fully Declarative)**
  * Widgetのラッパーとして記述する。

#### Tooltip: 基本的な使い方 (View Only)

```python
Tooltip(
    message="Click to edit",
    child=IconButton(icon=Icons.edit, ...)
)
```

## 3. 画面遷移のパターン (Navigation Patterns)

画面遷移は「状態の変化（宣言的）」とも「ユーザーの移動（命令的）」とも捉えられるため、宣言的／命令的の境界線が特に曖昧になりやすい領域です。
nuiitivetでは、要件の複雑さに応じて以下のパターンを使い分けることを推奨します。

### 3.1 シングルページ・ウィザード (Single Page Wizard)

* **概要**: 1つの画面内で、状態に応じて表示内容を切り替えるパターン。
* **実装**: `Navigator` を使用せず、条件分岐 (`if/else`) や `map` を使用する。
* **用途**: 戻るボタンの履歴に残したくない、密結合なステップ遷移（ウィザード形式など）。

```python
class WizardScreen(Widget):
    def build(self):
        # current_step (Observable) の値に応じて表示するWidgetを切り替える
        return self.vm.current_step.map(lambda step: 
            Step1() if step == 1 else
            Step2() if step == 2 else
            Step3() if step == 3 else
            Step4()
        )
```

### 3.2 並列遷移 (Parallel Navigation)

* **概要**: タブバーやドロワーのように、互いに独立した画面を切り替えるパターン。
* **実装**: `IndexedStack` や `BottomNavigationBar` を使用する。
* **特徴**: 画面の状態（スクロール位置など）は維持されるが、遷移履歴（戻るスタック）は持たない。

```python
class MainScreen(Widget):
    def build(self):
        return Scaffold(
            body=IndexedStack(
                index=self.vm.current_tab_index,
                children=[HomeTab(), SearchTab(), ProfileTab()]
            ),
            bottom_navigation_bar=BottomNavigationBar(...)
        )
```

### 3.3 標準的な遷移 (Standard Navigation)

* **概要**: 一般的な「一覧→詳細」や「ショッピングカート」のような、戻る履歴を持つ遷移パターン。
* **実装**: `Navigator.push()` を使用して命令的に遷移する。
* **特徴**: データ（カートの中身など）はリアクティブに管理しつつ、遷移のタイミング（次へ、戻る）はイベントハンドラで命令的に制御する（Hybridアプローチ）。

```python
# 例: 商品一覧 -> カート -> 注文完了 というフロー

# 1. データは Observable で管理 (Global/Scoped Service)
class CartService:
    items = Observable([])

class ProductListScreen(Widget):
    def on_add_cart(self, product):
        # データ操作はリアクティブに (Serviceの状態を更新)
        cart_service.items.value.append(product)
        
    def on_cart_click(self):
        # 画面遷移は命令的に
        Navigator.push(CartScreen())

class CartScreen(Widget):
    def build(self):
        # 画面内の表示はリアクティブに (Serviceの状態をバインド)
        return ForEach(cart_service.items, ...)

    def on_checkout_click(self):
        # 2. 注文処理を実行 (非同期)
        await self.vm.checkout()
        # 3. 完了画面へ遷移 (現在のカート画面を破棄して入れ替え)
        Navigator.push_replacement(OrderCompleteScreen())

class OrderCompleteScreen(Widget):
    def on_back_to_home_click(self):
        # 4. 最初の商品一覧まで戻る
        Navigator.pop_until(ProductListScreen)
```

### 3.4 Intent駆動の遷移 (Intent-based Navigation)

* **概要**: Standard Navigation を ViewModel から行う場合のベストプラクティス。
* **実装**: ViewModel は「遷移の意図 (Intent)」のみを発行し、具体的な Widget の生成は View 層（Navigatorの設定）に委譲する。
* **メリット**: ViewModel と View の疎結合化、型安全なルーティング、テスト容易性の向上。

```python
# 1. Intent (遷移の意図) を定義
@dataclass
class ProductListIntent: pass

@dataclass
class CartIntent: pass

@dataclass
class OrderCompleteIntent: pass

# 2. ViewModel (具体的なWidgetを知らない)
class CartViewModel:
    def __init__(self, navigator: INavigator):
        self.navigator = navigator

    async def checkout(self):
        await self.service.submit_order()
        # "注文完了画面へ行きたい" という意図だけを伝える
        self.navigator.push_replacement(OrderCompleteIntent())

# 3. View (Navigatorの設定でIntentとWidgetを紐付ける)
Navigator(
    initial_routes=[PageRoute(builder=lambda: ProductListScreen())],
    routes={
        ProductListIntent: lambda _: PageRoute(builder=lambda: ProductListScreen()),
        CartIntent: lambda _: PageRoute(builder=lambda: CartScreen()),
        OrderCompleteIntent: lambda _: PageRoute(builder=lambda: OrderCompleteScreen()),
    }
)
```

### 3.5 ネストされた遷移 (Nested Navigation)

* **概要**: Parallel Navigation と Standard Navigation を組み合わせた、アプリ構造の標準的なパターン。
* **実装**: 各タブ (`Parallel`) の中に、独立した `Navigator` (`Standard`) を配置する。
* **用途**: InstagramやTwitterのように、タブごとに独立した遷移履歴を持ちたい場合。

```python
class MainScreen(Widget):
    def build(self):
        return Scaffold(
            # Parallel Navigation (タブ切り替え)
            body=IndexedStack(
                index=self.vm.current_tab_index,
                children=[
                    # Tab 1: Home (Standard Navigation)
                    # このタブ内での遷移は、このNavigatorが管理する
                    Navigator(
                        key="home_nav",
                        initial_routes=[PageRoute(builder=lambda: ProductListScreen())],
                        routes={
                            ProductListIntent: lambda _: PageRoute(builder=lambda: ProductListScreen()),
                            CartIntent: lambda _: PageRoute(builder=lambda: CartScreen()),
                            # ...
                        }
                    ),
                    # Tab 2: Search (Standard Navigation)
                    Navigator(
                        key="search_nav",
                        initial_routes=[PageRoute(builder=lambda: SearchScreen())]
                    ),
                    # Tab 3: Profile
                    Navigator(
                        key="profile_nav",
                        initial_routes=[PageRoute(builder=lambda: ProfileScreen())]
                    ),
                ]
            ),
            bottom_navigation_bar=BottomNavigationBar(...)
        )
```

### 3.6 宣言的ルーティング (Declarative Routing) - Future Work

* **概要**: URLやディープリンクに基づいて、アプリ全体のナビゲーション状態を決定するパターン。
* **実装**: `Router` が URL を解析し、宣言的に定義されたマッピングに従って `Navigator` を操作する。
* **用途**: Web対応、外部連携、複雑な状態復元。

```python
# アプリ起動時やURL変更時に、URLに基づいてNavigatorのスタックを再構築する
Router(
    routes={
        "/": HomeIntent(),
        "/product/:id": lambda id: ProductDetailIntent(id),
        "/cart": CartIntent(),
    },
    # URL "/product/123" が開かれた場合:
    # 1. HomeIntent -> HomeScreen
    # 2. ProductDetailIntent(123) -> DetailScreen
    # というスタックを自動的に構築し、戻るボタンでHomeに戻れるようにする
    on_intent=lambda stack: Navigator.reset(stack)
)
```

## 4. 関連資料

* [Concurrency & Execution Model](../design/CONCURRENCY_MODEL.md)
* [Navigation](../design/NAVIGATION.md)
* [Overlay](../design/OVERLAY.md)
* [Asyncio Integration](../design/ASYNCIO_INTEGRATION.md)
