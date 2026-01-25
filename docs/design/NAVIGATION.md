# Navigation システム設計

このドキュメントは、[docs/design/DECLARATIVE_VS_IMPERATIVE.md](DECLARATIVE_VS_IMPERATIVE.md) の実現に向けた Navigator（画面遷移）の設計書です。

議論の経緯やタスクメモは以下

- [docs/design/archive/DESIGN_OVERLAY_NAVIGATION.md](archive/DESIGN_OVERLAY_NAVIGATION.md)

## 1. アーキテクチャの基本構造

### 1.1 Overlay と Navigator の関係性

#### 方針: 物理構造に基づく分離 + 内部実装の共通化

ユーザー API は物理構造を反映した直感的なものにし、内部は Route/スタック管理を共通化します。

- `Navigator.push()` は「画面を遷移」
- `Overlay.show()` は「最前面レイヤーに表示」

内部実装は、Navigator は `PageRoute` を扱うスタックとして振る舞い、Overlay は内部専用の `_modal_navigator` を持って Dialog/Snackbar を Route として扱います。

```text
┌─────────────────────────────────────┐
│ App                                  │
│                                      │
│  ┌───────────────────────────────┐  │
│  │ Overlay (物理レイヤー)        │  │ ← 常に最前面
│  │  内部: _modal_navigator       │  │
│  │    ├─ DialogRoute             │  │
│  │    └─ SnackbarRoute           │  │
│  └───────────────────────────────┘  │
│                                      │
│  ┌───────────────────────────────┐  │
│  │ Content                       │  │
│  │  ┌──────────────────┐         │  │
│  │  │ Navigator (部品) │         │  │ ← ユーザーが配置
│  │  │  ├─ PageRoute    │         │  │
│  │  │  └─ PageRoute    │         │  │
│  │  └──────────────────┘         │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
```

### 1.2 ルート Navigator の設計

フルスクリーン遷移は一般的なパターンであり、ルート Navigator は実質的に必須と考えます。
App がデフォルトでルート Navigator を提供し、グローバルアクセス API を提供します。

```python
# グローバルアクセス（簡潔、推奨）
Navigator.root().push(...)

# Context ベース（将来の拡張、詳細制御）
Navigator.of(context).push(...)              # 最寄りの Navigator
Navigator.of(context, root=True).push(...)   # ルート Navigator
```

### 1.3 Context Lookup パターン

タブごとに独立した Navigator（タブごとの遷移履歴）を実現するため、`Navigator.of(context)` を実装します。

- 実装は親を辿るだけ
- ルート Navigator は `Navigator.root()` により O(1) で取得でき、頻出ケースを簡潔・高速にします

```python
class Widget:
    def find_ancestor(self, widget_type: type["T"]) -> "T | None":
        """Find the nearest ancestor of the specified type."""
        current = self._parent
        while current is not None:
            if isinstance(current, widget_type):
                return current
            current = current._parent
        return None


class Navigator(Widget):
    _root_navigator: "Navigator | None" = None

    @classmethod
    def root(cls) -> "Navigator":
        """Get the root navigator."""
        if cls._root_navigator is None:
            raise RuntimeError("No root navigator found.")
        return cls._root_navigator

    @classmethod
    def of(cls, context: Widget, root: bool = False) -> "Navigator":
        """Find the nearest Navigator in the widget tree."""
        if root:
            return cls.root()

        navigator = context.find_ancestor(Navigator)
        if navigator is None:
            raise RuntimeError(
                "No Navigator found in the widget tree above "
                f"{context.__class__.__name__}. "
                "Did you forget to wrap your widget in a Navigator?"
            )
        return navigator
```

### 1.4 ViewModel 向け Interface（Protocol）

ViewModel が `Navigator` の実装詳細に依存しなくて済むように、`INavigator` を提供します。

```python
from __future__ import annotations

from typing import Any, Protocol


class INavigator(Protocol):
    def push(self, content: Any) -> None:
        ...

    def pop(self, result: Any | None = None) -> None:
        ...
```

## 2. Intent System の設計（Navigation 観点）

### 2.0 Intent System とは

Intent System は、画面遷移を「Widget/Route を直接渡す」だけでなく、Intent（意図）を表すデータとして宣言し、フレームワーク側で Route に解決して実行するための仕組みです。

```python
# 呼び出し側（意図）
Navigator.root().push(ProductDetailIntent(product_id=123))

# フレームワーク側（解決）
# - type(intent) をキーに routes から factory を引く
# - factory(intent) により Route を生成する
```

### 2.1 Intent の型システム

Intent は任意の dataclass として定義し、基底クラスや Protocol は不要とします。

```python
from dataclasses import dataclass


@dataclass
class HomeIntent:
    pass


@dataclass
class ProductDetailIntent:
    product_id: int
```

