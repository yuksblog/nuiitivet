import asyncio
import pytest
from nuiitivet.material import TextButton


@pytest.mark.asyncio
async def test_async_button_click_handler():
    """Test that an async on_click handler is scheduled as a task."""

    clicked = asyncio.Event()

    async def on_click():
        await asyncio.sleep(0.01)
        clicked.set()

    button = TextButton("Click Me", on_click=on_click)

    # Simulate click via PointerInputNode to ensure async handling logic is triggered
    button._pointer_node._emit_click()

    # Wait for the task to complete
    try:
        await asyncio.wait_for(clicked.wait(), timeout=1.0)
    except asyncio.TimeoutError:
        pytest.fail("Async click handler was not executed or timed out")

    assert clicked.is_set()


@pytest.mark.asyncio
async def test_sync_button_click_handler():
    """Test that a sync on_click handler is executed immediately."""

    clicked = False

    def on_click():
        nonlocal clicked
        clicked = True

    button = TextButton("Click Me", on_click=on_click)

    button._pointer_node._emit_click()

    assert clicked
