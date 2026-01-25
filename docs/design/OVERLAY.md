# Overlay システム設計

このドキュメントは、`docs/design/DECLARATIVE_VS_IMPERATIVE.md` の実現に向けた Overlay の設計書です。

Navigation（Navigator / Intent / Back）は `docs/design/NAVIGATION.md` に分冊しました。

議論の経緯やタスクメモは以下

- [docs/design/archive/DESIGN_OVERLAY_NAVIGATION.md](archive/DESIGN_OVERLAY_NAVIGATION.md)
- [docs/design/archive/OVERLAY_SHOW_API.md](archive/OVERLAY_SHOW_API.md)

## 1. アーキテクチャの基本構造

### 1.1 Overlay と Navigator の関係性

#### 方針: 物理構造に基づく分離 + 内部実装の共通化

ユーザー API は物理構造を反映した直感的なものにし、内部は Route/スタック管理を共通化する。

- `Overlay.show()` は「最前面レイヤーに表示」
- `Navigator.push()` は「画面を遷移」（詳細は `docs/design/NAVIGATION.md`）

内部実装は、Overlay が内部専用のスタック（例: `_modal_navigator`）を持ち、表示中の overlay entry（必要なら Route）を管理する。

補足: `Overlay` core は `show()` のみを提供し、シナリオ固有 API（dialog/snackbar 等）はサブクラスに寄せる。

#### 設計意図（分離と共通化）

- ユーザー視点で「どこに描画されるか（物理レイヤー）」が直感的に分かる API にする
  - `Overlay.show()` は常に最前面
  - `Navigator.push()` は画面遷移
- 一方で実装は Route/スタック管理を共通化し、シナリオ別表示（dialog/snackbar/page 等）の実装重複を避ける

上記の「Dialog/Snackbar」は概念例であり、実装上は `Overlay.show()` により生成される overlay entry（Route を含む）として扱う。

```text
┌─────────────────────────────────────┐
│ App                                  │
│                                      │
│  ┌───────────────────────────────┐  │
│  │ Overlay (物理レイヤー)        │  │ ← 常に最前面
│  │  内部: _modal_navigator       │  │
│  │    └─ OverlayEntry/Route      │  │
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

## 2 Overlay API 設計

### 2.1 Navigator と同様のAPI設計

- App がルート Overlay を提供し、グローバルアクセス API を提供する。
- ViewModel が実装詳細に依存しないよう `IOverlay` を提供する。
  - `Overlay.of(context)`: 最寄りの Overlay
  - `Overlay.root()`: ルート Overlay

### 2.2 Overlay core は `show()` のみ

- `Overlay` は汎用の `show()` のみを提供し、シナリオ固有 API（dialog/snackbar/sheet 等）は提供しない。
- `Overlay.show()` は `Widget | Route` のみを受け付ける。
- Intent の解決（Intent -> Widget/Route）は `Overlay` では行わない。
- Intent 解決は `MaterialOverlay` などのサブクラスが `IntentResolver` を用いて提供する。

### 2.3 `Overlay.show()` コア API

`Overlay.show()` は「最前面レイヤーへ表示する」ための最小コア API とする。

```python
def show(
    self,
    content: Widget | Route,
    *,
    passthrough: bool = False,
    dismiss_on_outside_tap: bool = False,
    timeout: float | None = None,
    position: OverlayPosition | None = None,
) -> OverlayHandle[Any]:
    ...
