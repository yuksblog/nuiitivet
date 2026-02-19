# Animation System Internal Design

## 1. Purpose and Scope

This document defines the **internal design** of nuiitivet animation primitives, centered on `Animatable`.

### In scope

- Runtime behavior of `Animatable` in `src/nuiitivet/animation/animatable.py`
- Motion contracts and state model in `src/nuiitivet/animation/motion.py`
- Value/vector conversion contracts in `src/nuiitivet/animation/converter.py`
- Integration patterns observed in `src/nuiitivet/material/*`

### Out of scope

- End-user tutorials and cookbook-style usage guides
- Full visual design catalog for transitions
- M3 design rationale not directly affecting runtime contracts

### Audience and reading path

- Widget authors should start with Section 10 and Section 11.
- For runtime guarantees and cleanup requirements, then read Section 5, Section 9, and Section 12.
- Section 7 and Section 8 are primarily for motion/converter implementers.

## 2. Terminology

- **value**: Current resolved animation value (`Animatable.value`).
- **target**: Destination value (`Animatable.target`).
- **retarget**: Updating `target` while animation is active.
- **tick**: One scheduler callback that advances state by `dt`.
- **done**: Motion completion state (`MotionState.done`).
- **visual-only animation**: Affects paint output only.
- **layout-affecting animation**: Affects measured size or child layout.

## 3. System Architecture

### 3.1 Components

- `Animatable[T]`
  - Owns value/target and ticking lifecycle.
  - Delegates motion math to `Motion`.
- `Motion`
  - Creates and updates mutable `MotionState`.
  - Handles retarget semantics.
- `VectorConverter[T]`
  - Converts domain values to/from numeric vectors.
- `runtime.clock`
  - Schedules per-frame callbacks.

### 3.2 Dependency direction

`Widget/material` -> `Animatable` -> `Motion` / `VectorConverter` -> `runtime.clock`

Animation primitives do not depend on material widget implementation details.

### 3.3 Widget entry points

Widget code should interact with animation primitives through three entry points:

- `target` assignment: drive animation from interaction/domain state.
- `subscribe(...)`: request redraw/layout or perform controlled side effects.
- `map(...)`: derive read-only observable values for property binding.

Do not access or mutate `Animatable` internals (`_state`, `_ticker`) from widget code.

## 4. Core Data Model and Invariants

### 4.1 `Animatable` internal state

`Animatable` maintains:

- `_value: _ObservableValue[T]`
- `_target: T`
- `_motion: Motion | None`
- `_state: MotionState | None`
- `_ticker: Callable[[float], None] | None`

### 4.2 `MotionState` fields

`MotionState` carries mutable simulation data:

- `value: list[float]`
- `target: list[float]`
- `start: list[float]`
- `elapsed: float`
- `velocity: list[float]`
- `done: bool`

### 4.3 Invariants

- `len(value) == len(target) == len(start) == len(velocity)` must hold.
- When done:
  - state value is snapped to state target,
  - `Animatable.value` equals converted target,
  - ticker is unscheduled.
- `stop()` must produce a quiescent state:
  - target is synchronized to current value,
  - velocity is zeroed,
  - done is set to true.

## 5. Lifecycle and State Transitions

### 5.1 Initialization

- Float mode: `Animatable(initial_value: float, motion=...)` uses `FloatConverter`.
- Generic mode: `Animatable.vector(initial, converter, motion=...)`.
- If `motion` is provided, initial `MotionState` is created with `value == target == initial`.

### 5.2 Target assignment

When assigning `anim.target = x`:

1. `_target` is updated.
2. If `motion is None`, `_value` is updated immediately (no ticking).
3. Else:
   - convert target to vector,
   - `create_state(...)` if missing, otherwise `retarget(...)`,
   - ensure ticker is scheduled.

### 5.3 Tick progression

On each `_tick(dt)`:

1. Guard: if motion/state missing, stop ticking.
2. Call `motion.step(state, dt)`.
3. Publish converted `state.value` to `_value`.
4. If done:
   - publish exact target value,
   - normalize `state.value = state.target.copy()`,
   - mark `state.done = True`,
   - unschedule ticker.

### 5.4 Stop

`stop()` must:

- unschedule ticker,
- set target to current value,
- normalize state vectors to current value,
- zero velocity,
- mark done.

### 5.5 Widget lifecycle integration

