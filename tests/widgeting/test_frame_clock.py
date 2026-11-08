"""The frame clock: the loop says when a frame begins and ends, and how long a frame is."""

from time import perf_counter

import pytest

from nuiitivet.widgeting import frame_clock
from nuiitivet.widgeting.frame_clock import (
    DEFAULT_FRAME_INTERVAL,
    begin_frame,
    end_frame,
    frame_deadline,
    frame_interval,
    frame_started_at,
    set_frame_interval,
)


@pytest.fixture(autouse=True)
def fresh_clock():
    frame_clock._interval = DEFAULT_FRAME_INTERVAL
    frame_clock._started_at = None
    yield
    frame_clock._interval = DEFAULT_FRAME_INTERVAL
    frame_clock._started_at = None


def test_the_deadline_is_a_share_of_the_frame_from_its_start():
    set_frame_interval(0.020)
    started = perf_counter()
    begin_frame(started)

    assert frame_started_at() == started
    assert frame_deadline(0.5) == pytest.approx(started + 0.010)
    assert frame_deadline(0.0) == pytest.approx(started)


def test_between_frames_there_is_no_deadline():
    assert frame_started_at() is None
    assert frame_deadline(0.5) is None

    begin_frame(perf_counter())
    end_frame()
    assert frame_started_at() is None
    assert frame_deadline(0.5) is None


def test_the_interval_has_a_floor_and_a_default():
    assert frame_interval() == DEFAULT_FRAME_INTERVAL
    set_frame_interval(0.0)
    assert frame_interval() == 0.001
    set_frame_interval(1 / 120)
    assert frame_interval() == pytest.approx(1 / 120)
