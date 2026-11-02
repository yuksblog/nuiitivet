# Navigation

A `Navigator` holds a stack of screens and paints the top one. `Overlay` is
built on the same kernel ([OVERLAY.md](OVERLAY.md)).

## Overview

Four groups of modules take part: the window that owns the root navigator,
the navigator package, the transition kernel both stacks stand on, and the
Material layer that subclasses the navigator. The overlay, the reload
snapshot, the `will_pop` modifier and a ViewModel stand at their edges.

### Structure

```mermaid
flowchart LR
    window[The Window]
    navigation[The Navigator]
    kernel[The Kernel]
    material[The Material Layer]
    overlay[overlay/overlay.py]
    snapshot[dev/navigation_snapshot.py]
    willpop[modifiers/will_pop.py]
    vm[a ViewModel]

    window -- "the root navigator · request_back" --> navigation
    window -- "async_request_close_topmost · occluding_content_widget" --> overlay
    navigation -- "StackRuntime · TransitionEngine · TransitionSpec" --> kernel
    overlay -- "StackRuntime" --> kernel
    material -- "subclasses, with its composer and default spec" --> navigation
    snapshot -- "snapshot_stack · restore_stack" --> navigation
    navigation -- "handle_back_event" --> willpop
    vm -- "NavigatorProtocol" --> navigation
```

| Module | Role |
| --- | --- |
| The Window | holds the root navigator and routes a back action |
| The Navigator | keeps the stack of routes, resolves a push, paints the top, absorbs back requests |
| The Kernel | tracks when an element enters, stays and exits a stack; drives the progress of a transition |
| The Material Layer | subclasses the navigator with the Material default and composer |
| `overlay/overlay.py` | the layers above the screen, offered a back action first ([OVERLAY.md](OVERLAY.md)) |
| `dev/navigation_snapshot.py` | saves the route log before a reload and replays it after ([HOT_RELOAD.md](HOT_RELOAD.md)) |
| `modifiers/will_pop.py` | lets a screen refuse to be popped ([MODIFIER.md](MODIFIER.md)) |
| a ViewModel | app code that pushes and pops through `NavigatorProtocol` |

### Promises

- `navigation` and `overlay` import neither the other. Both import
  `transition`.
- A screen enters the tree only as the widget of a route.

## The Window

The window holds the root navigator and routes a back action.

### Structure

```mermaid
flowchart LR
    content[the content factory]
    window[Window]
    navigator[Navigator]
    overlay[Overlay]

    content -- "a Navigator, or a plain widget" --> window
    window -- "Navigator(widget) for a plain root · request_back()" --> navigator
    window -- "has_entries · async_request_close_topmost · occluding_content_widget" --> overlay
```

| Module | Role |
| --- | --- |
| the content factory | the window's `content`, returning the root |
| `Window` | holds the root navigator, wraps a plain root in the implicit one (`MaterialApp` overrides the wrap), offers a back action to the overlay and then the navigator |
| `Navigator` | the stack of screens (The Navigator) |
| `Overlay` | the layers above the screen ([OVERLAY.md](OVERLAY.md)) |

### Sequence

#### A back action

```mermaid
sequenceDiagram
    participant W as Window
    participant O as Overlay
    participant N as Navigator

    W->>O: has_entries()
    alt an entry is open
        W->>O: async_request_close_topmost()
        alt an entry closed
            O-->>W: handled
        else nothing closed, an entry still occludes
            Note over W: stops here
        else nothing closed, nothing occludes (a pass-through entry)
            W->>N: request_back()
            N-->>W: handled, or False at the root route
        end
    else no entry
        W->>N: request_back()
        N-->>W: handled, or False at the root route
    end
```

### Promises

- A window owns one root navigator. A plain widget given as the content is
  wrapped in one.
- A back action never reaches past an occluding overlay entry, an entry
  animating out included. A pass-through entry blocks nothing.
- The window handles one request per input.

## The Navigator

