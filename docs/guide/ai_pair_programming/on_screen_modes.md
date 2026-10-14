# The on-screen modes

Every fix starts from the screen of your running app. Three things you can do
there, with the app launched under the [dev runner](hot_reload.md):

| You want to | Do this |
| --- | --- |
| Tell the coding agent what to change, or what went wrong, right where it is | [Write an instruction on the app](#write-instructions-on-the-app-comment-mode) — `Ctrl+Shift+C` |
| Fix a size, an order or an alignment yourself | [Edit the layout directly](#edit-the-layout-directly-layout-edit-mode) — `Ctrl+Shift+E` |
| Read or edit the code behind a widget | [Jump to the source](#jump-to-the-source) — `Ctrl+Shift+Click` |

## Write instructions on the app (comment mode)

Telling an agent *where* is often the hard part of telling it what to do.
Comment mode puts the instruction on the app itself: mark a widget or an area,
write what you want done on the mark, and the agent reads the place and the
words together.

| Gesture | What it does |
| --- | --- |
| `Ctrl+Shift+C` | Enter comment mode (`Cmd+Shift+C` on macOS — either accelerator works throughout). |
| Hold `H` | Show every gesture of this mode while the key is down. |
| Hover | The widget under the cursor gets amber corner brackets and a caption naming it: the one a click would mark. |
| `W` / `S`, `A` / `D` | Move that choice up to its parent and back down, or along to the widget beside it, when the one you mean is covered by its children or too small to aim at. `Enter` or a click then marks it. |
| Click | Mark the widget under the cursor; a field opens on the mark. On a marked widget, or on its numbered badge, the field opens again instead: on your text, to change or clear it, or empty once the agent has answered, to reply. |
| Drag | Mark an **area** instead — a gap, a misaligned band, anywhere with no widget to name. The field opens the same way. |
| In the field | Type the instruction. `Enter` keeps it (leave it empty to keep just the number); `Ctrl+Enter` keeps it and sends; `Shift+Enter` breaks the line; `Esc` closes the field, and on a mark you just made with nothing written yet, removes the mark too (`Ctrl+Z` brings it back). `Shift+←/→` selects, `Ctrl+A/C/X/V` (`Cmd` on macOS) select all, copy, cut and paste. A click keeps the text and then does what it would have done anyway. |
| `Ctrl+Enter`, or **Send**, the button at the bottom-right | Send your comments to the agent. The button hides below the window's edge with a sliver showing; bring the pointer to the sliver and it stands up. A click there also keeps the field you were typing in. |
| The badge | After **Send**, a grey disc with an hourglass joins the number of every mark the agent has not answered yet. The answer replaces it with a coloured disc: green with a check mark for done, red with a cross for refused, blue with a question mark for a question to you. Hover to read the line. |
| Hover a mark's numbered badge | Read its thread under the badge: your lines and the agent's, each led by an icon for who wrote it. A thread taller than the window shows its newest lines and counts the rest. Nothing but the number stays beside a mark. |
| `Delete` / `Backspace` | Remove the mark under the cursor, on its widget or on its badge. `Ctrl+Z` brings it back. |
| `Ctrl+Z` / `Ctrl+Shift+Z` | Undo and redo what you did since you last sent — a mark, an unmark, a text. The same keys as layout edit mode. |
| `Ctrl+Backspace` | Remove every mark, sent ones included. `Ctrl+Z` brings them back. |
| `Esc` | Leave. The marks go off the screen but stay, sent or not; enter again and they are back as you left them. |
| `Ctrl+Shift+E` | Switch to [layout edit mode](#edit-the-layout-directly-layout-edit-mode), your marks kept. |

Click the widget you mean, or drag a box over the area. A field opens on the
mark; type the instruction and press `Enter` to keep it. Mark as many places
as you like, then press `Ctrl+Enter` or the **Send** button: the agent
handles them all in one turn, each by its number.
A mark with no text is fine too — refer to it by number in chat. The text can
be a problem instead of a change: comment right after it happens, and the
agent replays what you did in the app to reproduce it before fixing.

The agent answers each **Send** while its watch runs: in chat,
`/nuiitivet-see-comments watch`, once per session, before or after your first
Send. It does what each comment says, writes its answer on the mark, `done`
and what it did, `refused` and why, or a `question` for you, and waits for
the next Send; no chat message is needed. Without the watch,
`/nuiitivet-see-comments` reads them once, and without the skill
[installed](install_skills.md), `see_comments` does.

Stay in the mode: the hourglass on each mark turns into the answer. To answer
back, click the mark, type, press `Enter`, and press **Send** again: your
reply joins the thread, and the agent reads the whole thread. A `refused` or a
`question` waits for that reply; remove the mark with `Delete` if you accept
the refusal, and a `done` mark the same way once you have seen it.

Press `Esc` when you want the app back. The line at the centre says so, and
`unsent comments` if you left something the agent has not seen; the marks
return with the mode.

> **Privacy note.** `interaction_log` records neither coordinates nor typed
> content, because it records ambiently. A comment may carry both, and your
> own words — that is the point of it, since you chose to show it. The journal
> still only gains a content-free marker that you commented on *something*;
> the payload goes out only when the agent asks for it.

## Edit the layout directly (layout edit mode)

Some fixes are not worth asking an agent for: a width or a height, the
order of two widgets — layout, in short. Layout edit mode lets you make those
yourself, by dragging the widget on the app's own screen. The dev runner writes
the change into the source, and hot reload applies it. When you enter, the
mode's name and `H help` show at the centre for a moment, and when you leave
the same spot says so. Hold `H` whenever you want the whole list.

| Gesture | What it does |
| --- | --- |
| `Ctrl+Shift+E` | Enter layout edit mode (`Cmd+Shift+E` on macOS) — `E` for *edit*. Inside comment mode it switches directly, your marks kept; `Ctrl+Shift+C` switches back. |
| Hold `H` | Show every gesture of this mode while the key is down. |
| Hover | The widget under the cursor gets teal corner brackets and a caption naming it. A label or icon a widget draws for itself counts as that widget. |
| Click | Select it. `W` / `S` then move to its parent and back, for when the container is what you want to resize. The selection holds while the pointer stays on it — over its children too — and moving off it returns to hover. |
| Drag a corner bracket | Resize. A dashed **ghost** follows the pointer, captioned with the value that will be written. |
| `W` / `A` / `S` / `D` while dragging a corner | Move the grabbed corner by one pixel. From the first press the mouse no longer moves it, and `auto` / `wt` are written only when the corner lands exactly on them, not within the usual band; release writes as usual. |
| Drag the body | Reorder among its siblings, or move it into the container under the pointer. The container it would land in — its own, or another under the pointer — is **tinted**, and an **insertion line** marks the slot, captioned with the sibling it goes before. In a `Grid` the **cell** under the pointer is tinted instead, captioned with its row and column, or its area name, and with whoever already sits there. A drag that keeps the widget's place **aligns** it instead: it snaps to `start` / `center` / `end` on each axis, a dashed rect marks where every child of the container will land, and the caption names the value (`center`, `bottom-right`) and how many children move — the alignment written is the container's, so the whole column or stack moves with it. |
| `W` / `S` / `0`–`9` while dragging over a `Stack` | Pick the layer the widget lands in. A list beside the stack names its layers, bottom to top, with the landing marked; a layer that is a container takes the widget inside, any other gives the widget its place in the stack, and past the top layer is a new one on top. |
| Release | Write and reload. The ghost stays until the reload lands. |
| `Alt` while dragging | Land on the exact pixel count instead of snapping. |
| `Delete` / `Backspace` | Remove the selected widget from the source — its whole expression, children included. No confirmation: `Ctrl+Z` brings it back. A handler or import the widget used stays behind for you or the agent to clean up. |
| `Enter`, or a second click on the selection | Edit its text in place. A field opens over the widget; `Enter` writes the new string into the literal the code passed (`text=` / `label=`, or the first argument), `Esc` or a click elsewhere cancels. The field edits like a text field: `Shift+←/→` selects, `Ctrl+A/C/X/V` (`Cmd` on macOS) select all, copy, cut and paste. Text that comes from a variable, an f-string or a function call cannot be edited here — the badge says so. |
| `Ctrl+Z` | Undo the last edit this mode wrote. |
| `Ctrl+Shift+Z` | Redo what `Ctrl+Z` undid. A new edit clears what could be redone. |
| `Esc` | Cancel the drag in flight; otherwise leave. |

The value written is one of the three sizes a widget accepts:

- `"auto"` when you release within a few pixels of the widget's natural size;
- `"wt"` when you release where a weight would put it — the full cross axis of
  a `Column`, or its share of the leftover on the main axis;
- the integer otherwise.

The caption says which (`w 240  |  h auto`). A widget with a `size` parameter
(`Icon`) stays square: the larger of the two deltas wins.

When one call builds many widgets — a helper returning a card, called from a
loop — every one of them gets a ghost and the caption counts them
(`14 widgets`), because the edit changes them all.

Some drags are **refused**: the badge says why, and the file is left
alone. That happens for:

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
    not import `GridItem`: the runner adds no import, so the badge asks for
    one;
- Align
  - an `alignment` / `cross_alignment` / `item_alignment` bound to a name or an
    expression;
  - a widget as big as its container on every axis it could align on —
    `"wt"`, or the same size — since there is nowhere for it to go;
- Either
  - a call the runner cannot find at the recorded line, or a widget built with
    no source recorded.

Other drags are not refused but simply **do nothing** — no badge, because no
line or rect was ever drawn to promise a change:

- Reorder
  - releasing the widget in its own slot, or its own grid cell;
  - releasing over a `Grid`'s padding, where there is no cell;
- Align
  - releasing on the alignment the container already has.

A drag inside a `Column` or `Row` reads by its dominant direction: along the
axis it reorders, across it aligns. In a `Flow` or `UniformFlow` any travel
that leaves the widget's slot reorders, and one that stays in it aligns — a
`Flow` only when it is mostly up or down. A `CrossAligned` you wrote yourself
is respected: dragging its child rewrites that value, and other children with
their own `CrossAligned` stay put when the container's alignment changes.

Over a `Stack`, one layer is read at a time, and the list beside the stack
says which. A widget dragged in from outside reads the top layer: into it if
that is a container, onto the stack — on top — otherwise, never into the
background box underneath. A widget that started inside the stack reads its
own layer wherever the pointer is, so a card under a floating button still
reorders in its column. `W` / `S` or a digit moves the landing to another
layer — the content column under a floating button, say — and the choice
holds until the pointer leaves the stack.

After the reload, the badge reports anything that did not go as the ghost
said: a size that landed elsewhere, a reload that failed on the edit, or a
`"wt"` whose meaning changed with the move — a share of the `Row`'s leftover
where it filled the `Column`'s width.

A widget that leaves a container can leave something behind. Out of a `Grid`,
its `GridItem` stays, and the badge names the `width` / `height` / `padding` /
`alignment` the item carried. Out of a `Container` or `Box`, the box stays,
empty — and an empty box takes a widget dropped on it as its `child`, while a
box that already has one is passed over, so the drop lands in the list around
it.

`Ctrl+Z` reverts any of this. The one exception is a line you have edited by
hand since: the undo is refused rather than applied to the wrong text.

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

## Jump to the source

`Ctrl+Shift+Click` (`Cmd+Shift+Click` on macOS) on a widget **opens the code
that built it**, in your editor. It is not a mode: it works with no mode on, and
inside comment mode or layout edit mode, where it opens the code instead of
marking or selecting — so you can read through several widgets without
leaving marks behind.

Hold `Ctrl+Shift` and the widget under the cursor gets **rose** brackets and a
caption naming its file and line, so you can aim before clicking — a different
colour from comment mode's amber, so inside that mode you can tell a jump from
a mark. After the click a
caption says what happened — `opening app.py:42`, or why nothing did — and
clears on the next pointer move.

VS Code works as installed. For another editor, pass its URL scheme to
`--editor` — `{file}` and `{line}` are filled in for you, encoding and all:

```bash
python -m nuiitivet.dev run app.py --editor "cursor://file{file}:{line}:1"
python -m nuiitivet.dev run app.py \
  --editor "jetbrains://pycharm/navigate/reference?project=NAME&path={file}:{line}"
```

`Ctrl+Shift` is the dev runner's prefix: every chord it claims — `Ctrl+Shift+C`,
`Ctrl+Shift+E`, `Ctrl+Shift+Click` — starts with it, and nothing else does.

## Next Steps

- [Dev Bridge MCP](dev_bridge_mcp.md) — what the agent sees and does in the
  same running app.
- [AI pair-programming](index.md) — the section overview.
