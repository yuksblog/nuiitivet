"""OS desktop integration, exposed as the ``Desktop`` namespace.

The ``Desktop`` class is a namespace, not something to instantiate — the same
convention as :class:`~nuiitivet.platform.file_dialog.FileDialog`. It scopes
APIs that talk to the operating system's desktop shell, keeping them visually
distinct from in-app concepts (an OS notification is not a ``Toast``, and
``Desktop.notify`` is not an ``Observable`` notification).
"""

from __future__ import annotations

from .notification import notify as _notify


class Desktop:
    """Operating-system desktop integration (notifications, ...)."""

    @staticmethod
    def notify(title: str, body: str = "") -> None:
        """Raise a desktop notification with ``title`` and an optional ``body``.

        Fire-and-forget: returns immediately, never raises, and is safe to
        call from an event handler or a worker thread alike. Failures are
        logged once per process instead of surfacing — a notification must
        never take the app down. Delivery is best-effort: the OS may still
        suppress it (permissions, focus modes) without an error.
        """
        _notify(title, body)