The navigator keeps routes on a stack from the kernel, resolves a push to a
route, paints through a layer composer, and absorbs back requests.

### Structure

```mermaid
flowchart LR
    navigator[Navigator]
    route[Route]
    stack["StackRuntime[Route]"]
    engine[TransitionEngine]
    composer[NavigationLayerComposer]
    proto[NavigatorProtocol]
    routes[the intent table]
    screen[the outgoing screen]
    snapshot[dev/navigation_snapshot.py]

    navigator -- "Route(widget, transition)" --> route
    navigator -- "push · mark_active · mark_exiting · complete_exit" --> stack
    navigator -- "start(progress, motion, on_complete)" --> engine
    navigator -- "paint_static · paint_transition" --> composer
    navigator -- "the factory for an intent's type" --> routes
    navigator -- "handle_back_event(), before a pop" --> screen
    navigator -. "implements" .-> proto
    snapshot -- "snapshot_stack · restore_stack" --> navigator
```

| Module | Role |
| --- | --- |
| `Navigator` | `push` turns a widget or an intent into a route and starts the enter transition; `pop` and `request_back` take one route off, absorbing requests during a transition; `of` finds the navigator a widget drives; `paint` draws the top route or a transition frame; `_restore_log` keeps a descriptor per push |
| `Route` | a screen and the transition it moves with; disposing it unmounts the screen |
| `StackRuntime[Route]` | the stack from the kernel (The Kernel) |
| `TransitionEngine` | drives the progress of a transition (The Kernel) |
| `NavigationLayerComposer` | the paint of a static screen and of a transition frame |
| `NavigatorProtocol` | the three methods a ViewModel is typed against |
| the intent table | `Navigator.routes`: an intent type to the factory that builds its screen, or its screen and transition |
| the outgoing screen | asked before a pop; the question is forwarded down its built tree to a `will_pop` modifier |
| `dev/navigation_snapshot.py` | the reload's read and replay of the log ([HOT_RELOAD.md](HOT_RELOAD.md)) |

### Sequence

#### A screen is pushed and popped

```mermaid
sequenceDiagram
    participant N as Navigator
    participant S as StackRuntime
    participant E as TransitionEngine
    participant C as layer composer
    participant R as the new Route

    N->>S: push(B), mark_active(B)
    N->>E: start(0 → 1, motion: B.enter)
    loop each frame
        E->>N: progress
        N->>C: paint_transition(from A via A.exit_, to B via B.enter)
    end
    E->>N: complete
    Note over N,C: paint_static(B) from here
    N->>N: pop()
    N->>S: mark_exiting(B)
    N->>E: start(1 → 0, motion: B.exit_back)
    loop each frame
        E->>N: progress
        N->>C: paint_transition(from B via B.exit_back, to A via A.enter_back)
    end
    E->>N: complete
    N->>S: complete_exit(B)
    S->>R: dispose() → unmount
```

#### A back request reaches the navigator

```mermaid
sequenceDiagram
    participant W as Window
    participant N as Navigator
    participant E as TransitionEngine
    participant S as the outgoing screen

    W->>N: request_back()
    alt a pop is in flight
        N->>N: pending_pop_requests += 1
        N->>E: finish the running pop at once
        loop while pending_pop_requests > 0
            N->>N: _pop_once(skip_animation = not the last)
        end
    else a push is in flight
        N->>E: finish the push at once
        N->>N: _pop_once()
    else idle
        N->>N: _pop_once()
    end
    Note over N,S: inside each _pop_once
    N->>S: handle_back_event() down to will_pop
    alt the screen refuses
        S-->>N: False
        N->>N: pending_pop_requests = 0
    else the screen allows
        S-->>N: True
        N->>E: start the pop
    end
```

#### The stack is restored after a reload

