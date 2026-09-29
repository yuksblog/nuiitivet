# Programming Paradigms

nuiitivet is built to be intuitive: the developer's mental model and the code
say the same thing. No single paradigm does that for every part of a UI, so
three are used, each where it reads most naturally.

| Part of the UI | Paradigm | Why |
| --- | --- | --- |
| What is on screen: the widget tree and its modifiers | Declarative | A static structure reads best as a structure. |
| Keeping display and state in step | Data binding to `Observable`s | "When the data changes, the display changes" is a causal rule, and a reactive mechanism keeps it consistent without code per change. |
| What happens after a user action | Imperative, in an event handler | A flow through time reads and debugs best as a sequence of steps. |

## Components on the Boundary

Some components are part of the structure and part of a flow. Each is placed
by which half dominates.

A **dialog** is declared as a widget and shown imperatively: an event handler
`await`s `Overlay.dialog(...)` and receives the result, because a dialog is a
conversation with the user and its result belongs to the flow that opened it.
A **snackbar** is fire-and-forget, one imperative call, because it is a
notification with no result to wait for. A **tooltip** is fully declarative,
a wrapper around the widget it describes, because it is an attribute of that
widget rather than an event.

A ViewModel never creates a widget. It issues an **intent**, a data class
naming what it wants shown, to a protocol (`OverlayProtocol`,
`NavigatorProtocol`), and the View layer maps the intent to a widget where
the overlay or navigator is configured. The framework ships the standard
intents (`BasicDialogIntent`); an application registers its own. The protocol
object is passed to the ViewModel method per call, resolved by the handler
with `.of(self)`, rather than stored in the ViewModel's constructor: widgets
build their ViewModel in `__init__`, where every `.of()` lookup fails because
the widget has no ancestors yet. The same shape serves `Navigator` and
`Overlay`, so a ViewModel is written one way for both and tested with a fake
protocol.

## Navigation

Navigation mixes a change of state, declarative, with the user moving,
imperative. The patterns are chosen by what the back history should contain:

- **A wizard** switches the content of one screen on a state value (a `Deck`
  index, or a `map` over the step), with no `Navigator`: tightly coupled
  steps do not belong in the back history.
- **Parallel screens**, tabs or a drawer, switch between independent screens
  with a `Deck`: each keeps its state, scroll position included, and there is
  no back history between them.
- **Standard navigation**, list to detail, a checkout, pushes and pops routes
  on a `Navigator`. The data (a cart's contents) stays reactive in a service
  or ViewModel; only the timing of the transition is imperative, in the
  handler.
- **Intent-based navigation** is standard navigation from a ViewModel: the
  ViewModel pushes an intent and `Navigator.intents(...)` maps it to a screen,
  so the ViewModel knows no widget and the routing is typed.
- **Nested navigation** hosts an independent `Navigator` inside each parallel
  screen, so each tab keeps its own history.

Declarative routing from a URL or deep link, a router that rebuilds the
navigator stack from a path, is not provided; nothing in a desktop app has
asked for it.
