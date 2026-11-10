# Accessibility

The window assembles what its widgets say about themselves into a tree of
entries. A reader hands that tree to assistive technology.

## Overview

Two groups of modules take part, and the reader that asks them.

### Structure

```mermaid
flowchart LR
    semantics[The Semantics]
    tree[The Tree]
    reader[the reader]

    tree -- "semantics_node · describe() · parts()" --> semantics
    tree -- "activate() · adjust(part, direction)" --> semantics
    reader -- "semantics_tree() · perform_semantics_action(id, action)" --> tree
    tree -- "a SemanticsTree" --> reader
```

| Module | Role |
| --- | --- |
| The Semantics | the node, the value it answers in, the modifier that overrides the answer, the widgets that attach one |
| The Tree | the walk that turns the answers into entries, the focused entry, the actions |
| the reader | asks a window for its tree, sends an action back |

### Promises

- A widget says what it is. Only the window builds the tree.
- A widget's answer is read when the tree is built. Nothing is kept between
  two trees but the ids.
- A tree holds no widget. The reader names an entry by its id.
- The tree is asked for on the UI thread, after a layout.

## The Semantics

A `SemanticsNode` answers for the widget that carries it, in a `Semantics`
value. A widget that draws several controls itself answers for each as a
part, an entry beneath its own.

### Structure

```mermaid
flowchart LR
    widget[Widget]
    clickable[Clickable]
    text[TextBase]
    editable[EditableText]
    field[TextField]
    slider[_SliderBase]
    modifier["semantics()"]
    node[SemanticsNode]
    said[Semantics]
    scope[FocusScope]

    clickable & text & editable & slider -- "is a" --> widget
    widget -- "semantics_node" --> node
    clickable -- "attach_semantics(self, SemanticsNode(_semantics, on_activate))" --> node
    text -- "attach_semantics(self, SemanticsNode(_semantics))" --> node
    editable -- "attach_semantics(self, SemanticsNode(_semantics))" --> node
    field -- "semantics_node, the EditableText's · semantics_label" --> editable
    slider -- "SemanticsNode(_semantics, parts, on_adjust)" --> node
    slider -- "FocusScope(VirtualStopPolicy(count, get_current, set_current))" --> scope
    modifier -- "label · role" --> node
    node -- "returns, from describe() · parts()" --> said
```

| Module | Role |
| --- | --- |
| `Widget` | answers with its node, or with none |
| `Clickable` | the host most controls inherit; says it is a button unless a subclass says otherwise |
| `TextBase` | a text; says its string |
| `EditableText` | a text field; says its content |
| `TextField` | answers with its `EditableText`'s node, hands it the label |
| `_SliderBase` | a slider; a range slider is a group with its handles as parts |
| `semantics()` | writes a label, or one per part, and a role on the widget's node, attaching one when there is none |
| `SemanticsNode` | holds the id, the overrides, the callbacks into the widget |
| `Semantics` | what one entry says, an immutable value |
| `FocusScope` | the stops the parts line up with ([INTERACTION_ARCHITECTURE.md](INTERACTION_ARCHITECTURE.md)) |

### Promises

- A widget answers with one node or none. A widget that answers with none
  has no entry. Its children still have theirs.
- A widget may answer with a descendant's node. That node has one entry, at
  the outer widget's rect.
- A label or a role written by `semantics()` replaces the widget's own. A
  list of labels replaces the parts' own, in their order.
- A node's id lasts as long as the node. So does the id of each part.
- Node ids and part ids come from one counter. It never gives 0, the id of
  the window's entry.
- A host that has parts has one per stop of its focus scope, in the stops'
  order.

## The Tree

A `_Builder` walks a window once per request. It returns the entries with
the focused one, or carries one action to a widget.

### Structure

```mermaid
flowchart LR
    reader[the reader]
    window[Window]
    builder[_Builder]
    tree[SemanticsTree]
    entry[SemanticsEntry]
    hooks[the hooks]
    node[SemanticsNode]
    focus[FocusNode]
    scope[FocusScope]

    reader -- "semantics_tree() · perform_semantics_action(id, action)" --> window
    window -- "build_semantics_tree(self) · perform_semantics_action(self, id, action)" --> builder
    builder -- "_focus_traversal_root() · _focus_traversal_descendants(widget) · _focused_node · _last_input_source" --> window
    builder -- "blocks_focus_traversal" --> hooks
    builder -- "describe() · parts() · part_id(index) · activate() · adjust(part, direction)" --> node
    builder -- "policy.current_index() · policy.set_current(part)" --> scope
    builder -- "request_focus(KEYBOARD)" --> focus
    builder -- "SemanticsTree(entries, focus)" --> tree
    tree -- "entries, by id" --> entry
```

| Module | Role |
| --- | --- |
| the reader | asks for the tree, sends an action back |
| `Window` | `semantics_tree()` and `perform_semantics_action()`, the walk's root, the focused node, the last input source |
| `_Builder` | builds the entries from the nodes the walk meets, finds the focused entry, finds the node an action goes to |
| `SemanticsTree` | the entries by id, the window's own at the root, the id of the focused one |
| `SemanticsEntry` | one entry, with its rect, its children and the actions it takes |
| the hooks | what hides or narrows the walk ([INTERACTION_ARCHITECTURE.md](INTERACTION_ARCHITECTURE.md)) |
| `SemanticsNode` | the answers the entries are built from (The Semantics) |
| `FocusNode`, `FocusScope` | where the focus is, which stop is current ([INTERACTION_ARCHITECTURE.md](INTERACTION_ARCHITECTURE.md)) |

### Sequence

#### An action reaches a widget

```mermaid
sequenceDiagram
    participant R as the reader
    participant W as Window
    participant B as _Builder
    participant N as SemanticsNode
    participant F as FocusNode
    participant S as FocusScope

    R->>W: perform_semantics_action(id, action)
    W->>B: perform_semantics_action(self, id, action)
    B->>B: build the tree, find the entry and its node
    alt no such entry, or the entry does not list the action
        B-->>W: False
        W-->>R: False
    else
        B->>W: _last_input_source = KEYBOARD
        alt FOCUS
            B->>F: request_focus(KEYBOARD)
            opt the entry is a part
                B->>S: policy.set_current(part)
            end
        else ACTIVATE
            B->>N: activate()
        else INCREMENT or DECREMENT
            B->>N: adjust(part, direction)
        end
        B-->>W: True
        W-->>R: True
    end
```

### Promises

- The walk starts at the Tab sequence's root. It steps through the same
  children.
- A blocked widget that says nothing is left out with its subtree.
- A blocked host that says something keeps its entry. Nothing beneath it has
  one.
- An entry that is not a group, a menu or a radio group takes the text
  beneath it as its label when it has none. That text has no entry of its
  own.
- An entry with a label hides the text beneath it.
- The focused entry is the entry of the focused node's host, else of the
  nearest ancestor that has one, else the window's.
- When the focused host has parts, the focused entry is the part at its
  scope's current index.
- An action is looked up in the tree as it is at that moment.
- An action runs only when its entry lists it.
- A disabled entry lists no action.
- An action counts as keyboard input.
