# Layout edit mode

Some fixes are not worth asking an agent for: a width or a height, the
order of two widgets — layout, in short. Layout edit mode lets you make those
yourself, by dragging the widget on the app's own screen.

## 1. Enter the mode

Press `Ctrl+Shift+E` (`Cmd+Shift+E` on macOS). The mode's name and `H help`
show at the centre for a moment.

## 2. Select the widget

Hover, and the widget under the cursor gets teal corner brackets and a caption
naming it. A label or icon a widget draws for itself counts as that widget.
Click to select it. The selection holds while the pointer stays on it — over
its children too — and moving off it returns to hover. `W` / `S` move the
selection to its parent and back, for when the container is what you want
and its children cover every pixel of it.

## 3. Change it

What you drag, and which way, decides what is written. A corner resizes.
The body, dragged along the container's axis, reorders; across it, aligns;
into another container, moves. `Enter` edits the text, and `Delete` removes
the widget.

Every drag ends on release. The value is written into the call that built
the widget. Hot reload applies it. The ghost stays until the reload lands.
After the reload, a notice at the window's bottom-left, the **badge**,
reports anything that did not go as the ghost said: a size that landed
elsewhere, or a reload that failed on the edit.

### Resize: drag a corner

Drag a corner bracket. A dashed **ghost** follows the pointer, captioned with
the value that will be written (`w 240  |  h auto`), one of the three sizes a
widget accepts:

- `"auto"` when you release within a few pixels of the widget's natural size;
- `"wt"` when you release where a weight would put it — the full cross axis of
  a `Column`, or its share of the leftover on the main axis;
- the integer otherwise.

A widget with a `size` parameter (`Icon`) stays square: the larger of the two
deltas wins.

To land on an exact size, hold `Alt` while dragging: the pointer's pixel
count is written instead of a snapped value. `W` / `A` / `S` / `D` while
dragging a corner move it by one pixel. From the first press the mouse no
longer moves it. `auto` / `wt` are then written only when the corner lands
exactly on them.

When one call builds many widgets — a helper returning a card, called from a
loop — every one of them gets a ghost, and the caption counts them
(`14 widgets`).

### Reorder, or move into another container

Drag the body along the container's axis to reorder among its siblings: up
and down in a `Column`, left and right in a `Row`. In a `Flow` or
`UniformFlow`, any travel that leaves the widget's slot reorders. Drag the
body into another container to move it there. The container it would land in —
its own, or another under the pointer — is **tinted**, and an **insertion
line** marks the slot, captioned with the sibling it goes before. In a `Grid`
the **cell** under the pointer is tinted instead, captioned with its row and
column, or its area name, and with whoever already sits there.

Over a `Stack`, the drop targets one layer at a time, and a list beside the
stack names its layers, bottom to top, with the landing marked. A widget
dragged in from outside lands in the top layer: inside it when the layer is a
container, on top of the stack otherwise, never in the background box
underneath. A widget that started inside the stack stays in its own layer
wherever the pointer is, so a card under a floating button still reorders in
its column. `W` / `S` or a digit `0`–`9` moves the landing to another layer,
the content column under a floating button, say. Past the top layer is a new
one on top. The choice holds until the pointer leaves the stack.

A widget that leaves a container can leave something behind. Out of a `Grid`,
its `GridItem` stays, and the badge names the `width` / `height` / `padding` /
`alignment` the item carried. Out of a `Container` or `Box`, the box stays,
empty. An empty box takes a widget dropped on it as its `child`. A box that
already has a child is passed over, and the drop lands in the list around it.
A `"wt"` moves as written. The badge notes when its meaning changed with the
move: a `"wt"` that filled a `Column`'s width becomes a share of a `Row`'s
leftover.

### Align

Drag the body across the container's axis: left and right in a `Column`, up
and down in a `Row`. In a `Flow` or `UniformFlow`, a drag that stays in the
widget's slot aligns. In a `Flow`, it must be mostly up or down. The widget
snaps to `start` / `center` / `end` on each axis. A dashed rect marks where
every child of the container will land. The caption names the value
(`center`, `bottom-right`) and how many children move. The alignment written
is the container's, so the whole column or stack moves with it. A
`CrossAligned` you wrote yourself is respected: dragging its child rewrites
that value, and other children with their own `CrossAligned` stay put when
the container's alignment changes.

### Edit the text

