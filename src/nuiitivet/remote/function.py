"""``@server``: a function the app awaits, that runs away from the UI."""

from __future__ import annotations

import asyncio
import functools
import inspect
import typing
from typing import Any, Callable, Coroutine, Generic, ParamSpec, TypeVar

from nuiitivet.observable.protocols import MutableObservableBase
from nuiitivet.observable.switched import CancelToken

from .codec import Codec, _at, codec_for
from .scope import is_server_only
from .writer import CallWriter, WriteOnlyObservable

P = ParamSpec("P")
R = TypeVar("R")


class ServerError(Exception):
    """An exception of a server function whose class the caller cannot be given.

    A built-in exception reaches the caller as itself. Any other class may
    exist only on the server, so the caller gets this one.
    """

    def __init__(self, type_name: str, message: str) -> None:
        """Initialize ServerError.

        Args:
            type_name: The name of the class raised in the function.
            message: That exception's text.
        """
        super().__init__(f"{type_name}: {message}")
        self.type_name = type_name
        self.message = message


class ServerFunction(Generic[P, R]):
    """One ``@server`` function: its declared types and how a call runs."""

    def __init__(self, fn: Callable[P, R]) -> None:
        """Initialize ServerFunction.

        Args:
            fn: The function as the app wrote it.

        Raises:
            TypeError: If *fn* breaks a rule of :func:`server`.
        """
        self.fn = fn
        self.name = f"{getattr(fn, '__module__', '?')}.{getattr(fn, '__qualname__', repr(fn))}"
        self._check_placement()
        self._signature = inspect.signature(fn)
        self._values: dict[str, Codec] = {}
        self._writers: dict[str, Codec] = {}
        self._tokens: list[str] = []
        hints = self._hints()
        for parameter in self._signature.parameters.values():
            self._declare(parameter, hints)
        if "return" not in hints:
            raise self._error("the return type needs an annotation")
        self._result = self._codec("the return type", hints["return"])
        self._caller_signature = self._signature.replace(
            parameters=[p for p in self._signature.parameters.values() if p.name not in self._tokens],
            return_annotation=inspect.Signature.empty,
        )

    # -- definition ---------------------------------------------------------

    def _error(self, message: str) -> TypeError:
        return TypeError(f"@server {self.name}: {message}")

    def _check_placement(self) -> None:
        fn = self.fn
        if not inspect.isfunction(fn) or fn.__name__ == "<lambda>" or fn.__qualname__ != fn.__name__:
            # A method or a closure carries state that exists on one side only.
            raise self._error("only a function defined with def at module level can be a server function")
        if inspect.iscoroutinefunction(fn) or inspect.isgeneratorfunction(fn) or inspect.isasyncgenfunction(fn):
            raise self._error("a server function is a plain def; it already runs away from the UI")
        if not is_server_only(fn.__module__):
            raise self._error(
                f"module {fn.__module__} is not server-only; call nv.server_only() "
                "at its top, or in the __init__.py of its package"
            )

    def _hints(self) -> dict[str, Any]:
        try:
            return typing.get_type_hints(self.fn)
        except NameError as error:
            raise self._error(f"{error}; an annotation must name a type defined above the function") from None

    def _codec(self, where: str, hint: Any) -> Codec:
        try:
            return codec_for(hint)
        except TypeError as error:
            raise self._error(f"{where}: {error}") from None

    def _declare(self, parameter: inspect.Parameter, hints: dict[str, Any]) -> None:
        name = parameter.name
        if parameter.kind in (parameter.VAR_POSITIONAL, parameter.VAR_KEYWORD):
            raise self._error(f"*{name} is not allowed; each argument is declared with its type")
        if name not in hints:
            raise self._error(f"parameter {name} needs an annotation")
        hint = hints[name]
        if hint is CancelToken:
            if parameter.default is parameter.empty:
                # The caller never passes the token, and a type checker only
                # accepts that for a parameter with a default.
                raise self._error(f"parameter {name} needs a default: {name}: CancelToken = CancelToken()")
            self._tokens.append(name)
        elif hint is WriteOnlyObservable:
            raise self._error(f"parameter {name} needs its value type: WriteOnlyObservable[T]")
        elif typing.get_origin(hint) is WriteOnlyObservable:
            self._writers[name] = self._codec(f"parameter {name}", typing.get_args(hint)[0])
        else:
            self._values[name] = self._codec(f"parameter {name}", hint)

    # -- one call -----------------------------------------------------------

    async def call(self, *args: P.args, **kwargs: P.kwargs) -> R:
        """Run the function on a worker thread and return its result.

        Arguments, the result and every Observable write are copied the way
        a network connection would carry them, so the function shares no
        object with its caller. Cancelling the awaiting task sets the
        function's ``CancelToken``.

        Args:
            *args: The function's own arguments, without its ``CancelToken``.
            **kwargs: The same, by name.

        Raises:
            TypeError: If an argument or the result is not of its declared type.
            ServerError: If the function raised an exception that is not a
                built-in one. A built-in exception is raised as itself.
        """
        bound = self._caller_signature.bind(*args, **kwargs)
        bound.apply_defaults()
        token = CancelToken()
        writers: list[CallWriter] = []
        arguments: dict[str, Any] = {}
        for name, value in bound.arguments.items():
            if name in self._writers:
                if not isinstance(value, MutableObservableBase):
                    raise TypeError(f"{self.name}: {name} takes an Observable, got {type(value).__name__}")
                writers.append(CallWriter(value, self._writers[name]))
                arguments[name] = writers[-1]
            else:
                arguments[name] = _at(f"{self.name}: {name}", self._values[name].copy, value)
        for name in self._tokens:
            arguments[name] = token

        try:
            result = await asyncio.to_thread(self._run, arguments)
        except asyncio.CancelledError:
            token._supersede()
            for writer in writers:
                writer.close(deliver=False)
            raise
        except BaseException:
            for writer in writers:
                writer.close(deliver=True)
            raise
        for writer in writers:
            writer.close(deliver=True)
        return result

    def _run(self, arguments: dict[str, Any]) -> R:
        """The call's body, on its worker thread."""
        call = inspect.BoundArguments(self._signature, arguments)  # type: ignore[arg-type]
        try:
            result = self.fn(*call.args, **call.kwargs)
        except Exception as error:
            if type(error).__module__ == "builtins":
                raise
            raise ServerError(type(error).__qualname__, str(error)) from error
        copied: R = _at(f"{self.name}: return value", self._result.copy, result)
        return copied


