# Layout edit mode

Some fixes are not worth asking an agent for: a width, or a button outlined
instead of filled. Layout edit mode lets you make those yourself, on the
app's own screen.

## How a round goes

### 1. Enter the mode

Press `Ctrl+Shift+E` (`Cmd+Shift+E` on macOS). The mode's name and `H help`
show at the centre for a moment. Inside comment mode the same chord switches
over, your marks kept. `Ctrl+Shift+C` switches back.

### 2. Select the widget

Hover, and the widget under the cursor gets teal corner brackets and a
caption naming its type. Hovering a button's label brackets the button.
Click to select the widget. The selection stays until you click another
widget or click nothing. It keeps its brackets while the pointer is on it,
over its children too. Once the pointer leaves, a faint pair of brackets
stays. When the container is what you want and its children cover every
pixel of it, select a child and press `W`: `W` moves the selection to its
parent, `S` back down.

### 3. Drag a corner

Drag a corner bracket. A dashed **ghost** follows the pointer, captioned
with the value that will be written (`w 240  |  h auto`). `Esc` before the
release cancels the drag. The corner is one way to change the widget; its
body, its handles and the bar over it are the others, each listed under
[Everything you can change](#everything-you-can-change) in place of this
step.

### 4. Release, and read the badge

Every drag ends on release. A pick ends on its row. The value is written
into the call that built the widget. Hot reload applies it. The ghost stays
until the reload lands. When one call builds many widgets, a helper
returning a card called from a loop, every one of them gets a ghost, and
the caption counts them (`14 widgets`). After the reload, a notice at the
window's bottom-left, the **badge**, reports anything that did not go as
the ghost said: a size that landed elsewhere, or a reload that failed on
the edit.

### 5. Undo if it went wrong

`Ctrl+Z` reverts the last edit this mode wrote. The one exception is a line
you have edited by hand since: the undo is refused. `Ctrl+Shift+Z` redoes
what `Ctrl+Z` undid. A new edit clears what could be redone.

### 6. Leave

Press `Esc`. With a widget selected, the first press drops the selection and
its bar; the second leaves.

## Everything you can change

Each way below takes the place of step 3 of the round. The body's drag
depends on its direction: along the container's axis it reorders, across
it aligns, into another container it moves.

### Resize: drag a corner

Drag a corner bracket. A dashed **ghost** follows the pointer, captioned with
the value that will be written (`w 240  |  h auto`), one of the three sizes a
widget accepts:

- `"auto"` when you release within a few pixels of the widget's natural size;
- `"wt"` when you release where a weight would land: at a `Column`'s full
  width, or at the share of the leftover a weight gets along the main axis;
  the caption reads `wt` there;
- the integer otherwise.

A widget with a `size` parameter (`Icon`) stays square: the larger of the two
deltas wins.

Hold `Alt` to land on an exact size: the pointer's pixel count is written
instead of a snapped value. `W` / `A` / `S` / `D` while dragging a corner
move it by one pixel. From the first press the mouse no longer moves it.
`auto` / `wt` are then written only when the corner lands exactly on them.

### Reorder, or move into another container

Drag the body along the container's axis to reorder among its siblings, or
into another container to move it there. To drag a container whose children
cover it, press in its padding, away from the midpoints of its edges. The
container it would land in, its own or another under the pointer, is
**tinted**. An **insertion line** marks the slot, captioned with the sibling
it goes before. A `"wt"` moves as written. The badge notes when its meaning
changed with the move: a `"wt"` that filled a `Column`'s width becomes a
share of a `Row`'s leftover.

#### In a `Column`, a `Row`, a `Flow` or a `UniformFlow`

Up and down reorder in a `Column`, left and right in a `Row`. In a `Flow` or
`UniformFlow`, any travel that leaves the widget's slot reorders.

#### Into or out of a `Grid`

The **cell** under the pointer is tinted instead of a line. Its caption
names the row and column, or the area name, and whoever already sits there.
A widget that leaves a `Grid` leaves its `GridItem` behind, and the badge
names the `width` / `height` / `padding` / `alignment` the item carried.

#### Over a `Stack`

A list beside the stack names its layers, bottom to top, with the landing
marked. A widget dragged in from outside lands in the top layer: inside it
when the layer is a container, otherwise on top of the stack. It never lands
in the background box underneath. A widget that started inside the stack
stays in its own layer wherever the pointer is, so a card under a floating
button still reorders in its column. `W` / `S` step the landing to another
layer, and a digit `0`–`9` picks one by its number in the list. Past the top
layer is a new one on top. The choice holds until the pointer leaves the
stack.

#### Into or out of a `Container` or a `Box`

An empty box takes a widget dropped on it as its `child`. A box that already
has a child is passed over, and the drop lands in the list around it. A
widget that leaves a box leaves it behind, empty.

### Align

Drag the body across the container's axis: left and right in a `Column`, up
and down in a `Row`. In a `Flow` or `UniformFlow`, a drag that stays in the
widget's slot aligns. In a `Flow`, it must be mostly up or down; mostly
sideways within the slot, it does nothing. In a `Stack`, a `Container` or a
`Box`, a drag in any direction aligns. The widget snaps to `start` /
`center` / `end` on each axis. A dashed rect marks where every child of the
container will land. The caption names the value (`center`, `bottom-right`)
and how many children move. The alignment written is the container's. A
`CrossAligned` you wrote yourself is respected: dragging its child rewrites
that value. Other children with their own `CrossAligned` stay put when the
container's alignment changes.

### Space it: the handles

A hovered widget that takes a `padding` has an outlined pill, a **handle**,
on each of its four edges. A `Column` or `Row` has one more in each gap
between its children. Hover a handle and it fills, along with every handle
that moves with it.

#### Drag a handle

Pull a padding handle away from the content and the padding grows. The
content's edge is zero; pushing past it stays at zero. Push a gap handle
toward the next child, down in a `Column` or right in a `Row`, and the gap
grows. Every gap handle moves together, and every later child is drawn
where the new gap puts it. A tinted **band** shows the value, from the
content's edge out to the handle. Its caption is what will be written
(`padding 20`, `gap 12`). Values snap to multiples of 4. `Alt` and
`W` / `A` / `S` / `D` work as on a corner.

On an axis the widget sizes to its content, the band grows outward and the
handle rides with it. On a fixed width or height, a `"wt"`, or a root that
fills its window, the band grows inward from the edge instead: the content
moves, and the handle does not follow the pointer.

#### Click a handle

Click a handle and the fill turns: every side moves as one (`padding=20`),
then the pair the handle belongs to (`padding=(20, 8)`), then the one side
alone (`padding=(8, 8, 20, 8)`), and round again. The shape starts as the
source spells it.

### Pick a preset: the bar over the selection

Select a `Button`, an `IconButton`, an `IconToggleButton`, a `Card` or a
`Text`, and a bar appears just over it. The bar carries the widget's type,
then a box per preset it takes: `style` and `size` for a button, `style`
for a card, `type scale` for a text. Each box shows what the source holds.
Click a box and its list opens under it. Click a row to write it.
`W` / `S` or `↑` / `↓` move along the list, `Enter` writes, `Esc` closes it.

A box reads `filled (default)` when the call passes no `style`; a pick
inserts the keyword. It reads `custom` when the value is not a preset, such
as a `copy_with(...)`, a variable or a constructor. A pick then replaces
that whole expression.

### Edit the text

`Enter`, or a second click on the selection, edits its text in place. A field
opens over the widget. `Enter` writes the new string into the literal the code
passed (`text=` / `label=`, or the first argument). `Esc` or a click elsewhere
cancels. The field edits like a text field: `Shift+←/→` selects,
`Ctrl+A/C/X/V` (`Cmd` on macOS) select all, copy, cut and paste. Text that
comes from a variable, an f-string or a function call cannot be edited here —
the badge says so.

### Delete

`Delete` / `Backspace` removes the selected widget from the source — its whole
expression, children included. No confirmation. A handler or import the
widget used stays behind for you or the agent to clean up.

## Every gesture

| Gesture | What it does |
| --- | --- |
| `Ctrl+Shift+E` | Enter layout edit mode (`Cmd+Shift+E` on macOS). Inside comment mode it switches directly, your marks kept; `Ctrl+Shift+C` switches back. |
| Hold `H` | Show every gesture of this mode while the key is down. |
| Hover | The widget under the cursor gets teal corner brackets, a caption naming its type, and handles on its edges and in its gaps. |
| Click | Select it. `W` / `S` then move to its parent and back. The selection stays until another click or `Esc`. |
| Drag a corner bracket | Resize. A dashed ghost follows the pointer, captioned with the value that will be written. |
| Drag a handle | Change the padding on that side, or the gap. A band shows the value; away from the content is more. |
| Click a handle | Turn how many sides move with it: every side, its pair, or itself alone. |
| `W` / `A` / `S` / `D` while dragging a corner or a handle | Move it by one pixel; the mouse no longer moves it. |
| `Alt` while dragging | Land on the exact pixel count instead of snapping. |
| Drag the body | Reorder among its siblings, move into the container or grid cell under the pointer, or, keeping its place, align it. |
| `W` / `S` / `0`–`9` while dragging over a `Stack` | Pick the layer the widget lands in; past the top layer is a new one. |
| Release | Write and reload. The ghost stays until the reload lands. |
| Click a box on the bar over the selection | Open its list of presets; a row writes. `W` / `S` move along it, `Enter` writes, `Esc` closes. |
| `Enter`, or a second click on the selection | Edit its text in place; `Enter` writes, `Esc` or a click elsewhere cancels. |
| `Delete` / `Backspace` | Remove the selected widget from the source, children included. |
| `Ctrl+Z` | Undo the last edit this mode wrote. |
| `Ctrl+Shift+Z` | Redo what `Ctrl+Z` undid. A new edit clears what could be redone. |
| `Esc` | Cancel the drag in flight, or close the open list; otherwise drop the selection; with none, leave. |

## Everything it writes, refuses, or ignores

### What it writes

Layout edit mode writes these, and nothing else:

- `width`, `height` and `size`;
- a child's place in the list that orders the children — `children=[...]`, or
  the data a comprehension or `Column.builder()` iterates, even one bound to a
  name (`tags = [...]`);
- a `GridItem`'s `row` / `column` or area, with the wrapper itself added or
  removed as a widget enters or leaves a `Grid`;
- a container's `alignment` / `cross_alignment` / `item_alignment`, or a
  `CrossAligned`'s value;
- `padding` and `gap`, in the shape the handles stand for: one int, an
  `(h, v)` pair, or four sides;
- `style` as a preset call (`nv.ButtonStyle.outlined("m")`), and `type_scale`
  as a role (`nv.TypeScale.TITLE_LARGE`); a module that imports `Button`
  itself gets `ButtonStyle.outlined("m")`.

It does not write colours, shapes or the other values inside a style.

### What it refuses

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
  - a widget as big as its container on every axis it could align on:
    `"wt"`, or the same size;
- Space
  - a `padding` or `gap` bound to a name, an expression or an observable;
- Pick
  - a `style` or `type_scale` that may come through `**kwargs`;
  - a bare `Button(...)` in a module that does not import `ButtonStyle`
    (likewise `Card` / `CardStyle`, `Text` / `TypeScale`): no import is added,
    and the badge asks you for one;
- Any
  - a widget whose call has moved or changed since the last reload, or one
    built by code outside your files.

### What does nothing

No badge, no change:

- Reorder
  - releasing the widget in its own slot, or its own grid cell;
  - releasing over a `Grid`'s padding, where there is no cell;
- Align
  - releasing on the alignment the container already has;
- Space
  - releasing a handle where it started, which is a click: it turns the shape
    instead;
- Pick
  - choosing the row the source already holds.

## Next Steps

- [Source jump](source_jump.md) — read or edit the code behind a widget.
- [With a coding agent](index.md) — the section overview.
