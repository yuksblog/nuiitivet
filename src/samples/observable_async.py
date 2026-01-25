"""Async Data Fetching Sample - Observable Phase 1

Demonstrates:
- .dispatch_to_ui() for thread-safe updates
- Async data fetching from worker threads
- Loading states with observables
- Error handling
"""

import threading
import time
from typing import Optional

from nuiitivet.observable import Observable
from nuiitivet.material.app import MaterialApp
from nuiitivet.material import Text
from nuiitivet.material.styles.text_style import TextStyle
from nuiitivet.widgeting.widget import ComposableWidget, Widget
from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.material.buttons import FilledButton, OutlinedButton
from nuiitivet.widgets.box import Box


class User:
    """Simple user data model"""

    def __init__(self, id: int, name: str, email: str):
        self.id = id
        self.name = name
        self.email = email


class AsyncDataViewModel:
    """ViewModel with async data fetching"""

    # Define observables as class attributes (descriptors)
    user: Observable[Optional[User]] = Observable(None)
    loading = Observable(False)
    error: Observable[Optional[str]] = Observable(None)

    def __init__(self):
        # UI thread-safe observables (using .dispatch_to_ui())
        self.user.dispatch_to_ui()
        self.loading.dispatch_to_ui()
        self.error.dispatch_to_ui()

        # Computed status message
        self.status_message = self.loading.map(lambda loading: "Loading..." if loading else "")

        # Computed display text
        self.user_display = self.user.map(lambda u: f"👤 {u.name}\n📧 {u.email}" if u else "No user selected")

        # Computed error display
        self.error_display = self.error.map(lambda e: f"Error: {e}" if e else "")

    def fetch_user(self, user_id: int):
        """Fetch user data in background thread"""

        def worker():
            # Simulate API call
            self.loading.value = True
            self.error.value = None

            try:
                time.sleep(1.5)  # Simulate network delay

                # Simulate occasional errors
                if user_id == 999:
                    raise Exception("User not found")

                # Create fake user data
                user = User(
                    id=user_id,
                    name=f"User {user_id}",
                    email=f"user{user_id}@example.com",
                )

                # ✅ Safe: .dispatch_to_ui() ensures UI thread update
                self.user.value = user

            except Exception as e:
                self.error.value = str(e)
                self.user.value = None

            finally:
                self.loading.value = False

        # Start background thread
        thread = threading.Thread(target=worker)
        thread.daemon = True
        thread.start()


class AsyncDataApp(ComposableWidget):
    def __init__(self):
        super().__init__()
        self.viewmodel = AsyncDataViewModel()

    def build(self) -> Widget:
        vm = self.viewmodel

        return Box(
            padding=20,
            child=Column(
                gap=20,
                children=[
                    # Title
                    Text(
                        "Async Data Fetching",
                    ),
                    # Description
                    Text(
                        "Thread-safe Observable updates\n" "(using .dispatch_to_ui())",
                        style=TextStyle(color=(100, 100, 100, 255)),
                    ),
                    # User selection buttons
                    Column(
                        gap=10,
                        children=[
                            Text("Select User:"),
                            Row(
                                gap=10,
                                children=[
                                    FilledButton("User 1", on_click=lambda: vm.fetch_user(1)),
                                    FilledButton("User 2", on_click=lambda: vm.fetch_user(2)),
                                    FilledButton("User 3", on_click=lambda: vm.fetch_user(3)),
                                ],
                            ),
                            Row(
                                gap=10,
                                children=[
                                    FilledButton("User 4", on_click=lambda: vm.fetch_user(4)),
                                    FilledButton("User 5", on_click=lambda: vm.fetch_user(5)),
                                    OutlinedButton("Error (999)", on_click=lambda: vm.fetch_user(999)),
                                ],
                            ),
                        ],
                    ),
                    # Loading indicator
                    Text(
                        vm.status_message,
                        style=TextStyle(color=(50, 150, 255, 255)),
                    ),
                    # Error display (conditional on error presence)
                    Box(
                        padding=10,
                        background_color=(255, 230, 230, 255),
                        child=Text(
                            vm.error_display,
                            style=TextStyle(color=(200, 0, 0, 255)),
                        ),
                    ),
                    # User data display
                    Box(
                        padding=15,
                        background_color=(240, 248, 255, 255),
                        child=Text(
                            vm.user_display,
                        ),
                    ),
                    # Info
                    Text(
                        "Click buttons to fetch data in background\n" "(1.5 second delay)",
                        style=TextStyle(color=(100, 100, 100, 255)),
                    ),
                ],
            ),
        )


if __name__ == "__main__":
    widget = AsyncDataApp()
    app = MaterialApp(content=widget)
    try:
        app.run()
    except Exception:
        print("Async data demo requires pyglet/skia to run.")
