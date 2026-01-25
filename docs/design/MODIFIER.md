# Modifier System Design

## Overview

Modifier は、既存の Widget をラップして、機能（Capabilities）や視覚効果（Effects）を付加する仕組みです。
Widget の継承や過剰なネスト（Wrapper Widget）を避け、宣言的かつフラットに機能を合成することを目的としています。

## Core Concepts

### 1. Modifier as a Wrapper

Modifier は本質的に「Widget を受け取り、新しい Widget を返す関数」です。
適用された Modifier は、元の Widget を `ModifierBox` などのラッパー Widget で包み込み、そのラッパーが機能や描画を担当します。

### 2. The `modifier()` Method

すべての Widget は `modifier()` メソッドを持ちます。これを使用して Modifier を適用します。
以前は `apply()` という名前でしたが、より宣言的で名詞的な `modifier()` に変更されました。

```python
# 基本的な使用法
widget.modifier(background("red"))
```

### 3. Chaining

Modifier は `|` 演算子を使用してチェーン（連結）することができます。
チェーンされた Modifier は左から右へ順番に適用されます。

```python
# チェーンの例
widget.modifier(
    background("white") | border("black", 2) | padding(10)
)
```

### 4. Immutability

Widget および Modifier はイミュータブル（不変）として扱われます。
`modifier()` メソッドは元の Widget を変更せず、新しい Widget インスタンス（ラッパー）を返します。

## Available Modifiers

### Visual Effects

* **`background(color)`**: 背景色を設定します。
* **`border(color, width)`**: 枠線を描画します。
* **`shadow(color, blur, offset_x, offset_y)`**: ドロップシャドウを描画します。
* **`corner_radius(radius)`**: 角丸を適用します（背景やボーダーに影響）。
* **`clip()`**: 子要素が領域をはみ出した場合にクリッピングします。

### Layout

Modifier ではレイアウトを扱いません。

nuiitivet では、レイアウト Widget とそのパラメータだけでレイアウトを制御します。
このおかげで、利用者は Widget とそのパラメータだけを見ればレイアウトを理解し、定義することができます。
Modifier でレイアウトを扱ってしまうと、このシンプルさが失われてしまいます。

### Interaction & Behavior

* **`clickable(on_click)`**: クリックイベントを処理します。
* **`hoverable(on_hover_change)`**: ホバー状態の変化を検知します。
* **`scrollable(axis)`**: スクロール機能を追加します。

## Implementation Details

### `ModifierElement` vs `Modifier`

* **`ModifierElement`**: 単一の機能を持つ Modifier の最小単位（例: `BackgroundModifier`）。
* **`Modifier`**: 複数の `ModifierElement` がチェーンされたリスト。

### `ModifierBox`

多くの視覚的 Modifier（background, border, padding 等）は、内部的に `ModifierBox` という単一の Widget に集約されます。
これにより、複数の Modifier を適用しても Widget ツリーが無駄に深くならず、描画パフォーマンスが最適化されます。

`ModifierBox` は `Widget` のサブクラスであり、適用された Modifier の情報を保持し、描画時にそれらを反映します。