```

#### パラメータ

- `passthrough=False`
  - `False`: Overlay がポインタイベントを消費し、背面への入力をブロックする。
  - `True`: Overlay がイベントを透過し、背面へ入力を通す。
- `dismiss_on_outside_tap=False`
  - `True`: 表示コンテンツ外（outside）のタップで閉じる。
- `timeout: float | None`
  - 秒。
  - `None`: 自動で閉じない。
- `position: OverlayPosition | None`
  - `None` は center と等価。

#### 制約

- `passthrough=True` と `dismiss_on_outside_tap=True` は両立しない（`ValueError`）。

#### Outside-tap の定義

- outside は [BOX_MODEL.md](BOX_MODEL.md) の hit-testing ルールに基づく。
- outside-tap dismissal は「バリア層がポインタイベントを受け取ったときに close する」ことで実現する。
- コンテンツが viewport を覆う場合、outside-tap dismissal は実質的に機能しない。

### 2.4 Positioning: `OverlayPosition` (v1)

v1 は alignment + offset のみを提供する。

- `OverlayPosition.alignment(alignment: str, *, offset: tuple[float, float] = (0, 0))`

`alignment` は [LAYOUT.md](LAYOUT.md) の single-child alignment 語彙に従う。

- `"top-left"`, `"top-center"`, `"top-right"`
- `"center-left"`, `"center"`, `"center-right"`
- `"bottom-left"`, `"bottom-center"`, `"bottom-right"`

`offset` は alignment の後に適用する。

- 単位は px。
- 座標系は overlay root のレイアウト空間。
  - $+x$ は右。
  - $+y$ は下。

### 2.5 `OverlayHandle` / `OverlayResult`

`Overlay.show()` は `OverlayHandle[T]` を返す。

- `handle.close(value)` でその handle が指す entry を閉じる。
- `await handle` は構造化された結果を返す。

```python
class OverlayResult[T]:
    value: T | None
    reason: OverlayDismissReason


class OverlayDismissReason(Enum):
    CLOSED = ...
    OUTSIDE_TAP = ...
    TIMEOUT = ...
    DISPOSED = ...
```

#### Result semantics

- `handle.close(value)` -> `OverlayResult(value=value, reason=CLOSED)`
- outside-tap -> `OverlayResult(value=None, reason=OUTSIDE_TAP)`
- timeout -> `OverlayResult(value=None, reason=TIMEOUT)`
- 明示的な close なしに entry が破棄された -> `OverlayResult(value=None, reason=DISPOSED)`

`await handle` が永久に待ち続けないことを保証する（dispose でも完了させる）。

### 2.6 サブクラス API（MaterialOverlay 等）

シナリオ固有 API はサブクラスに寄せる。

#### MaterialOverlay の責務

`MaterialOverlay` は `Overlay` のサブクラスとして実装し、Material UI 向けの解決とショートカット API を提供する。

- 継承: `MaterialOverlay(Overlay)`
- 取得:
  - `MaterialOverlay.root()` は root overlay が `MaterialOverlay` の場合のみ成功する。
  - `MaterialOverlay.of(context)` は widget tree から最寄りの `MaterialOverlay` を探す。

#### Intent 解決

- `MaterialOverlay.dialog(...)` は `Widget | Route | Any` を受け付ける。
  - `Widget | Route` はそのまま表示する。
  - それ以外は `IntentResolver.resolve(intent)` で `Widget | Route` に解決して表示する。
- `MaterialOverlay` は `intent_resolver` を注入可能。
  - もしくは `intents: Mapping[type[Any], Callable[[Any], Widget | Route]]` を渡す（内部で mapping resolver を構築）。
- 標準 intent をデフォルトで登録する。
  - `AlertDialogIntent`
  - `LoadingDialogIntent`

#### 提供 API (v1)

- `MaterialOverlay.dialog(...)`
  - 既定で背面入力はブロック（`passthrough=False`）。
  - `dismiss_on_outside_tap` は省略可能。
    - `LoadingDialogIntent` は既定で `False`。
    - それ以外は既定で `True`。
- `MaterialOverlay.snackbar(message, *, duration=3.0)`
  - `Snackbar` を用いて実装する。
  - 既定で `passthrough=True`（背面入力をブロックしない）。
  - `timeout=duration` で自動 dismiss。
  - 既定位置は `OverlayPosition.alignment("bottom-center", offset=(0, -24))`。
- `MaterialOverlay.loading(message="Loading...")`
  - `LoadingDialogIntent` を表示し、context manager の exit で必ず close する。

### 2.7 Root overlay の差し替え: `overlay_factory`

Material アプリが root overlay として `MaterialOverlay` を使えるよう、`App` は overlay を注入可能にする。

- `App` / `App.navigation()` は `overlay_factory: Callable[[], Overlay]` を受け取る。
- `overlay_factory` を省略した場合、既定は `Overlay` を生成する。

例:

```python
app = App(
    overlay_factory=lambda: Overlay(),
)
```

```python
app = MaterialApp(
    overlay_factory=lambda: MaterialOverlay(),
)
```

Material の実装では、`MaterialApp` が内部で `overlay_factory` を設定し、必要なら `overlay_routes` を `MaterialOverlay(intents=...)` に渡す。

### 2.8 補足: `Overlay.show()` の範囲

- `Overlay.show()` は intent 登録や標準 dialog/widget の提供責務を持たない。
- 標準 UI（AlertDialog/LoadingDialog 等）や intent は `MaterialOverlay` 側で提供する。

## 3. 非同期処理とライフサイクル

- 全体像（threads × asyncio × UI thread）は [CONCURRENCY_MODEL.md](CONCURRENCY_MODEL.md) を参照。
- 実行基盤（async runtime）とイベントループ統合の詳細は [ASYNCIO_INTEGRATION.md](ASYNCIO_INTEGRATION.md) に集約。
- Overlay の責務としては、`await handle` がハングしないことを保証する。
  - entry が明示的に close されずに除去された場合でも、`OverlayDismissReason.DISPOSED` で完了する。
  - `OverlayResult.reason` を見て呼び出し側が分岐する。

## 4. Z-Index と描画順序

### 4.1 描画順序の設計

挿入順序による描画順序制御（後から追加されたものが上）を採用し、明示的な z-index は不要とする。

#### 設計意図（描画順序）

- z-index の数値管理は複雑さを増やす割に初期要件では不要（YAGNI）
- 「後から開いたものが上」という時系列の直感に一致し、Flutter とも整合する

```python
class Overlay(Widget):
    def __init__(self):
        self._entries: list[OverlayEntry] = []

    def _insert_entry(self, entry: OverlayEntry):
        self._entries.append(entry)
        self.mark_needs_layout()

    def build(self, context):
        return Stack(children=[entry.builder() for entry in self._entries])
