# Layout System Design

## Overview

See [BOX_MODEL.md](BOX_MODEL.md) for the single source of truth on rect terminology (allocated/content), hit testing rules, and visual overflow (outsets).

本フレームワークのレイアウトシステムは、Widget ツリー構造そのものによって表現されます。
CSS のような外部スタイルシートや複雑な制約システム（Auto Layout 等）ではなく、プロパティとコンポジションによる直感的な制御を目指しています。

## Core Principles

### 1. Spacing: Padding & Gap (No Margin)

Widget 間の余白制御は `padding` と `gap` のみに統一します。`margin`（外側余白）は使用しません。

* **Padding (内側余白)**
  * すべての Widget は `padding` プロパティを持ちます。
  * 自身のコンテンツと境界線（Border/Background）との間のスペースを制御します。

* **Gap (子要素間の間隔)**
  * 複数の子を持つコンテナ（`Row`, `Column` 等）は `gap` プロパティを持ちます。
  * 子 Widget 同士の間に一定の間隔を挿入します。

* **Flow の 2軸 Gap**
  * 折り返しレイアウト（`Flow`）は、将来的な `direction` 追加を見据えて `main_gap` / `cross_gap` を持ちます。
    * `main_gap`: run 内（主方向）の間隔
    * `cross_gap`: run 同士（交差方向）の間隔
  * 対応関係の目安: CSS の `gap` / `row-gap` / `column-gap`、Flutter の `Wrap(spacing, runSpacing)`。

* **Grid の row/column Gap**
  * 2次元レイアウト（`Grid`）は軸が固定なので、`row_gap` / `column_gap` を持ちます。
    * `row_gap`: 行（Y方向）間の間隔
    * `column_gap`: 列（X方向）間の間隔
  * CSS の `row-gap` / `column-gap` と同じ意図です。

* **Why No Margin?**
  * `margin`と`padding` の両方があると、どちらを使えば良いか混乱します。
  * コンポーネント自身が「外側の余白」を持つことは、コンポーネントの再利用性を損なう原因となります（配置される文脈によって必要な外側余白は変わるため）。
  * 余白が必要な場合は、親コンテナの `gap`、親の `padding`、あるいは透明な `Spacer` Widget を使用して制御します。

### 2. Sizing System

Widget のサイズは `Sizing` 型によって抽象化され、`width` / `height` プロパティで指定します。

#### Sizing Types

* **`fixed(value)`**: 固定ピクセル値。
* **`auto`**: コンテンツの内容に合わせてサイズを決定（Intrinsic size）。
* **`flex(weight=1.0)`**: 親の利用可能な領域（残りのスペース）を埋めます。
  * Flexbox の `flex-grow` に相当します。
  * 複数の `flex` 要素がある場合、`weight` の比率でスペースを分配します。
  * 文字列で `"50%"` のように指定した場合、`flex(50.0)` として解釈されます。
    * 注意: これは「親の50%」という絶対的なサイズではなく、「重み50」として扱われます。兄弟要素がすべて `%` 指定であれば比率通りになりますが、固定サイズの要素が混在する場合は「残りスペース」に対する配分となる点に注意してください。

#### Grid: Room Allocation and Fill

補足: `Grid` の責務は「部屋割り（行/列/エリアと、各セルの allocated rect を決める）」です。
与えられた部屋をどう使うか（intrinsic で置くか、いっぱいに埋めるか）は子 Widget の `width` / `height`（`Sizing`）で決めます。

例: セルを埋めたい場合は `Sizing.flex(1)` を明示します。

```python
cell = MaterialContainer(
    Text("Cell"),
    width=Sizing.flex(1),
    height=Sizing.flex(1),
)
```

#### The `size` Parameter (Specific Widgets)

`Icon` や `Checkbox` など、正方形であることが本質的な Widget では、初期化パラメータとして `size` を提供します。

* **Purpose**: アスペクト比（1:1）を強制し、`width` と `height` の不整合を防ぐために使用します。
* **Behavior**:
  * 初期化時に `size` を受け取り、内部的に `width` と `height` の両方に同じ値を設定します。
  * これらの Widget は通常、コンストラクタで個別の `width` / `height` 引数を受け付けません。