`Enter`, or a second click on the selection, edits its text in place. A field
opens over the widget; `Enter` writes the new string into the literal the code
passed (`text=` / `label=`, or the first argument), `Esc` or a click elsewhere
cancels. The field edits like a text field: `Shift+←/→` selects,
`Ctrl+A/C/X/V` (`Cmd` on macOS) select all, copy, cut and paste. Text that
comes from a variable, an f-string or a function call cannot be edited here —
the badge says so.

### Delete

`Delete` / `Backspace` removes the selected widget from the source — its whole
expression, children included. No confirmation. A handler or import the
widget used stays behind for you or the agent to clean up.

### Undo

`Ctrl+Z` reverts the last edit this mode wrote. The one exception is a line
you have edited by hand since: the undo is refused rather than applied to the
wrong text. `Ctrl+Shift+Z` redoes what `Ctrl+Z` undid; a new edit clears what
could be redone.

## 4. Leave

Press `Esc`.

## Every gesture

| Gesture | What it does |
| --- | --- |
| `Ctrl+Shift+E` | Enter layout edit mode (`Cmd+Shift+E` on macOS) — `E` for *edit*. Inside comment mode it switches directly, your marks kept; `Ctrl+Shift+C` switches back. |
| Hold `H` | Show every gesture of this mode while the key is down. |
| Hover | The widget under the cursor gets teal corner brackets and a caption naming it. |
| Click | Select it. `W` / `S` then move to its parent and back. The selection holds while the pointer stays on it. |
| Drag a corner bracket | Resize. A dashed ghost follows the pointer, captioned with the value that will be written. |
| `W` / `A` / `S` / `D` while dragging a corner | Move the grabbed corner by one pixel; the mouse no longer moves it. |
| `Alt` while dragging | Land on the exact pixel count instead of snapping. |
| Drag the body | Reorder among its siblings, move into the container or grid cell under the pointer, or, keeping its place, align it. |
| `W` / `S` / `0`–`9` while dragging over a `Stack` | Pick the layer the widget lands in; past the top layer is a new one. |
| Release | Write and reload. The ghost stays until the reload lands. |
| `Enter`, or a second click on the selection | Edit its text in place; `Enter` writes, `Esc` or a click elsewhere cancels. |
| `Delete` / `Backspace` | Remove the selected widget from the source, children included. `Ctrl+Z` brings it back. |
| `Ctrl+Z` | Undo the last edit this mode wrote. |
| `Ctrl+Shift+Z` | Redo what `Ctrl+Z` undid. A new edit clears what could be redone. |
| `Esc` | Cancel the drag in flight; otherwise leave. |

## Everything it writes, and every drag it refuses

### What it writes

Layout edit mode writes four things, and nothing else:

- `width`, `height` and `size`;
- a child's place in the list that orders the children — `children=[...]`, or
  the data a comprehension or `Column.builder()` iterates, even one bound to a
  name (`tags = [...]`);
- a `GridItem`'s `row` / `column` or area, with the wrapper itself added or
  removed as a widget enters or leaves a `Grid`;
- a container's `alignment` / `cross_alignment` / `item_alignment`, or a
  `CrossAligned`'s value.

`padding`, `gap`, colours and every other style value are yours to change in
code.

### Drags it refuses

The badge says why, and the file is left alone. That happens for:

- Resize
  - a size bound to a name or an expression (`width=self.card_w`);
  - a widget whose constructor takes no `width`, `height` or `size`;
- Reorder
  - a reorder whose order is not in one list literal in the file — `head +
    tail`, `[first, *rest]`, a filtered comprehension, items from a call or a
    view model, a name that is assigned twice or used again after its list. The
    badge names the list;
  - a move out of, or into, a container whose `children` are not written as a
    list literal — `Column.builder()`, a `ForEach`, a comprehension. The badge
    says so while you hover, before you release;
  - a `GridItem` whose `row` / `column` or area name is bound to a name or an
    expression; it can neither change cell nor leave the grid;
  - a move into a `Grid` written as a bare `Grid(...)` in a module that does
    not import `GridItem`: no import is added, and the badge asks you for
    one;
- Align
  - an `alignment` / `cross_alignment` / `item_alignment` bound to a name or an
    expression;
  - a widget as big as its container on every axis it could align on —
    `"wt"`, or the same size — since there is nowhere for it to go;
- Either
  - a widget whose call has moved or changed since the last reload, or one
    built by code outside your files.

### Drags that do nothing

No badge, no change:

- Reorder
  - releasing the widget in its own slot, or its own grid cell;
  - releasing over a `Grid`'s padding, where there is no cell;
- Align
  - releasing on the alignment the container already has.

## Next Steps

- [Source jump](source_jump.md) — read or edit the code behind a widget.
- [With a coding agent](index.md) — the section overview.