- Initialize animation wiring in construction/mount paths before first paint.
- If mount can change effective state (theme/focus/external observable), re-sync animation targets on mount.
- On unmount/dispose, stop animations that can continue ticking and dispose owned subscriptions/timers.
- Cleanup order should be: dispose subscriptions -> unschedule timers -> `stop()` active animatables -> clear refs.

## 6. Scheduler and Time Semantics

- Ticking is registered via `runtime.clock.schedule_interval(..., 1 / 60.0)`.
- Registration is idempotent (`_ticker` guard prevents duplicates).
- Unschedule is idempotent (`_ticker is None` guard).
- Motions clamp negative `dt` to `0.0`.
- Time-based motions with `duration <= 0.0` complete immediately.

## 7. Motion Contract Specification

`Motion` protocol defines:

- `create_state(value, target) -> MotionState`
- `step(state, dt) -> bool` (returns done)
- `retarget(state, target) -> None`

### 7.1 Linear/Bezier retarget policy

- `start` becomes current `state.value`.
- `target` becomes new target.
- `elapsed` resets to `0.0`.
- `done` resets to `False`.

### 7.2 Spring retarget policy

- `target` is replaced.
- Existing velocity is preserved.
- `done` resets to `False`.

### 7.3 Error behavior

- Dimension mismatch raises `ValueError`.
- `SpringMotion` initial velocity dimension mismatch raises `ValueError`.

## 8. VectorConverter Contract

`VectorConverter[T]` must satisfy:

- Stable vector dimensionality for a given `T` domain.
- Deterministic `to_vector`/`from_vector` behavior.
- Defensive validation in `from_vector` where required (e.g., RGBA length must be 4).

Implementation notes:

- `FloatConverter` maps scalar to one-dimensional vector.
- `RgbaTupleConverter` clamps channels to integer `[0, 255]`.

## 9. Observable Integration and Ownership

`Animatable` exposes `_ObservableValue` APIs:

- `subscribe(cb)`
- `changes()`
- `map(transform)`

Ownership rules:

- If subscription is created manually, caller owns disposal.
- If bound through framework host mechanisms, host manages lifecycle.
- Design docs must explicitly state ownership for every subscription site.

### 9.1 Ownership decision table

| Wiring style | Typical API | Disposal owner | Required action by widget author |
| --- | --- | --- | --- |
| Direct binding via host | framework-managed bind/observe API | Host/binding framework | Ensure dependency is registered correctly |
| Manual subscription | `anim.subscribe(...)` | Widget/component | Dispose on unmount/dispose |
| Timer + animation loop | scheduler callbacks + `Animatable` | Widget/component | Unschedule timer and stop animation on unmount |

## 10. Widget Integration Patterns (Developer-Facing)

This section intentionally uses **Pattern A/B/C** as the primary taxonomy because it is easier for widget authors to choose an implementation style.

### 10.1 Pattern A: Direct Property Binding (Preferred when possible)

Use `Animatable` (or `map(...)`) directly as an observable input to widget properties.

Responsibilities:

- Prefer this pattern for simple value propagation with minimal lifecycle code.
- Keep transformation logic pure and deterministic (`map(...)` should not have side effects).

Cautions:

- If the bound property affects geometry, ensure the target widget/property path triggers layout updates.
- Avoid heavy computations inside `map(...)` because it runs on every value publication.

Typical failures:

- Binding to a visual property while expecting layout updates.
- Hiding expensive work in a transform function and causing frame drops.

### 10.2 Pattern B: Manual Subscription (Low-level control)

Subscribe explicitly and perform imperative updates in the callback.

Responsibilities:

- Use when callback side effects are required (multiple property updates, conditional logic, external sync).
- Explicitly request repaint/layout based on the changed domain.

Cautions:

- If value changes affect geometry, call `mark_needs_layout()` (and typically `invalidate()`).
- Define disposal ownership clearly (manual subscriptions must be disposed by owner).
- Prevent retarget chatter with epsilon checks before assigning `target` repeatedly.

Typical failures:

- Calling only `invalidate()` for layout-affecting animation.
- Forgetting to dispose subscriptions on unmount/dispose.
- Reassigning the same target every frame and causing unnecessary work.

### 10.3 Pattern C: Late Read in `paint()` / `layout()`

Read `anim.value` during rendering/layout execution without synchronizing to an intermediate stored property.

Responsibilities:

- Use in custom widgets where direct pull-based reads keep state minimal.
- Pair with an external tick trigger (`subscribe(...)`) so paint/layout is re-requested while animation progresses.

