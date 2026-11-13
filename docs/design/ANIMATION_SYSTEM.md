# Animation System

An animation is a value that moves toward a target. A widget assigns the
target and subscribes to the value.

## Overview

Four groups of modules take part.

### Structure

```mermaid
flowchart LR
    animatable[The Animatable]
    motions[The Motions]
    kernel[The Transition Kernel]
    definitions[The Definitions]
    clock[observable/runtime.py]
    widgets[the widgets]
    stacks[navigation/navigator.py · overlay/overlay.py]
    material[material/]

    widgets -- "target = v · subscribe(cb) · map(fn) · stop()" --> animatable
    animatable -- "create_state · step(state, dt) · retarget(state, target)" --> motions
    animatable -- "schedule_interval(tick, 1/60) · unschedule(tick)" --> clock
    kernel -- "Animatable(start, motion) · target = 1.0" --> animatable
    stacks -- "start(start, target, apply, on_complete, motion) · push · mark_active · mark_exiting · TransitionState.create(spec)" --> kernel
    material -- "TransitionDefinition(motion, pattern) · FadePattern · ScalePattern · SlidePattern" --> definitions
    material -- "BezierMotion · SpringMotion" --> motions
    kernel -- "definition.motion" --> definitions
    definitions -- "motion" --> motions
```

| Module | Role |
| --- | --- |
| The Animatable | the retargetable value |
| The Motions | the arithmetic of one step |
| The Transition Kernel | the enter and exit driver, and a stack's bookkeeping |
| The Definitions | the building block of a design system's transitions |
| `observable/runtime.py` | the clock a tick is scheduled on ([OBSERVABLE.md](OBSERVABLE.md)) |
| the widgets | assign targets and bind values |
| `navigation/navigator.py · overlay/overlay.py` | the two stacks the kernel serves ([NAVIGATION.md](NAVIGATION.md), [OVERLAY.md](OVERLAY.md)) |
| `material/` | the MD3 definitions and the visual resolution ([MATERIAL_INTERACTION.md](MATERIAL_INTERACTION.md)) |

### Promises

- No widget drives a timeline by hand.
- `animation/` and `transition/` import nothing from `widgeting/`.

## The Animatable

`Animatable[T]` owns the current value and the target.

### Structure

```mermaid
flowchart LR
    animatable[animation/animatable.py]
    motion[animation/motion.py]
    converter[animation/converter.py]
    clock[observable/runtime.py]
    value[observable/value.py]
    widgets[the widgets]

    widgets -- "Animatable(initial, motion) · Animatable.vector(initial, converter, motion) · target = v · snap_to(v) · set_motion(m) · stop()" --> animatable
    widgets -- "subscribe(cb) · map(fn) · value" --> animatable
    animatable -- "create_state(value, target) · step(state, dt) · retarget(state, target)" --> motion
    animatable -- "to_vector(value) · from_vector(vector)" --> converter
    animatable -- "schedule_interval(_tick, 1/60) · unschedule(_tick)" --> clock
    animatable -- "the published value" --> value
```

| Module | Role |
| --- | --- |
| `animation/animatable.py` | `Animatable`: the value, the target, the motion state, the ticker |
| `animation/motion.py` | advances a state (The Motions) |
| `animation/converter.py` | maps a domain value to a vector of floats and back |
| `observable/runtime.py` | the clock ([OBSERVABLE.md](OBSERVABLE.md)) |
| `observable/value.py` | the `State` the value is published through ([OBSERVABLE.md](OBSERVABLE.md)) |
| the widgets | assign a target, bind the value |

### Sequence

#### A target is assigned

```mermaid
sequenceDiagram
    participant W as the widgets
    participant A as animation/animatable.py
    participant M as animation/motion.py
    participant C as animation/converter.py
    participant K as observable/runtime.py

    W->>A: target = v
    alt no motion
        A->>A: value = v
    else
        A->>M: create_state(current, target), or retarget(state, target)
        A->>K: schedule_interval(_tick, 1/60), once
        loop each tick
            K->>A: _tick(dt)
            A->>M: step(state, dt)
            A->>C: from_vector(state.value)
            A->>A: publish the value
        end
        A->>C: from_vector(state.target), on done
        A->>A: publish the exact target
        A->>K: unschedule(_tick)
    end
```

### Promises

- An animatable ticks only while its value differs from its target.
- Without a motion the value jumps to the target.
- The last published value is the exact target.

## The Motions

A `Motion` creates a state, advances it by `dt` and retargets it.

### Structure

```mermaid
flowchart LR
    motion[animation/motion.py]
    animatable[animation/animatable.py]
    mmotion[material/motion.py]

    animatable -- "create_state(value, target) · step(state, dt) · retarget(state, target)" --> motion
    mmotion -- "BezierMotion(x1, y1, x2, y2, duration) · SpringMotion(stiffness, damping_ratio)" --> motion
```

