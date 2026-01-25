# M3仕様とFramework Paddingの結合ルール設計

See [BOX_MODEL.md](BOX_MODEL.md) for the single source of truth on `padding`, hit testing, and visual overflow (`outsets`).

## 問題の本質

**M3には `padding`/`margin` という概念が存在しない**

M3の仕様では、各コンポーネントのサイズは以下で定義される：

- Touch Target（インタラクション領域）
- Container Size（視覚的なコンテナ）
- Content Size（内部コンテンツ）
- State Layer（フィードバック領域）

しかし、**「padding」や「margin」という用語は使われていない**。

## M3の実際の表現

### 例1: Button (M3 Specs)

```text
Container height: 40dp
Horizontal padding: 24dp (内部テキストとコンテナ端の距離)
Minimum width: 48dp (touch target)
```

→ M3では "padding" と呼んでいるが、これは**コンテナ内のコンテンツ配置**を指す

### 例2: Checkbox (M3 Specs)

```text
Container: 18×18dp (アイコン)
State layer: 40×40dp (円形)
Minimum touch target: 48×48dp
```

→ padding という言葉は使われず、**各層のサイズが独立して定義**される

### 例3: List Item (M3 Specs)

```text
Container height: 56dp
Leading element: 24×24dp icon
Content padding: 16dp (from leading/trailing edge)
Spacing between icon and text: 16dp
```

→ "padding" は**コンテナ内部の配置ルール**として使われる

## M3の暗黙のルール

M3では以下の階層構造が暗黙的に存在する：

```text
Component (コンポーネント全体)
├─ Touch Target (最小48×48dp, インタラクション領域)
├─ Container (視覚的な境界)
├─ State Layer (ホバー/プレスフィードバック)
└─ Content (内部コンテンツ)
    └─ Internal Spacing/Padding (コンテンツ配置)
```

**重要**: これらは全て**コンポーネント内部の構造**であり、**外部レイアウトとは無関係**。

## フレームワークの `padding` の意味

我々のフレームワークでは：

```python
Widget(padding=...)
```

これは**Widget基底クラスの機能**で、以下の2つの解釈がある：

### 解釈A: 内部パディング（Container的）

```text
┌─────────────────────────────┐
│ Widget Boundary             │
│  ┌─────────────────────┐    │
│  │ padding (内側余白)   │    │
│  │  ┌───────────────┐  │    │
│  │  │   Content     │  │    │
│  │  └───────────────┘  │    │
│  └─────────────────────┘    │
└─────────────────────────────┘
```

→ M3の「Container内のcontent配置」に相当

### 解釈B: 「外側余白」に見える（よくある誤解）

```text
┌─────────────────────────────┐
│ Parent Layout               │
│  ┌─────────────────────┐    │
│  │ padding (insets)    │    │
│  │  ┌───────────────┐  │    │
│  │  │   Widget      │  │    │
│  │  │   Boundary    │  │    │
│  │  └───────────────┘  │    │
│  └─────────────────────┘    │
└─────────────────────────────┘
```

→ M3には対応概念なし（ただし Framework の `padding` は margin ではない）
    - `padding` 自体は allocated→content の insets
    - leaf widget の描画や hit test のルール次第で「外側余白っぽく」見えたり振る舞ったりする

## 提案：2層モデル

### ルール1: M3コンポーネント = 自己完結的な内部構造

M3の各コンポーネント（Button, Checkbox, etc）は**内部構造を持つ閉じた単位**。

```python
# M3コンポーネントは「M3仕様のサイズ」を持つ
Checkbox(size=48)  # M3の「48dp touch target」
Button(height=40)  # M3の「40dp container height」
```

→ これらは**M3仕様のパラメータ**であり、padding とは無関係。

### ルール2: Widget.padding = allocated→content の insets

`Widget.padding` は**allocated rect から content rect を切り出すための insets（内側余白）**。

補足: leaf widget では「外側余白」に見えることがある

- 見た目の描画（背景なし等）が content rect に寄っていると、padding 部分は視覚的に空白になりやすい。
- それでも hit test は（原則）allocated rect を基準にするため、padding 部分がタッチターゲットに含まれることがある。

```python
# M3コンポーネント + フレームワークのレイアウト調整
Checkbox(size=48, padding=10)
#        ↑         ↑
#        M3仕様    insets (padding)
```

**図解**:

```text
┌─────────────────────────────────────┐
│ Widget (preferred_size に含まれる)    │
│  ┌─────────────────────────────┐    │
│  │ padding=10 (insets)         │    │
│  │  ┌───────────────────────┐  │    │
│  │  │ M3 Component          │  │    │
│  │  │ (size=48)             │  │    │
│  │  │  - Touch Target       │  │    │
│  │  │  - State Layer        │  │    │
│  │  │  - Icon               │  │    │
│  │  └───────────────────────┘  │    │
│  └─────────────────────────────┘    │
└─────────────────────────────────────┘
preferred_size = 48 + 10*2 = 68dp
```

