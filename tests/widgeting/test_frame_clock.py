"""The frame clock: the loop says when a frame begins and ends, and how long a frame is."""

from time import perf_counter

import pytest

from nuiitivet.widgeting import frame_clock
from nuiitivet.widgeting.frame_clock import (
    DEFAULT_FRAME_INTERVAL,
    begin_frame,
    end_frame,
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


def test_a_frame_under_way_reports_when_it_began():
    started = perf_counter()
    begin_frame(started)

    assert frame_started_at() == started


def test_between_frames_no_frame_is_under_way():
    assert frame_started_at() is None

    begin_frame(perf_counter())
    end_frame()
    assert frame_started_at() is None


def test_the_interval_has_a_floor_and_a_default():
    assert frame_interval() == DEFAULT_FRAME_INTERVAL
    set_frame_interval(0.0)
    assert frame_interval() == 0.001
    set_frame_interval(1 / 120)
    assert frame_interval() == pytest.approx(1 / 120)