| Module | Role |
| --- | --- |
| `animation/motion.py` | `MotionState`, vectors of one dimension; `LinearMotion` and `BezierMotion`, time-based; `SpringMotion`, physics |
| `animation/animatable.py` | the caller (The Animatable) |
| `material/motion.py` | the MD3 curves ([MATERIAL_INTERACTION.md](MATERIAL_INTERACTION.md)) |

### Promises

- A retarget never reverses. It never restarts from the original start.
- A time-based motion continues from the current value with its elapsed
  time reset. A spring keeps its velocity.

## The Transition Kernel

The kernel drives one enter or exit from 0 to 1. It tracks which entries of
a stack are entering, active and exiting.

### Structure

```mermaid
flowchart LR
    engine[transition/engine.py]
    spec[transition/spec.py]
    state[transition/state.py]
    stack[transition/stack.py]
    animatable[animation/animatable.py]
    definitions[animation/transition_definition.py]
    hosts[navigation/navigator.py · overlay/overlay.py]
    material[material/]

    hosts -- "start(start, target, apply, on_complete, motion) · cancel(token)" --> engine
    engine -- "Animatable(start, motion) · target · subscribe" --> animatable
    hosts -- "resolve_phase_motion(spec, phase, back) · Transitions.empty()" --> spec
    spec -- "definition.motion" --> definitions
    hosts -- "TransitionState.create(spec) · phase_obs · progress_obs" --> state
    hosts -- "push(element) · mark_active · mark_exiting · pop · elements · can_pop" --> stack
    material -- "transition_state.transition_spec · phase · progress" --> state
```

| Module | Role |
| --- | --- |
| `transition/engine.py` | `TransitionEngine`: one animatable from 0 to 1 per transition, a token per start, the exact completion |
| `transition/spec.py` | `TransitionSpec`, an opaque lifecycle token, and `Transitions.empty()`, the token with no motion; the lookup of a phase's motion |
| `transition/state.py` | `TransitionState`: the phase and the progress as `State`s |
| `transition/stack.py` | `StackRuntime`: the entries by identity, each entering, active, exiting or disposed |
| `animation/animatable.py` | the value the engine drives (The Animatable) |
| `animation/transition_definition.py` | where a spec's motion comes from (The Definitions) |
| `navigation/navigator.py · overlay/overlay.py` | the hosts, which render and animate ([NAVIGATION.md](NAVIGATION.md), [OVERLAY.md](OVERLAY.md)) |
| `material/` | resolves the visuals from the state ([MATERIAL_INTERACTION.md](MATERIAL_INTERACTION.md)) |

### Sequence

#### A transition is started and completes

```mermaid
sequenceDiagram
    participant H as the host
    participant E as transition/engine.py
    participant A as animation/animatable.py

    H->>E: start(start=0, target=1, apply, on_complete, motion)
    E->>E: a new token, the active one
    E->>A: Animatable(start, motion), subscribe
    E->>A: target = 1
    loop each published value
        A->>E: the value
        E->>H: apply(value)
    end
    E->>E: within epsilon of the target, the token still active
    E->>H: apply(1.0), on_complete()
```

### Promises

- A core `TransitionSpec` carries no visual policy.
- A completion whose token is no longer active is dropped.

## The Definitions

A `TransitionDefinition` pairs a motion with a pattern from progress to
visuals.

### Structure

```mermaid
flowchart LR
    definition[animation/transition_definition.py]
    pattern[animation/transition_pattern.py]
    lerp[animation/interpolate.py]
    motion[animation/motion.py]
    material[material/]

    material -- "TransitionDefinition(motion, pattern) · a | b" --> definition
    definition -- "motion" --> motion
    definition -- "pattern.resolve(progress) · CompositePattern(a, b)" --> pattern
    pattern -- "lerp(begin, end, t)" --> lerp
    material -- "FadePattern · SlidePattern · ScalePattern · FractionalSlidePattern" --> pattern
```

| Module | Role |
| --- | --- |
| `animation/transition_definition.py` | `TransitionDefinition`, a motion and a pattern; the pipe operator composes two |
| `animation/transition_pattern.py` | the patterns, each resolving a progress into `TransitionVisuals`; the merge of two |
| `animation/interpolate.py` | the interpolation arithmetic |
| `animation/motion.py` | the motion a definition carries (The Motions) |
| `material/` | builds the MD3 definitions ([MATERIAL_INTERACTION.md](MATERIAL_INTERACTION.md)) |

### Promises

- `a | b` keeps the left definition's motion. Both patterns apply.
- A pattern maps progress to visuals and nothing else.
