---
name: nuiitivet-see-comments
description: Read and act on the comments the user left in the running Nuiitivet app — the numbered marks and typed instructions from comment mode. Use when the user says `see_comments`, "see the comments", or refers to a mark by number ("#2", "the second one"). Reads the `see_comments` MCP tool, or `python -m nuiitivet.dev see-comments` when that tool is not registered.
user-invocable: true
---

# See the Comments

The user marked widgets and areas in the running app (comment mode,
`Ctrl+Shift+C`) and typed an instruction on some of them. Read the comments,
then do what they say, in one turn.

## Read

1. Call the `see_comments` MCP tool.
2. No tool of that name is registered → run, from the project root:

   ```
   python -m nuiitivet.dev see-comments
   ```

   It prints the same JSON. If it reports no running app, the app is not up
   under `python -m nuiitivet.dev run app.py`; ask the user to start it.

## Act

- `nodes` and `regions` share one numbering. `index` is the badge on the user's
  screen; "the second one" is `index: 2`.
- `instruction` is the user's instruction for that mark, in their words — an
  order, not a description. Do it. A mark with no `instruction` is still a
  comment: the user says what they mean in chat, by number. If they have not,
  ask by number — never guess.
- Several comments are one work order. Do every one, then answer per number:
  `#1 done: width 240 → 320`, `#2 refused: the value is an expression`.
- `active: true` → the user is still in comment mode and has not pressed
  `Enter`, so the set is not committed. Do not act on it: tell them that, or
  ask them to press `Enter`.
- `lost` > 0 → some marks did not survive a reload. Say so; never reason over
  a silently shortened list.
- Nothing marked → you cannot arm the mode or clear it. Ask the user to press
  `Ctrl+Shift+C`, click a widget or drag a box over the area, press `Enter`
  and type the instruction, then `Enter` twice.
- After your fix hot-reloads, call `see_comments` again to verify: nodes
  re-resolve to the rebuilt tree and regions are re-derived on every call.

## What a node carries

- `source` is the line that built it — edit there instead of searching.
  Innermost first; the `target: true` frame is the construction site and the
  rest are its callers, so a widget built by a shared helper shows both
  "change every one" and "change this one", and the instruction picks. Absent
  when the runner is not recording sites.
- `tree` / `state` are `describe_tree` / `describe_state` scoped to the node;
  read them instead of dumping the whole tree. `key` / `label` drive it with
  `click` / `type`; `path` locates it in `describe_tree`; `window` is the id to
  pass as `window=` when the node is not in the main window.
- No `key`, `label` or `target` on it is expected — most apps pass no `key=`.
  Its scoped `tree` tells two same-typed nodes apart (two bare buttons by the
  `Text` inside each), and `path` is how you reach it.
- `rect` is what is on screen of the node, clips applied — unlike
  `describe_tree`'s. A node clipped away entirely reports no `rect`.

## What a region carries

A region is an area the user dragged a box over, not a widget.

- `container` is the widget enclosing the box, with its immediate children;
  `contents` is a nested tree of what the box crosses, tagged `contained` /
  `clipped` (no tag = only on the path to a match).
- One box, two meanings: "the gap between these things" is `container`,
  "these things" is `contents`. Nothing is collapsed for you; the instruction
  picks.
- Empty `contents` is an answer, not a miss: nothing is painted there, and
  `container` names the widget that should have put something there.
