# Rendering Pipeline Architecture

本フレームワークの描画パイプラインは、**Build**, **Layout**, **Paint** の3つの主要フェーズで構成されています。
各フェーズは明確に責務が分離されており、特に **Layout-first Architecture** を採用することで、描画前に幾何情報が確定することを保証しています。

## 1. Build Phase

*Status: Implemented (WidgetBuilder, ScopedFragment)*

Widget ツリーの構築と状態変更に伴う差分更新を行うフェーズです。

* **責務**:
  * 宣言的な Widget 定義から、実際の Widget インスタンスツリーを生成する。
  * `Observable` の変更を検知し、影響を受けるスコープ（`ScopedFragment`）のみを再構築（Recomposition）する。
  * この段階では、Widget の親子関係とプロパティは決定されますが、具体的なサイズや位置は未定です。

### Scoped Rendering Optimization

* **Fine-grained Updates**: `render_scope` ブロックを使用して動的な子要素をラップすることで、親の再構築時に高コストな Widget の再生成を防ぎます。
* **Dedicated Scopes**: `ForEach` や `MaterialContainer` などのコア Widget は、リスト項目や装飾コンテンツを分離するために専用のスコープを持っています。
* **Dependency Tracking**: スコープメタデータは各子要素の `_layout_dependencies` / `_paint_dependencies` を記録し、バインディングの無効化を適切にルーティングします。
* **Batching**: バインディングキューとスコープ再構築キューは一緒にフラッシュされ、アンマウントされた Widget は即座に再構築されます。

## 2. Layout Phase

*Status: Implemented (Layout-first Architecture)*

Widget のサイズと位置を決定するフェーズです。Paint の前に必ず実行されます。

### The Layout Protocol

すべての `Widget` は以下のプロトコルに従います。

1. **`layout(width, height)` メソッド**
    * 親 Widget から呼び出され、利用可能なサイズ（制約）を受け取ります。
    * **責務**:
        1. 自身のサイズを決定する（`preferred_size` や `Sizing` 設定に基づく）。
        2. 子 Widget がある場合、それらの `layout()` を呼び出し、サイズと位置を決定する。
        3. 計算結果（自身のサイズ、子要素の相対位置）を `_layout_rect` に保存する。
        4. `_needs_layout` フラグをクリアする。
    * **禁止事項**: 描画コマンドの発行、副作用のある状態変更（レイアウト結果の保存を除く）。

2. **`_layout_rect` プロパティ**
    * `layout()` の計算結果として、親 Widget から見た相対位置とサイズ `(x, y, w, h)` を保持します。
    * `paint()` メソッドはこの値を読み取って描画を行います。

3. **`mark_needs_layout()` メソッド**
    * レイアウトに影響するプロパティ（`width`, `padding`, 子の追加削除など）が変更された場合に呼び出します。
    * 自身の `_needs_layout` フラグを立て、親 Widget へ再帰的に伝播させます。
    * これにより、次回のフレームで必要な部分のみ再レイアウトが行われます。

### Layout Cache & Profiling

* **Sizing Cache**: `parse_sizing()` はメモ化されており、繰り返される width/height リテラルは追加の割り当てなしに `Sizing` オブジェクトに変換されます。
* **Layout Engine Cache**: `LayoutEngine` は、推奨サイズ、内部矩形、子要素の配置結果をキャッシュします。キャッシュキーには、パディング、ボーダー幅、コンテナの `_layout_cache_token`、子トークンなどが含まれます。
* **Invalidation**: パディングやボーダー幅を変更する Widget は `_layout_cache_token` をインクリメントしてキャッシュを無効化します。
* **Profiling**: `enable_layout_cache_profiling()` により、開発者はヒット率を検査して複雑なツリーを最適化できます。

### Lifecycle Integration

`App` のメインループは以下の順序で処理を行います。

1. **Layout Pass**: ルート Widget の `layout()` を呼び出します（`_needs_layout` が True の場合のみ）。
    * この段階で、全 Widget のサイズ、位置、スクロール領域（Metrics）が確定します。
    * スクロールバーの表示判定やヒットテストの正確性が保証されます。

## 3. Paint Phase

*Status: Implemented (Skia integration)*

確定したレイアウト情報に基づいて、実際に画面への描画を行うフェーズです。

* **責務**:
  * `layout()` で計算された `_layout_rect` を使用して、自身と子 Widget を描画する。
  * Skia キャンバスへの描画コマンド発行。
  * クリッピングや座標変換（`save`, `translate`, `restore`）の適用。
* **制約**:
  * この段階でのサイズ計算や配置変更は禁止されています。
  * `paint()` は純粋なコンシューマーであり、レイアウト結果を変更してはいけません。

### Paint Cache Reuse

* **CachedPaintMixin**: 重い描画を行う Widget は `CachedPaintMixin` を使用して、背景レイヤーをオフスクリーン Skia サーフェスにレンダリングします。
* **Cache Invalidation**: `_paint_dependencies` が変更された場合、またはプロパティセッターや Modifier が `invalidate_paint_cache()` を呼び出した場合にキャッシュは破棄されます。
* **Hit Testing**: キャッシュされたレイヤーはヒットテストに影響を与えません。`_last_rect` が唯一の真実のソースであり続けます。
* **Theme Awareness**: ColorRole を参照する Widget は `ThemeManager` を購読し、テーマ変更時にキャッシュを無効化する責務を持ちます。