### ルール3: M3内部構造は自動計算

M3コンポーネントの内部構造（Icon/State Layer/Touch Target）は**M3仕様に従って自動計算**。

```python
class Checkbox(Widget):
    def __init__(self, size=48, padding=0, ...):
        super().__init__(width=size, height=size, padding=padding)
        
        # M3仕様の内部構造（ユーザーは触らない）
        self._touch_target = size              # 48dp
        self._state_layer = size * (40/48)     # 40dp (M3比率)
        self._icon_size = size * (18/48)       # 18dp (M3比率)
    
    def preferred_size(self):
        # M3サイズ + padding
        l, t, r, b = self.padding
        return (self._touch_target + l + r,
                self._touch_target + t + b)
    
    def paint(self, canvas, x, y, width, height):
        # paddingを適用してcontent領域取得
        cx, cy, cw, ch = self.content_rect(x, y, width, height)
        
        # content領域内にM3コンポーネントを配置
        # （M3内部構造はここで描画）
        self._paint_m3_component(canvas, cx, cy, cw, ch)
```

## 統一ルール定義

### ✅ 採用するルール

**`Widget.padding` = allocated→content の insets（全Widget共通）**

1. **M3仕様パラメータ**: `size`, `height`, `width` 等
   - M3の公式仕様に従う
   - コンポーネント内部構造を定義

2. **Framework padding**: `padding` パラメータ
    - allocated→content の insets
    - `preferred_size()` に含まれる（結果としてレイアウト上は「周囲に余白がある」ように振る舞うことがある）

3. **M3内部構造**: 自動計算
   - Touch Target, State Layer, Icon等
   - M3比率で自動計算
   - ユーザーは通常意識しない

### 実装パターン

#### パターン1: 固定サイズWidget（Checkbox, Icon）

```python
class Checkbox(Widget):
    def __init__(self, size=48, padding=0, ...):
        # M3: size = Touch Target
        # Framework: padding = allocated→content insets
        super().__init__(width=size, height=size, padding=padding)
        self._m3_size = size
    
    def preferred_size(self):
        l, t, r, b = self.padding
        return (self._m3_size + l + r, self._m3_size + t + b)
```

#### パターン2: 可変サイズWidget（Button）

```python
class Button(Widget):
    def __init__(self, label, padding=0, ...):
        # M3: 内部padding (24dp horizontal) は別パラメータ
        # Framework: padding = allocated→content insets
        super().__init__(padding=padding)
        self._m3_horizontal_padding = 24  # M3内部
        self._m3_height = 40              # M3仕様
    
    def preferred_size(self):
        # M3: text width + M3内部padding
        text_w = self._measure_text()
        m3_width = text_w + self._m3_horizontal_padding * 2
        m3_height = self._m3_height
        
        # Framework: M3サイズ + padding
        l, t, r, b = self.padding
        return (m3_width + l + r, m3_height + t + b)
```

#### パターン3: レイアウトWidget（Column, Row）

```python
class Column(Widget):
    def __init__(self, children, spacing=0, padding=0, ...):
        # M3: 該当なし（レイアウトはフレームワーク機能）
        # Framework: padding = 子の配置前の内側余白
        super().__init__(padding=padding)
        self._spacing = spacing  # 子間のスペース
    
    def preferred_size(self):
        # 子のサイズ + spacing
        children_size = self._calculate_children_size()
        
        # Framework: children + padding
        l, t, r, b = self.padding
        return (children_size.w + l + r, children_size.h + t + b)
```

## 用語の整理

### M3用語 → Framework用語マッピング

| M3用語 | Framework用語 | 説明 |
| -------- | --------------- | ------ |
| Container size | `size`, `width`, `height` | M3コンポーネントのサイズ |
| Content padding (内部) | M3パラメータ or 自動計算 | コンポーネント内部の配置 |
| Touch target | M3パラメータ（通常は`size`） | インタラクション領域 |
| State layer | 自動計算 | M3比率で決定 |
| Spacing (between items) | `spacing` | 子要素間の距離 |
| **(該当なし)** | `padding` | allocated→content の insets（結果として周囲の空白に見えることがある） |

### 重要な区別

```python
# ❌ M3には存在しない概念
m3_component.margin = ...  # M3にmarginはない

# ✅ Frameworkで追加する概念
widget.padding = ...  # allocated→content insets

# ✅ M3の概念
m3_component.size = 48           # Touch target (M3仕様)
m3_component.container_height = 40  # Container (M3仕様)
```

## 具体例：Checkbox

### M3仕様

```text
Touch target: 48×48dp (minimum)
State layer: 40dp diameter
Icon: 18×18dp
```

### Framework実装

