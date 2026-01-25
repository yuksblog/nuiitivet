# Widget Architecture & Mixin Design

`nuiitivet` の `Widget` クラスは、複数の Mixin を組み合わせた **協調的継承 (Cooperative Multiple Inheritance)** パターンを採用しています。
各 Mixin は単一責任の原則に基づき、特定の機能（ライフサイクル、レイアウト、入力など）を担当します。

See also: [WIDGET_INTERNAL_STATE_ACCESS.md](WIDGET_INTERNAL_STATE_ACCESS.md)

## Internal State Access

Internal state ownership is defined by mixin responsibility. Access underscore-prefixed fields only within the owning module.
Across module boundaries, use the public accessors documented in [WIDGET_INTERNAL_STATE_ACCESS.md](WIDGET_INTERNAL_STATE_ACCESS.md).

## Widget vs ComposableWidget

通常、アプリケーション開発者は `ComposableWidget` を使ってビルドツリーを構築します。
一方、上級者などが低レベルの leaf ウィジェットを作成する場合は `Widget` を使います。

- `Widget`
  - `build()` に依存せず、`layout()` / `paint()` / `hit_test()` を中心に振る舞う leaf を作りたい
  - 子の管理は `children`（や専用ストア）で行い、build で subtree を返さない
  - 例: 低レベル描画ウィジェット、入力/レイアウトのプリミティブ

- `ComposableWidget`
  - `build()` を実装して子ツリーを組み立てたい（`build()` は必須、`None` は返さない）
  - `rebuild()` を呼びたい/呼ばれたい
  - `scope()` / `render_scope()` / `invalidate_scope_id()` を使って部分再構築したい
  - `ComposableWidget.build()` は必須で、戻り値は常に `Widget`（`None` は禁止）
  - 例: Page/Route、Overlay、状態に応じて subtree を差し替えるコンポーネント

## 継承構造 (MRO)

`Widget` は leaf-friendly な基底クラスで、`build()` を前提にしません。
`build()` / `rebuild()` / `scope()` を使うウィジェットは `ComposableWidget` を継承します。

Python の MRO (Method Resolution Order) に従い、メソッド呼び出しは上から下へと連鎖します。

```python
class Widget(
    AnimationHostMixin,   # アニメーション
    BindingHostMixin,     # データバインディング (Observable)
    LifecycleHostMixin,   # ライフサイクル (mount/unmount)
    InputHubMixin,        # 入力イベント
    ChildContainerMixin,  # 子要素管理 (children)
    WidgetKernel,         # 基本レイアウト・描画
):
    ...

class ComposableWidget(
  BuilderHostMixin,     # コンポジション (build/scope/rebuild)
  Widget,
):
  ...
```

## 各 Mixin の役割

### 1. Widget (Leaf-Friendly Base)

- **役割**: 各 Mixin を統合する leaf-friendly な基底。
- **責務**:
  - レイアウト/描画/入力/ライフサイクルの土台。
  - `build()` を実行しない（コンポジションは `ComposableWidget` に限定）。

### 2. ComposableWidget (Composition Root)

- **役割**: `BuilderHostMixin` を組み込むための明示的な基底。
- **責務**:
  - `build()` を持つウィジェットを明確に区別する。
  - `build()` は必須で、戻り値は常に `Widget`（`None` は禁止）。
  - `scope()` / `render_scope()` による部分再構築を利用可能にする。

### 3. BuilderHostMixin (Composition)

- **役割**: `build()` メソッドによるウィジェットの構成（コンポジション）を管理する。
- **責務**:
  - `build()` の実行と、生成されたサブツリー (`_built`) の保持。
  - `layout`, `paint`, `hit_test` をオーバーライドし、`_built` が存在する場合はそちらに処理を委譲する。
    - `layout`: `super().layout()` の後に `_built.layout()` を実行。
    - `hit_test`: まず `_built.hit_test()` を試し、ヒットしなければ `super().hit_test()` へ。
    - Higher-level events that target the composed subtree are delegated to `_built` when present (e.g. back navigation via `handle_back_event`).
  - `on_mount` / `on_unmount` で `_built` のライフサイクルを同期させる。

### 4. LifecycleHostMixin (Lifecycle)

- **役割**: アプリケーションとの接続とライフサイクルイベントを管理する。
- **責務**:
  - `mount(app)` / `unmount()` のドライバ実装（再帰呼び出しの起点）。
  - `on_mount` / `on_unmount` フックの提供。
  - `on_dispose` コールバックの管理。