```mermaid
sequenceDiagram
    participant C as dev/controller.py
    participant S as dev/navigation_snapshot.py
    participant Old as the navigator before the reload
    participant New as the navigator after the reload

    C->>S: snapshot_navigation()
    S->>Old: snapshot_stack()
    Old-->>S: the restore log, bottom to top
    C->>C: rebuild the content from the window's factory
    C->>S: restore_navigation(log)
    S->>New: restore_stack(log)
    loop each entry
        alt an intent still registered
            New->>New: resolve it, push the route without animation
        else a widget push, or an intent no longer registered
            Note over New: replay stops, the screens above are lost
        end
    end
```

### Promises

- A screen's transition is held by its route until the route is disposed.
- A screen pushed with no transition moves with the navigator's default.
- Outside a transition only the top route is painted. The routes beneath
  stay mounted.
- Each screen of a transition is painted through its own spec.
- The restore log replays intent pushes only.
- Queued pops run without animation, except the last.
- No pop starts against the outgoing screen's refusal. A refusal discards
  the queue.
- A refused pop still counts as handled.

## The Kernel

The kernel tracks when an element enters, stays and exits a stack, and
drives the progress of a transition. It knows nothing of screens or layers.

### Structure

```mermaid
flowchart LR
    navigator[Navigator]
    overlay[Overlay]
    stack[StackRuntime]
    entry[StackEntry]
    engine[TransitionEngine]
    handle[TransitionHandle]
    spec[TransitionSpec]
    phase[TransitionPhase]
    element[an element]

    navigator & overlay -- "push · mark_active · mark_exiting · complete_exit" --> stack
    navigator -- "start(start, target, apply, on_complete, motion)" --> engine
    stack -- "holds" --> entry -- "element · lifecycle" --> element
    stack -- "dispose() on complete_exit" --> element
    engine -- "returns" --> handle
    navigator -- "cancel()" --> handle
    spec -- "the motion of a phase: enter · exit_ · enter_back · exit_back" --> phase
```

| Module | Role |
| --- | --- |
| `Navigator`, `Overlay` | the two stacks built on the kernel (The Navigator, [OVERLAY.md](OVERLAY.md)) |
| `StackRuntime` | the ordered elements and their lifecycle: entering, active, exiting, disposed |
| `StackEntry` | one element with its lifecycle state |
| `TransitionEngine` | animates one progress from start to target and reports completion |
| `TransitionHandle` | cancels a running transition |
| `TransitionSpec`, `EmptyTransitionSpec` | the four motions of a screen; the spec that moves nothing |
| `TransitionPhase` | which of the four motions a frame is in |
| an element | a `Route`, or an overlay layer; anything with `dispose()` |

### Promises

- The stack holds any element with a `dispose()`. It disposes an element
  when its exit completes.
- The engine drives one progress per transition and reports completion once.

## The Material Layer

The Material navigator subclasses `Navigator` with its own composer and its
own default.

### Structure

```mermaid
flowchart LR
    app["MaterialApp._build_default_navigator"]
    matnav[MaterialNavigator]
    matcomposer[MaterialNavigationLayerComposer]
    specs["MaterialTransitions.page()"]
    navigator[Navigator]
    composer[NavigationLayerComposer]

    app -- "MaterialNavigator(content)" --> matnav
    matnav -- "is a" --> navigator
    matnav -- "layer_composer=" --> matcomposer -- "is a" --> composer
    matnav -- "_default_transition()" --> specs
```

| Module | Role |
| --- | --- |
| `MaterialApp._build_default_navigator` | wraps a plain root in a `MaterialNavigator` |
| `MaterialNavigator` | the navigator with the Material default and composer |
| `MaterialNavigationLayerComposer` | paints the Material motion of a transition |
| `MaterialTransitions.page()` | the page transition every Material screen moves with by default |
| `Navigator`, `NavigationLayerComposer` | what the Material classes subclass (The Navigator) |

### Promises

- `MaterialNavigator` adds no navigation API.
- The default transition is a subclass hook. `Navigator` defaults to the
  empty spec; `MaterialNavigator` to the page transition.