```

## 5. Back / Navigator との統合

Back ボタンの優先順位や `will_pop` の詳細は `docs/design/NAVIGATION.md` に集約します。

- Overlay 側は「トップの overlay entry を閉じる」責務に集中する。
- `Overlay.close(...)`（topmost を閉じるショートカット）を提供する。

## 未決事項 / 今後の検討事項

以下は、この正本では結論を固定しない（または実装・検証が必要な）項目です。

### Async / Runtime

- Current behavior is defined in `docs/design/ASYNCIO_INTEGRATION.md`.
- `asyncio.CancelledError` のハンドリング戦略
- Future のキャンセル通知の実装方法
- エラーログの出力方針（ユーザーに見せるべきか）
- UI イベントから coroutine をどう起動するか（実行基盤との統合）

### ViewModel / Dispose

- `CompositeDisposable` などのヘルパー提供
- ViewModel のライフサイクル管理パターンの整理
- ViewModel を自動的に dispose する仕組み
- ViewModel と Widget の関係性のベストプラクティス
- 既に dispose された Widget への操作の防御
- dispose 後の状態フラグ管理
- dispose の二重呼び出し防止

### Rendering / Overlay

- Scoped Overlay
  - 描画順序（App Overlay より下か上か）
  - Scoped Overlay 間の順序制御
- z-index を将来的に導入する場合の設計
- 互換性の維持（既存コードが動作し続けること）
- Overlay が多数ある場合の描画最適化
- 非表示 Overlay の描画スキップ

### Back Button / Events

Back Button / Events の詳細は `docs/design/NAVIGATION.md` を参照。

### Documentation / Prototype

- Intent System の基本設計の確定
- Context Lookup の実装方法の検討
- 非同期処理の実現方法の検討
- Z-Index 管理の実装方法の検討
- クラス図とシーケンス図の作成
- API リファレンスの下書き
- 実装タスクの優先順位付けとチケット化
- 最小限の機能でプロトタイプを作成し、問題点を洗い出す
- フィードバックを元に設計を見直す