Cautions:

- `paint()` / `layout()` must be read-only with respect to animation targets.
- Never assign `target` (or other state-changing operations) from paint-driven hot paths.
- For layout-driven animation, ensure layout invalidation is requested on ticks.

Typical failures:

- Infinite redraw loops caused by side effects in paint/layout.
- Stale geometry when `value` is read in layout but layout is not invalidated on updates.

### 10.4 Cross-check matrix (secondary review lens)

After choosing Pattern A/B/C, verify behavior by these orthogonal checks:

- **Visual-only**: repaint request is sufficient.
- **Layout-affecting**: layout + repaint requests are both wired.
- **State-sync retargeting**: source state changes update targets without chatter.

## 11. Material Integration Case Notes

### 11.1 Buttons

- Adopted pattern(s): **Pattern B + Pattern C**
- Separate animatables for state layer opacity and RGBA channels.
- Color animatables are created once, then retargeted.

### 11.2 TextField

- Adopted pattern(s): **Pattern B**
- Multiple coordinated animatables (`label_progress`, indicator width/color, label color).
- On mount, state is re-synchronized to avoid stale initial visual state.

### 11.3 NavigationRail

- Adopted pattern(s): **Pattern A + Pattern B + Pattern C**
- Multiple animatables synchronized from one expanded state.
- Uses `map(...)` for derived values (width, icon rotation).
- Layout class subscribes to animation ticks and requests layout+invalidate.

### 11.4 LoadingIndicator

- Adopted pattern(s): **Pattern B + Pattern C**
- Continuous loop via periodic retarget (`target += 1.0`).
- Requires strict unmount cleanup: unschedule timer, dispose subscription, stop animatable.

## 12. Failure Modes and Mitigations

### 12.1 Symptoms, likely causes, and fixes

- **Symptom**: animation stutters or CPU usage spikes while state is stable
  - Likely cause: repeated retargeting to effectively the same value
  - Fix: compare current target with epsilon before assignment

- **Symptom**: widget visually updates but geometry stays stale
  - Likely cause: layout-affecting animation only calls repaint
  - Fix: request both layout and repaint on animation ticks

- **Symptom**: redraw never settles / apparent render loop
  - Likely cause: side effects in `paint()`/`layout()` (including target assignments)
  - Fix: keep render/layout paths read-only and move state updates to event callbacks

- **Symptom**: callbacks fire after unmount / leaked work
  - Likely cause: manual subscriptions or timers not cleaned up
  - Fix: document ownership and execute unmount cleanup sequence

- **Symptom**: runtime `ValueError` in motion/converter paths
  - Likely cause: vector dimension mismatch
  - Fix: enforce dimension consistency in converter and motion boundaries

- **Symptom**: long-running loop animation drifts over time
  - Likely cause: unbounded floating-point accumulation
  - Fix: define tolerance and optional periodic phase normalization policy

## 13. Test Traceability

Current core behaviors are validated by tests such as:

- `tests/test_animatable_vector_driven.py`
  - float default converter behavior,
  - custom converter behavior,
  - in-flight retarget behavior,
  - spring multidimensional convergence.
- `tests/test_text_field_animation.py`
  - widget-level animation wiring and fake-clock stepping behavior.

Design changes must update this traceability section when adding or changing contracts.

### 13.1 Widget author test checklist

For any new widget animation, verify at least:

- Retarget-in-flight behavior (state changes during active animation).
- Correct invalidation kind:
  - repaint-only for visual changes,
  - layout + repaint for geometry changes.
- Unmount/dispose cleanup (no post-unmount callbacks, timers, or ticking).
- External observable sync correctness on initial mount and subsequent updates.

## 14. Future Extensions (Design Hooks)

- Pause/resume animation control API.
- Optional conversion-result caching for heavy value types.
- Explicit long-running loop policy (drift reset threshold, watchdog).
- Additional composition semantics for transitions (e.g., multiply/add blending).

---

## Appendix A: Minimal Internal Sequence

### A.1 In-flight retarget sequence

1. `target = A` schedules ticking and starts progression.
2. Before completion, `target = B` calls `retarget(...)`.
3. Motion continues from current state (not from original start).
4. Completion snaps to exact `B`, then ticker stops.

### A.2 Unmount cleanup sequence

1. Dispose subscriptions owned by widget.
2. Unschedule loop callbacks/timers.
3. Call `anim.stop()` if animation may still be active.
4. Clear references to avoid stale callbacks.