### 2.2 Route マッピング（routes）

`routes` は「Intent instance -> Route」を生成する辞書として扱います。

```python
routes: dict[type, callable[[object], "Route"]] = {
    HomeIntent: lambda intent: PageRoute(builder=lambda: HomeScreen()),
    ProductDetailIntent: lambda intent: PageRoute(
        builder=lambda: ProductDetailScreen(intent.product_id)
    ),
}

Navigator.root().push(ProductDetailIntent(product_id=123))
```

### 2.3 オーバーロード設計（push）

`Navigator.push()` は次の 3 パターンを受け付けます。

- Widget
- Route
- Intent

```python
# パターン1: Widget
Navigator.root().push(SettingsScreen())

# パターン2: Route
Navigator.root().push(PageRoute(builder=lambda: SettingsScreen()))

# パターン3: Intent
Navigator.root().push(SettingsIntent())
```

### 2.4 Intent 不明時の処理

登録されていない Intent を使った場合は RuntimeError を投げ、設定ミスを早期に検知します。

```python
Navigator.root().push(UnknownIntent())
# → RuntimeError: Intent 'UnknownIntent' not found in routes
```

### 2.5 App.navigation(...) 初期化パターン

ViewModel が View（Widget）に依存せずに画面遷移できるようにするため、通常の `App(...)` とは別に `App.navigation(...)` を提供します。これで ViewModel は Intent ベースで遷移を要求できます。

```python
# ナビゲーション付きアプリ
App.navigation(
    routes={
        HomeIntent: lambda intent: PageRoute(builder=...),
        DetailIntent: lambda intent: PageRoute(builder=...),
        SettingsIntent: lambda intent: PageRoute(builder=...),
    },
    initial_route=HomeIntent(),
    title="My App",
)
```

## 3. 戻るボタン（Back Button）のハンドリング

### 3.1 イベント伝播の優先順位

Esc / Back 相当のイベントの既定挙動は次の順序で処理します。

1. 最前面の Overlay を閉じる
2. 最前面の Navigator を pop
3. Root route では何もしない

```python
class App:
    def on_key_pressed(self, event):
        if event.key == "ESCAPE":
            if self._overlay.has_entries():
                self._overlay.close()
                return True

            if self._root_navigator and self._root_navigator.can_pop():
                self._root_navigator.pop()
                return True

            return False
```

### 3.2 Back 連打（連続入力）の扱い

Esc / Back が連続して入力されるケース（キーリピート、連打、OS 側の多重イベント）では、実装側で「戻る要求」を安全に処理できる必要があります。

#### 方針

- `App.handle_back_event()` は 1 回の入力につき 1 回だけ処理を進める
- Overlay が空なら `Navigator.request_back()` のみ
- `Navigator.request_back()` は「ユーザー入力用 API」として、遷移中の re-entrancy を吸収する

#### 工夫（Navigator 側）

- Pop アニメーション中に back が来た場合は、要求をキュー（`pending_pop_requests`）へ積み、現在の pop 遷移を即座に完了させる
- キューを消費する際は、途中の pop はアニメーションを省略し、最後の pop だけ通常の挙動にする
- Push アニメーション中に back が来た場合は、push を即座に完了させたうえで pop を 1 回行う
- `handle_back_event()`（will-pop 相当）がキャンセルを返した場合は、キューを破棄してこれ以上の pop を発生させない

### 3.3 will_pop() Modifier

戻る前の確認などのカスタムハンドリングは Modifier として実装します。

```python
from nuiitivet.modifiers import will_pop

EditScreen().modifier(will_pop(on_will_pop=self._on_will_pop))


async def _on_will_pop(self) -> bool:
    """Return True to continue pop, False to cancel."""
    if self.has_unsaved_changes.value:
        confirmed = await Overlay.root().dialog(
            AlertDialog(
                title=Text("確認"),
                content=Text("保存せずに戻りますか？"),
                actions=[
                    TextButton("キャンセル", on_pressed=lambda: False),
                    TextButton("戻る", on_pressed=lambda: True),
                ],
            )
        )
        return confirmed
    return True
```

### 3.4 Navigator との統合

`Navigator.pop()` の直前で will-pop chain を確認し、キャンセル可能にします。

```python
class Navigator(Widget):
    async def pop(self, result=None):
        if not self.can_pop():
            return

        route = self._routes[-1]
        widget = route.widget

        if hasattr(widget, "_modifier_element"):
            element = widget._modifier_element
            should_pop = await self._check_will_pop(element)
            if not should_pop:
                return

        self._routes.pop()
        route.dispose()
        self.mark_needs_layout()

    async def _check_will_pop(self, element) -> bool:
        if hasattr(element, "handle_back_event"):
            return await element.handle_back_event()
        return True
```