def server(fn: Callable[P, R]) -> Callable[P, Coroutine[Any, Any, R]]:
    """Mark a function as one that runs on the server when the app is on the web.

    The app awaits it the same way on both targets::

        @nv.server
        def load_orders(user_id: int) -> list[Order]: ...

        orders = await load_orders(42)

    On the desktop it runs on a worker thread. Either way it shares nothing
    with its caller: arguments and the result are copied, and may only be of
    the types that survive a connection -- ``None``, ``bool``, ``int``,
    ``float``, ``str``, ``bytes``, ``datetime``, ``date``, an ``Enum``, a
    dataclass of these, ``list[T]``, ``tuple[T, ...]``, ``dict[str, T]`` and
    ``T | None``.

    Two parameter types are not data. ``WriteOnlyObservable[T]`` receives an
    ``Observable`` of the caller for the function to report progress into.
    ``CancelToken``, declared with a default and never passed by the caller,
    is set when the awaiting task is cancelled.

    An exception reaches the caller: a built-in one as itself, any other as
    :class:`ServerError`.

    Args:
        fn: A plain ``def`` at the top level of a module that is covered by
            :func:`~nuiitivet.remote.scope.server_only`, with every parameter
            and the return type annotated.

    Raises:
        TypeError: If *fn* breaks one of these rules.
    """
    function = ServerFunction(fn)

    @functools.wraps(fn)
    async def call(*args: P.args, **kwargs: P.kwargs) -> R:
        return await function.call(*args, **kwargs)

    call.__signature__ = function._caller_signature  # type: ignore[attr-defined]
    return call


__all__ = ["ServerError", "ServerFunction", "server"]