```python
Checkbox(
    size=48,      # M3: Touch target
    padding=0,    # Framework: insets（default）
)

# preferred_size() = 48×48 (M3サイズ)
# 内部構造:
#   touch_target = 48dp (size)
#   state_layer = 40dp (自動計算: 48 * 40/48)
#   icon = 18dp (自動計算: 48 * 18/48)
```

### レイアウト調整が必要な場合

```python
Checkbox(
    size=48,       # M3: Touch target
    padding=10,    # Framework: insets
)

# preferred_size() = 68×68 (48 + 10*2)
# M3内部構造は変わらず48dp領域内に描画
# insets は content rect を狭め、結果として周囲に空白が見えることがある
```

## まとめ：統一ルール

### ✅ 決定事項

1. **M3仕様パラメータ（`size`, `width`, `height` 等）**
   - M3コンポーネントの**内部構造**を定義
   - M3公式仕様に従う
   - padding とは独立

2. **Framework padding**
    - allocated→content の insets（M3仕様には存在しない概念）
    - `preferred_size()` に含まれる
    - デフォルト値は `0`

3. **用語の使い分け**
   - "M3 internal padding" → M3仕様パラメータまたは自動計算
     - "Widget padding" → allocated→content の insets

4. **実装方針**
   - M3コンポーネントは自己完結的
     - padding は全Widget共通の allocated→content insets
   - レイアウトWidget（Column/Row）は padding を内側余白として使用

### 🎯 一貫性の保証

```python
# 全てのWidgetで統一
Column(padding=10)      # 子の配置前の内側余白
Row(padding=10)         # 子の配置前の内側余白
Text(padding=10)        # テキストの周囲余白
Checkbox(padding=10)    # allocated→content insets（leafでは周囲余白に見えることがある）
Icon(padding=10)        # allocated→content insets（leafでは周囲余白に見えることがある）
Button(padding=10)      # allocated→content insets
```

**意味**: 全て「preferred_size に含まれる余白」で統一。

**M3内部構造**: 各Widgetが独自に管理（padding とは独立）。

## 次回に向けた準備チェックリスト

MD3準拠対応をスムーズに行うため、実装着手前に以下を用意する。

### 1) 対象Widgetの確定

- Widget名（例: Switch / Radio / Slider / ListItem 等）
- Variant（例: Filled/Outlined、Small/Medium/Large など）
- 対象プラットフォーム差（Android/iOS/Webで差があるか）

### 2) MD3仕様データ（数値）

最低限、以下の数値をVariantごとに揃える。

- Touch target（最小サイズ）
- Container size（高さ/幅、形状）
- Content insets（leading/trailing/top/bottom）
- Icon/indicator サイズ
- Gap/spacing（要素間）
- State layer（サイズ、形、表示条件）
- Typography（font size, line height, weight など）

補足:

- M3の「padding」は原則として **Container内のcontent配置** を意味する。
- Frameworkの `Widget.padding` は allocated→content の insets として扱う（BOX_MODELのルール）。

### 3) 状態ごとの差分（見た目と入力）

- enabled / disabled
- hovered / pressed
- focused（Focus ring/outline の有無、outsetsか）
- selected / checked / indeterminate

状態ごとに「サイズが変わるか」「描画だけ変わるか」を明記する。

### 4) ルール接続（BOX_MODELへのマッピング）

- Preferred size: touch target を満たすか（例: min 48）
- Paint: container をどこに描くか（例: 48内で40を中央配置）
- Hit test: allocated rect を基準にするか（例外: viewport/clip）
- Outsets: shadow/focus/overlay を outsets として扱うか（layout/hit testに入れない）

### 5) テーマ/スタイル設計

- `*Style` に入れるべき token（例: container_height, content_insets, spacing, min_height）
- ThemeData 経由で参照するか、Widgetの引数で上書き可能にするか
- 既存Style/APIを破壊してよい変更点（後方互換は考慮しない）

### 6) 受け入れ条件（テスト観点）

- preferred_size の期待値（固定値 or 範囲）
- padding が preferred_size に含まれること
- hit test が allocated rect に従うこと
- clip/viewport の visible region 制約が壊れないこと

可能なら、目視確認用の `src/samples/*_demo.py` を同時に用意する。

## 仕様→実装の記入テンプレート

次回以降は、以下のテンプレを埋めるだけで実装タスク化できる。

### Widget: <NAME>

#### MD3 Spec (per variant)

| Variant | Touch target | Container | Insets (L/T/R/B) | Icon | Gap | Font | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| default | 48x48 | 40h | 16/0/16/0 | 20 | 8 | 14 | |

#### State differences

- disabled:
- hovered:
- pressed:
- focused:
- selected:

#### Framework mapping

- `Widget.padding`:
- preferred_size:
- paint (container placement):
- hit test:
- outsets:

#### Style/Theme tokens

- Style fields to add/update:
- ThemeData wiring:

#### Tests / Demo

- Tests to add/update:
- Demo to add/update:
