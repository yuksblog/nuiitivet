# Error handling

## Error handling policy

フレームワーク全体で発生する例外が `try/except: pass` で握りつぶされ、原因追跡が困難になる状態を避ける。

- "黙って消える失敗" を減らす
- 例外の扱いを一貫した方針で運用できるようにする
- ログ爆発を防ぎつつ、スタックトレースを残す

### Boundary vs internal (境界/内部)

本書は例外の扱いを「境界/内部」の 2 役割に分ける。

- 境界（外周）
  - OS/バックエンドからフレームワーク内部へ入る入口
  - 例外の扱いを確定させる
    - log + 継続に変換 / fail fast
    - raise
- 内部（実装詳細）
  - 境界から呼ばれる、描画/レイアウト/ツリー操作/購読などの処理本体
  - 例外を握りつぶさず境界へ伝播させる

## Processing categories (処理種別)

### Startup / initialization (起動・初期化)

アプリ起動、バックエンド初期化、必須リソース解決など「開始に失敗したら継続不能」な区間。

- 原則: raise（fail fast）
- 例外: 補助的機能の初期化で、失敗しても継続可能な場合は log + フォールバック

### Event input (イベント入力)

OS/バックエンドから届く入力（クリック、キー、ナビゲーション、フォーカス等）をアプリへ配送する区間。

- 原則: 境界（入力配送の外周）で捕捉し、log して次のイベントへ継続

### Rebuild (状態更新・合成)

イベント/タイマー等を受けて状態を更新し、UI ツリーを再構築・差分反映する区間。

- 原則: 境界で捕捉し log、可能なら当該 subtree/処理単位をスキップして継続

### Rendering / frame update hot path (描画・フレーム更新)

フレーム単位で反復し、描画やレイアウト、アニメーション更新を行う区間。

- 原則: フレーム境界で捕捉し log（同一事象は 1 回だけ）
- 当該フレームは安全に落として次フレームへ

### Subscriptions / callbacks (購読・コールバック)

利用者提供のコールバック、購読通知、非同期タスク完了通知など「外部コードを呼ぶ」区間。

- 原則: 呼び出し元（購読通知/コールバック実行の外周）で捕捉し log、購読を止めない
- 例外: 明示的なキャンセル/終了（CancelledError 相当）は ignore または DEBUG

### Repository mapping examples (本リポジトリでの対応付け例)

境界（外周）の例。

- エントリポイント: `src/__main__.py`
- App 実行境界: `nuiitivet.runtime.app.App.run` と、その周辺のフレーム駆動（例: `_render_frame`）
- バックエンド境界: `nuiitivet.backends.pyglet.runner.run_app` の `@window.event` ハンドラ（`on_draw` / `on_mouse_*` / `on_key_*` 等）
- イベントループ境界: `nuiitivet.backends.pyglet.event_loop.ResponsiveEventLoop.run` / `_perform_draw`
- 入力配送の外周: `nuiitivet.runtime.app_events.dispatch_*`

内部（実装詳細）の例。

- ツリー/合成: `nuiitivet.widgeting.*`
- レイアウト/スクロール: `nuiitivet.layout.*` / `nuiitivet.scrolling.*`
- 描画: `nuiitivet.rendering.*`
- アニメーション: `nuiitivet.animation.*`
- テーマ/色: `nuiitivet.theme.*` / `nuiitivet.colors.*`
- 観測/購読: `nuiitivet.observable.*`
- ウィジェット実装: `nuiitivet.widgets.*`（利用者提供コールバックを呼ぶ箇所は「購読・コールバック」に該当）

## Logging policy

### Exception logging

- 例外は `logger.exception(...)` を使用してスタックトレースを残す
- `logger.exception(...)` は、例外を捕捉して継続に変換する「境界」でのみ行う

### Avoid duplicate stack traces

- 内部は原則として `logger.exception(...)` を呼ばない
- 内部で捕捉が必要な場合は、コンテキスト付与（メッセージ整形、例外のラップ等）をして再送出する

### debug_once / exception_once

ログ爆発を防ぐため、同一事象は 1 回だけ出す仕組みを導入する。

- Key design
  - `category`（例: render/event/subscription） + `site`（例: 関数名 or 論理的な発火点名） + 例外型名
  - メッセージ全文をキーに入れない
- Capacity
  - 既定で最大 N 件（例: 1024）
  - 超過時は古いキーから破棄（LRU 等）
- Thread-safety
  - UI スレッド以外から呼ばれ得る場合、内部状態更新はスレッドセーフにする

### Default logger behavior

- フレームワークは `logging.getLogger("nuiitivet")`（または配下）を使用する
- logging 設定は利用者に委ね、ドキュメントで推奨設定を提示する
  - フレームワークは logging の設定（`basicConfig` やハンドラ追加）を行わない
  - `nuiitivet` ロガーのレベルの推奨設定は WARNING とする

例: `logging.yaml`

```yaml
version: 1
disable_existing_loggers: false

formatters:
  standard:
    format: "%(asctime)s %(levelname)s %(name)s: %(message)s"

handlers:
  stderr:
    class: logging.StreamHandler
    level: WARNING
    formatter: standard
    stream: ext://sys.stderr

loggers:
  nuiitivet:
    level: WARNING
    handlers: [stderr]
    propagate: false

root:
  level: WARNING
  handlers: [stderr]
```