### 3. Alignment: Parent's Responsibility

配置（Alignment）は、子 Widget 自身ではなく「親 Widget」の責務です。

#### Single Child Container

単一の子を持つ Widget（`Container` 等）は `alignment` プロパティを使用します。

* **Values**
  * 9点配置
    * `top-left`, `top-center`, `top-right`
    * `center-left`, `center`, `center-right`
    * `bottom-left`, `bottom-center`, `bottom-right`

補足: alignment は「配置位置」だけを決めます。サイズを埋めたい場合は `width` / `height`（例: `Sizing.flex(...)`）で指定します。

Note: `alignment` という用語は文脈によって意味が異なります。
CSS 系（Web）の `align-*` / `justify-*` には “stretch（余剰スペースをサイズで吸収する）” の概念が含まれることがありますが、
本フレームワークでは GUI 系の考え方を採用し、alignment は一貫して「配置のみ」です。

#### Multi Child Container

複数の子を持つ Widget（`Row`, `Column` 等）は Flexbox ライクな配置制御を使用します。

* **`main-alignment` (主軸方向)**
  * `start`, `center`, `end`
  * `space-between`, `space-around`, `space-evenly`
* **`cross-alignment` (交差軸方向)**
  * `start`, `center`, `end`

### 4. Overflow Strategy

**Overflow** とは、子 Widget の描画内容やレイアウトサイズが、親から割り当てられた領域（Bounds）を超える状態を指します。
一般的に Overflow の制御には Visible / Clip / Scroll がありますが、本フレームワークでは以下の設計思想に基づき **Visible** をデフォルトとしています。

* **Default: Visible**
  * デフォルトでは、コンテンツが領域をはみ出した場合でもそのまま描画されます（クリッピングされません）。
  * **Design Rationale**:
    * **Web Standard Alignment**: CSSのデフォルト値と同様 `overflow: visible`
    * **Fail Loudly**: Sizingシステムにより、基本的にはみ出すことはありません。もしそうなった場合は、レイアウト設計のバグであり、勝手に切り取られるよりも、はみ出して表示される方がバグに気づきやすく、修正が容易です。
    * **Design Freedom**: シャドウやフォーカスリングなどの視覚効果は、親の境界をはみ出す方が自然です。
    * **Role of Modifiers**: `Clip`（視覚効果）や `Scroll`（機能追加）は Modifier の責務であり、デフォルトの Widget は素直に描画すべきです。
    * **Performance First**: クリッピング処理（`saveLayer` / `clipRect`）は高コストです。デフォルトを Visible にすることで、フレームワークの基本性能を最大化します。

* **Handling Overflow**
  * **Clipping**: 視覚的に切り抜く必要がある場合は、`Clip` Modifier を使用します。
  * **Scrolling**: 領域内でスクロールさせる場合は、`Scroll` Modifier を使用します。

### 5. Role of Modifiers in Layout

**Modifier** は、既存の Widget をラップして、機能（Capabilities）や視覚効果（Effects）を付加する仕組みです。
詳細な設計については [MODIFIER.md](MODIFIER.md) を参照してください。

* **Principle: Layout is Property-driven**
  * レイアウト（サイズ、余白、配置）は、Widget 自身のプロパティ（`width`, `height`, `padding`, `alignment`）で制御します。
  * Modifier でレイアウトサイズや配置を直接変更することは避けます。

## Window (App) Sizing / Positioning

`App`（OS ウィンドウ）の `width` / `height` は Widget の `Sizing` とは別物です。

* Window の `width` / `height` は `WindowSizing`（または `WindowSizingLike`）として扱います。
  * **px** の固定値、または `"auto"`（preferred size）を受け取ります。
* `"50%"` のような指定は **サポートしません**（Widget の `Sizing.flex(...)` と意味が衝突するため）。

ウィンドウの表示位置は 9点 Alignment 語彙で指定します。

* `WindowPosition.alignment("bottom-center", offset=(0, -24))` のように指定します。
* `offset` は alignment の後に適用します。
  * 単位は px。
  * 座標系は UI と同様に $+x$ は右、$+y$ は下。