### 5. BindingHostMixin (Reactivity)

- **役割**: データバインディング（Observable）の購読管理。
- **責務**:
  - `bind` / `bind_to` による購読の登録。
  - `on_unmount` での自動的な購読解除（Dispose）。

### 6. AnimationHostMixin (Animation)

- **役割**: アニメーションの管理とフレーム更新要求。
- **責務**:
  - `animate` / `animate_value` メソッドの提供。
  - `invalidate` メソッドによる再描画リクエストの委譲。

### 7. InputHubMixin (Input)

- **役割**: 入力イベントのルーティングとハンドリング。
- **責務**:
  - ポインター、キーボード、フォーカス、スクロールイベントのディスパッチ。
  - `on_click` 等のイベントハンドラ登録。

### 8. ChildContainerMixin (Children)

- **役割**: 直接の子要素リスト（`children`）を管理する。
- **責務**:
  - `children` プロパティの提供。
  - `add_child`, `remove_child` などの操作 API。
  - `ChildrenStore` による子要素の保持。

### 9. WidgetKernel (Base Element)

- **役割**: ウィジェットの物理的な実体と基本動作を提供する基底クラス。
- **責務**:
  - `width`, `height`, `padding` プロパティの管理。
  - `_layout_rect`（レイアウト計算結果）と `_last_rect`（描画結果）の保持。
  - 基本的な `layout`（`_layout_rect` の更新と子要素へのサイズ伝播）。
  - 基本的な `paint`（子要素の描画）。
  - 基本的な `hit_test`（子要素の判定と自身へのヒット判定）。
    - `_built` の存在は知らず、`children` と自身の矩形のみを対象とする。

## 連携フローの例

### mount() の実行フロー

```python
widget.mount(app)
  ↓
LifecycleHostMixin.mount()  # 1. ドライバ起動。app を保持し、on_mount を呼ぶ。
  ↓ self.on_mount()
ComposableWidget (BuilderHostMixin).on_mount() # 2. (Composableのみ) ビルド実行。_built を生成し、マウントする。
  ↓ super().on_mount()
LifecycleHostMixin.on_mount() # 3. ユーザー定義のフック (デフォルトは何もしない)。
  ↓
(LifecycleHostMixin.mount に戻り、children の mount を再帰的に実行)
```

### layout() の実行フロー

```python
widget.layout(width, height)
  ↓
ComposableWidget (BuilderHostMixin).layout()   # 1. (Composableのみ) _built があれば、そちらの layout も呼ぶ。
  ↓ super().layout()
WidgetKernel.layout()                        # 2. 基本実装。children の layout を呼ぶ。
```

## Widget Optimization

To achieve high performance in Python, the framework implements caching and scoping strategies.

### 1. Recompose Scope API

- **Goal**: Minimize the cost of rebuilding widget trees when state changes.
- **Mechanism**:
  - `RecomposeScope` allows wrapping a subtree in a named scope.
  - `ScopeHandle` provides methods (`invalidate()`, `invalidate_scope_id()`) to trigger rebuilds only for that specific scope.
  - Binding invalidations are routed through `_lookup_scope_ids_for_dependency()`, ensuring that only the affected scopes are rebuilt.

### 2. Layout & Dimension Caching

- **Goal**: Avoid redundant layout calculations and parsing overhead.
- **Dimension Cache**:
  - `Dimension` objects (parsed from `SizingLike`) are memoized in `dimension.py`.
  - Reduces the overhead of parsing strings like `"50%"` or `"auto"` repeatedly.
- **Layout Cache**:
  - `LayoutEngine` caches preferred size, inner rect, and child placement results.
  - Caches are keyed by `_layout_cache_token` and dimension signatures.
  - Invalidation is strictly controlled via `_layout_dependencies` and scope updates.

### 3. Paint Cache & Snapshot Reuse

- **Goal**: Reduce Skia drawing commands for static content.
- **Mechanism**:
  - `CachedPaintMixin` allows widgets to render their background/content into a reusable Skia surface.
  - `paint_cache()` context manager handles the recording and playback of these surfaces.
  - `_paint_dependencies` or explicit `invalidate_paint_cache()` calls manage cache invalidation.
  - Hit testing continues to use the authoritative `_last_rect`.
