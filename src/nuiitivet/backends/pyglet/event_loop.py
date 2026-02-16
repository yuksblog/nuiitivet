"""Custom pyglet event loop tuned for low-latency event handling."""

from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path
from typing import Callable, Optional, TYPE_CHECKING

import pyglet

from nuiitivet.common.logging_once import exception_once

logger = logging.getLogger(__name__)


if TYPE_CHECKING:
    from pyglet.window import Window


class ResponsiveEventLoop(pyglet.app.EventLoop):
    """Event loop that dispatches queued events immediately and manages draw cadence."""

    def __init__(
        self,
        window: "Window",
        draw_callback: Callable[[float], None],
        draw_fps: Optional[float] = 30.0,
    ) -> None:
        super().__init__()
        self._window = window
        self._draw_callback = draw_callback
        self._draw_interval = self._normalise_interval(draw_fps)
        self._next_draw_deadline: Optional[float] = None
        self._draw_pending = True
        self._heartbeat_ts = time.perf_counter()

        # Freeze diagnostics: track which part of the loop is running.
        self._phase: str = "init"
        self._phase_started: float = time.perf_counter()
        self._phase_last: dict[str, float] = {}
        self._phase_count: dict[str, int] = {}

        self._tick_count: int = 0
        self._last_draw_ts: float = time.perf_counter()
        self._last_events_ts: float = time.perf_counter()

        self._breadcrumb_path: Optional[str] = None
        self._breadcrumb_failed: bool = False

        self._planned_wait_seconds: Optional[float] = None

        self._freeze_backstop_reset: Optional[Callable[[], None]] = None
        self._freeze_backstop_last_reset: float = 0.0
        self._freeze_backstop_min_interval: float = 0.2

    def set_freeze_backstop_reset(self, reset_fn: Callable[[], None], *, min_interval_seconds: float = 0.2) -> None:
        """Install a callable that rearms a backstop traceback timer.

        The caller owns the implementation (typically `faulthandler.cancel_dump_traceback_later`
        + `faulthandler.dump_traceback_later`). We call this periodically from the
        main thread heartbeat so it only fires when the main loop stalls.
        """

        self._freeze_backstop_reset = reset_fn
        self._freeze_backstop_last_reset = 0.0
        self._freeze_backstop_min_interval = max(0.01, float(min_interval_seconds))

    def enable_freeze_breadcrumb(self, path: str) -> None:
        """Enable a single-line phase breadcrumb file.

        The file is overwritten on each phase transition. This is intended for
        freeze diagnosis when other threads cannot run.
        """

        self._breadcrumb_path = str(path)
        self._breadcrumb_failed = False
        try:
            Path(self._breadcrumb_path).parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            # Best-effort.
            pass

    def _write_breadcrumb(self) -> None:
        if self._breadcrumb_failed or not self._breadcrumb_path:
            return

        try:
            now = time.perf_counter()
            wall = time.time()
            phase = getattr(self, "_phase", "unknown")
            started = float(getattr(self, "_phase_started", now))
            age = max(0.0, now - started)
            hb_age = self.heartbeat_age_seconds()
            planned = self._planned_wait_seconds
            planned_s = "" if planned is None else f" planned_wait={planned:.6f}"

            tick = int(getattr(self, "_tick_count", 0))
            draw_pending = int(bool(getattr(self, "_draw_pending", False)))

            last_draw_ts = float(getattr(self, "_last_draw_ts", now))
            last_events_ts = float(getattr(self, "_last_events_ts", now))
            draw_age = max(0.0, now - last_draw_ts)
            events_age = max(0.0, now - last_events_ts)

            draw_interval = getattr(self, "_draw_interval", None)
            draw_cfg = "" if draw_interval is None else f" draw_interval={float(draw_interval):.6f}"

            next_deadline = getattr(self, "_next_draw_deadline", None)
            if next_deadline is None:
                deadline_s = ""
            else:
                deadline_s = f" next_draw_in={float(next_deadline - now):.6f}"

            line = (
                f"ts={now:.6f} wall={wall:.6f} pid={os.getpid()} "
                f"phase={phase} phase_age={age:.6f} heartbeat_age={hb_age:.6f}{planned_s}"
                f" tick={tick} draw_pending={draw_pending}"
                f" last_draw_age={draw_age:.6f} last_events_age={events_age:.6f}"
                f"{draw_cfg}{deadline_s}\n"
            )

            with open(self._breadcrumb_path, "w", encoding="utf-8") as f:
                f.write(line)
                f.flush()
        except Exception:
            self._breadcrumb_failed = True

    def _beat(self) -> None:
        now = time.perf_counter()
        self._heartbeat_ts = now

        reset = self._freeze_backstop_reset
        if reset is None:
            return
        if (now - float(self._freeze_backstop_last_reset)) < float(self._freeze_backstop_min_interval):
            return
        self._freeze_backstop_last_reset = now
        try:
            reset()
        except Exception:
            # Best-effort diagnostics only.
            self._freeze_backstop_reset = None

    def _enter_phase(self, name: str) -> None:
        now = time.perf_counter()
        try:
            prev = getattr(self, "_phase", "")
            started = float(getattr(self, "_phase_started", now))
            if prev:
                dur = max(0.0, now - started)
                self._phase_last[prev] = dur
                self._phase_count[prev] = int(self._phase_count.get(prev, 0)) + 1
        except Exception:
            # Best-effort diagnostics only.
            pass

        self._phase = str(name)
        self._phase_started = now
        self._write_breadcrumb()

    def freeze_debug_snapshot(self) -> dict[str, object]:
        """Return a small snapshot for freeze diagnostics logging."""

        now = time.perf_counter()
        phase = getattr(self, "_phase", "unknown")
        started = float(getattr(self, "_phase_started", now))
        age = max(0.0, now - started)

        last_draw_ts = float(getattr(self, "_last_draw_ts", now))
        last_events_ts = float(getattr(self, "_last_events_ts", now))
        draw_age = max(0.0, now - last_draw_ts)
        events_age = max(0.0, now - last_events_ts)

        draw_interval = getattr(self, "_draw_interval", None)
        next_deadline = getattr(self, "_next_draw_deadline", None)
        next_draw_in = None if next_deadline is None else float(next_deadline - now)

        # Copy to avoid mutation while watchdog prints.
        last = dict(getattr(self, "_phase_last", {}) or {})
        count = dict(getattr(self, "_phase_count", {}) or {})
        return {
            "phase": phase,
            "phase_age_seconds": age,
            "heartbeat_age_seconds": self.heartbeat_age_seconds(),
            "tick": int(getattr(self, "_tick_count", 0)),
            "draw_pending": bool(getattr(self, "_draw_pending", False)),
            "last_draw_age_seconds": draw_age,
            "last_events_age_seconds": events_age,
            "planned_wait_seconds": getattr(self, "_planned_wait_seconds", None),
            "draw_interval_seconds": None if draw_interval is None else float(draw_interval),
            "next_draw_in_seconds": next_draw_in,
            "phase_last_seconds": last,
            "phase_count": count,
        }

    def heartbeat_age_seconds(self) -> float:
        return max(0.0, time.perf_counter() - float(self._heartbeat_ts))

    def set_draw_fps(self, draw_fps: Optional[float]) -> None:
        """Update draw interval at runtime."""
        self._draw_interval = self._normalise_interval(draw_fps)
        if self._draw_interval is None:
            self._next_draw_deadline = None
        else:
            now = time.perf_counter()
            self._next_draw_deadline = now
            self._draw_pending = True

    def request_draw(self, immediate: bool = False) -> None:
        """Request the next loop iteration to trigger a draw."""
        self._draw_pending = True
        if immediate and self._draw_interval is not None:
            self._next_draw_deadline = time.perf_counter()

    def run(self) -> None:
        """Run the event loop.

        Defaults to the asyncio-driven loop. To force the synchronous loop (e.g. for debugging),
        set `NUIITIVET_PYGLET_SYNC=1`.
        """
        raw = os.environ.get("NUIITIVET_PYGLET_SYNC", "").strip().lower()
        use_sync = raw in {"1", "true", "yes", "on", "enable", "enabled"}

        if use_sync:
            self._run_sync()
            return

        import asyncio

        try:
            asyncio.run(self.run_async())
        except RuntimeError:
            logger.warning(
                "Async event loop is already running. "
                "Falling back to synchronous loop. "
                "Consider calling `await app.run_async()` instead."
            )
            self._run_sync()

    def _run_sync(self) -> None:
        from pyglet.window import Window

        self._draw_pending = True
        self._next_draw_deadline = time.perf_counter() if self._draw_interval is not None else None

        self.has_exit = False

        Window._enable_event_queue = False
        for window in pyglet.app.windows:
            window.switch_to()
            window.dispatch_pending_events()

        platform_loop = pyglet.app.platform_event_loop
        platform_loop.start()
        pyglet.app.event_loop = self
        self.dispatch_event("on_enter")
        self.is_running = True

        try:
            while not self.has_exit:
                self._enter_phase("tick")
                self._beat()
                self._tick_count += 1
                dt = self.clock.tick(poll=False)

                self._enter_phase("events")
                self._drain_events(platform_loop)
                self._last_events_ts = time.perf_counter()

                if not pyglet.app.windows:
                    self.exit()
                    break

                now = time.perf_counter()
                if self._should_draw(now):
                    self._enter_phase("draw")
                    self._perform_draw(dt, now)

                timeout = self._compute_sleep_timeout(now)
                try:
                    max_step = float(os.environ.get("NUIITIVET_PYGLET_MAX_STEP", "0.05"))
                except Exception:
                    max_step = 0.05
                if max_step <= 0.0:
                    max_step = 0.05

                if timeout is None:
                    timeout = max_step
                else:
                    timeout = min(float(timeout), max_step)

                if timeout <= 0.0:
                    continue

                # On macOS, Cocoa's nextEventMatchingMask may effectively ignore
                # untilDate while the run loop is in a tracking mode (e.g.
                # window move/resize), causing long blocking even with a
                # nominal timeout. Sleep in Python and then poll events
                # non-blocking to keep the loop responsive.
                if sys.platform == "darwin":
                    self._planned_wait_seconds = float(timeout)
                    deadline = time.perf_counter() + float(timeout)
                    # Keep pumping the platform loop during the wait.
                    # Sleeping for the full timeout in one go can make the
                    # app feel unresponsive while Cocoa is in tracking modes.
                    sleep_slice = 0.005
                    while not self.has_exit:
                        self._enter_phase("poll")
                        platform_loop.step(0.0)
                        remaining = deadline - time.perf_counter()
                        if remaining <= 0.0:
                            break
                        self._enter_phase("sleep")
                        time.sleep(min(float(remaining), sleep_slice))
                else:
                    self._planned_wait_seconds = float(timeout)
                    self._enter_phase("step")
                    platform_loop.step(timeout)

                self._planned_wait_seconds = None
        finally:
            self.is_running = False
            try:
                self.dispatch_event("on_exit")
            finally:
                platform_loop.stop()

    async def run_async(self) -> None:
        """Run the event loop asynchronously."""
        import asyncio
        from pyglet.window import Window

        self._draw_pending = True
        self._next_draw_deadline = time.perf_counter() if self._draw_interval is not None else None

        self.has_exit = False

        Window._enable_event_queue = False
        for window in pyglet.app.windows:
            window.switch_to()
            window.dispatch_pending_events()

        platform_loop = pyglet.app.platform_event_loop
        platform_loop.start()
        pyglet.app.event_loop = self
        self.dispatch_event("on_enter")
        self.is_running = True

        try:
            while not self.has_exit:
                self._beat()
                dt = self.clock.tick(poll=False)
                self._drain_events(platform_loop)

                if not pyglet.app.windows:
                    self.exit()
                    break

                now = time.perf_counter()
                if self._should_draw(now):
                    self._perform_draw(dt, now)

                timeout = self._compute_sleep_timeout(now)
                if timeout is None:
                    # No timeout: wait indefinitely for an event
                    # But we must yield to asyncio loop
                    await asyncio.sleep(0.001)
                    platform_loop.step(0.0)
                elif timeout <= 0.0:
                    # Immediate timeout
                    await asyncio.sleep(0)
                    continue
                else:
                    # Wait for timeout or event
                    # We use a small slice to allow asyncio tasks to run
                    # TODO: This is a busy loop if timeout is large.
                    # Ideally we should wait on a file descriptor or similar.
                    # For now, we cap the sleep to a small value to keep UI responsive
                    # and allow other tasks to run.
                    sleep_time = min(timeout, 0.016)  # Max 16ms sleep
                    await asyncio.sleep(sleep_time)
                    platform_loop.step(0.0)

        finally:
            self.is_running = False
            try:
                self.dispatch_event("on_exit")
            finally:
                platform_loop.stop()

    def _normalise_interval(self, draw_fps: Optional[float]) -> Optional[float]:
        if draw_fps is None:
            return None
        fps_value = float(draw_fps)
        if fps_value <= 0:
            return None
        return 1.0 / fps_value

    def _dispatch_window_events(self) -> None:
        for window in list(pyglet.app.windows):
            window.dispatch_events()
            if getattr(window, "has_exit", False):
                self.exit()
                break

    def _drain_events(self, platform_loop) -> None:
        platform_loop.dispatch_posted_events()
        self._dispatch_window_events()

        # Avoid starving rendering when events arrive continuously.
        # If we drain indefinitely (e.g., rapid clicks/motion), the UI can
        # appear frozen because draw never runs.
        start = time.perf_counter()
        max_spins = 500
        spins = 0
        while not self.has_exit:
            timed_out = platform_loop.step(0.0)
            platform_loop.dispatch_posted_events()
            self._dispatch_window_events()
            if timed_out:
                break
            spins += 1
            if spins >= max_spins or (time.perf_counter() - start) >= 0.005:
                break

    def _should_draw(self, now: float) -> bool:
        # If no draw cadence is configured, draw only when explicitly requested.
        if self._draw_interval is None or self._next_draw_deadline is None:
            return bool(self._draw_pending)

        # With a cadence, draw when the deadline is reached.
        # Also respect explicit requests for an immediate frame.
        return bool(self._draw_pending) or now >= self._next_draw_deadline

    def _perform_draw(self, dt: float, now: float) -> None:
        self._draw_pending = False
        self._last_draw_ts = float(now)
        try:
            self._draw_callback(dt)
        except Exception:
            exception_once(logger, "pyglet_event_loop_draw_callback_exc", "Draw callback raised")
        finally:
            if self._draw_interval is not None:
                self._next_draw_deadline = now + self._draw_interval

    def _compute_sleep_timeout(self, now: float) -> Optional[float]:
        clock_timeout = self.clock.get_sleep_time(True)
        if clock_timeout is not None and clock_timeout < 0:
            clock_timeout = 0.0

        # When a draw cadence is configured, always wake for draw deadlines.
        if self._draw_interval is not None and self._next_draw_deadline is not None:
            remaining = self._next_draw_deadline - now
            draw_timeout = 0.0 if remaining <= 0 else remaining
            if clock_timeout is None:
                return draw_timeout
            return min(clock_timeout, draw_timeout)

        # No cadence: draw only when explicitly requested.
        if self._draw_pending:
            draw_timeout = 0.0
            if clock_timeout is None:
                return draw_timeout
            return min(clock_timeout, draw_timeout)

        return clock_timeout
