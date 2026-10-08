"""``@server``: a function the app awaits, that runs away from the UI.

``RemoteFunction`` is the part a worker function shares: the declared types,
the run on a desktop thread, and the function's own side of a call.
"""

from __future__ import annotations

import asyncio
import builtins
import functools
import inspect
import json
import typing
from typing import Any, Callable, Coroutine, Generic, ParamSpec, TypeVar

from nuiitivet.common.target import is_web
from nuiitivet.observable.protocols import MutableObservableBase
from nuiitivet.observable.switched import CancelToken

from .codec import Codec, Json, _at, codec_for
from .scope import is_server_only
from .writer import CallWriter, WriteOnlyObservable

P = ParamSpec("P")
R = TypeVar("R")

# Where the page posts a call, relative to its own URL.
CALL_ROUTE = "nv/call/"


class RemoteError(Exception):
    """An exception of a server or worker function, carried by its class name and message.

    A built-in exception reaches the caller as itself. Any other class
    reaches it as this one: the class may exist only where the function ran.
    """

    def __init__(self, type_name: str, message: str) -> None:
        """Initialize RemoteError.

        Args:
            type_name: The name of the class raised in the function.
            message: That exception's text.
        """
        super().__init__(f"{type_name}: {message}")
        self.type_name = type_name
        self.message = message


class RemoteFunction(Generic[P, R]):
    """One function that runs away from the UI: its declared types and how a call runs."""

    # The decorator's name, for the errors a definition raises.
    mark = "remote"

    def __init__(self, fn: Callable[P, R], *, placed: bool = True) -> None:
        """Initialize RemoteFunction.

        Args:
            fn: The function as the app wrote it.
            placed: Whether *fn* must live in the kind of module its mark
                requires. The page's stand-in for a function does not.

        Raises:
            TypeError: If *fn* breaks a rule of its mark.
        """
        self.fn = fn
        self.name = f"{getattr(fn, '__module__', '?')}.{getattr(fn, '__qualname__', repr(fn))}"
        self._check_placement(placed)
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
        return TypeError(f"@{self.mark} {self.name}: {message}")

    def _check_placement(self, placed: bool) -> None:
        fn = self.fn
        if not inspect.isfunction(fn) or fn.__name__ == "<lambda>" or fn.__qualname__ != fn.__name__:
            # A method or a closure carries state that exists on one side only.
            raise self._error(f"only a function defined with def at module level can be a {self.mark} function")
        if inspect.iscoroutinefunction(fn) or inspect.isgeneratorfunction(fn) or inspect.isasyncgenfunction(fn):
            raise self._error(f"a {self.mark} function is a plain def; it already runs away from the UI")
        if placed:
            self._check_module()

    def _check_module(self) -> None:
        """Raise the definition error when the function's module is not where its mark lives.

        A mark with no placement rule accepts any module.
        """

    def _hints(self) -> dict[str, Any]:
        try:
            return typing.get_type_hints(self.fn)
        except NameError as error:
            raise self._error(f"{error}; an annotation must name a type defined above the function") from None

    def _codec(self, where: str, hint: Any) -> Codec:
        for cls in _classes_in(hint):
            if is_server_only(cls.__module__):
                # The page rebuilds values of this class, so it needs the class.
                raise self._error(
                    f"{where}: {cls.__name__} is defined in the server-only module {cls.__module__}; "
                    "a type in the signature must come from a module the page gets"
                )
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

    # -- the caller's side ---------------------------------------------------

    async def call(self, *args: P.args, **kwargs: P.kwargs) -> R:
        """Run the function away from the UI and return its result.

        Arguments, the result and every Observable write are copied the way
        a network connection carries them, so the function shares no object
        with its caller. Cancelling the awaiting task sets the function's
        ``CancelToken``.

        Args:
            *args: The function's own arguments, without its ``CancelToken``.
            **kwargs: The same, by name.

        Raises:
            TypeError: If an argument or the result is not of its declared type.
            RemoteError: If the function raised an exception that is not a
                built-in one. A built-in exception is raised as itself.
        """
        bound = self._caller_signature.bind(*args, **kwargs)
        bound.apply_defaults()
        writers: dict[str, CallWriter] = {}
        values: dict[str, Json] = {}
        for name, value in bound.arguments.items():
            if name in self._writers:
                if not isinstance(value, MutableObservableBase):
                    raise TypeError(f"{self.name}: {name} takes an Observable, got {type(value).__name__}")
                writers[name] = CallWriter(value, self._writers[name])
            else:
                values[name] = _at(f"{self.name}: {name}", self._values[name].encode, value)

        token = CancelToken()
        try:
            if is_web():
                encoded = await self._call_on_web(values, writers)
            else:
                receivers: dict[str, Callable[[Json], None]] = {n: w.receive for n, w in writers.items()}
                encoded = await asyncio.to_thread(self.run, values, receivers, token)
        except asyncio.CancelledError:
            token._supersede()
            for writer in writers.values():
                writer.close(deliver=False)
            raise
        except BaseException:
            for writer in writers.values():
                writer.close(deliver=True)
            raise
        for writer in writers.values():
            writer.close(deliver=True)
        return typing.cast(R, self._result.decode(encoded))

    async def _call_on_web(self, values: dict[str, Json], writers: dict[str, CallWriter]) -> Json:
        """Run the call where this mark runs in a browser, and return the encoded result."""
        raise NotImplementedError

    # -- the function's side -------------------------------------------------

    def run(self, values: dict[str, Json], writers: dict[str, Callable[[Json], None]], token: CancelToken) -> Json:
        """Run the function here, on the calling thread, from the wire form of its arguments.

        Args:
            values: Each data argument by name, encoded.
            writers: For each ``WriteOnlyObservable`` parameter, where the
                function's writes go, encoded.
            token: The function's ``CancelToken``.

        Returns:
            The result, encoded.

        Raises:
            TypeError: If an argument or the result is not of its declared type.
            RemoteError: If the function raised an exception that is not a
                built-in one. A built-in exception is raised as itself.
        """
        arguments: dict[str, Any] = {}
        for name, codec in self._values.items():
            arguments[name] = _at(f"{self.name}: {name}", codec.decode, values[name])
        for name, codec in self._writers.items():
            arguments[name] = _Writer(codec, writers[name])
        for name in self._tokens:
            arguments[name] = token
        call = inspect.BoundArguments(self._signature, arguments)  # type: ignore[arg-type]
        try:
            result = self.fn(*call.args, **call.kwargs)
        except Exception as error:
            if type(error).__module__ == "builtins":
                raise
            raise RemoteError(type(error).__qualname__, str(error)) from error
        return _at(f"{self.name}: return value", self._result.encode, result)


class ServerFunction(RemoteFunction[P, R]):
    """One ``@server`` function: on the web, its call is one request to the server."""

    mark = "server"

    async def _call_on_web(self, values: dict[str, Json], writers: dict[str, CallWriter]) -> Json:
        """One POST; progress arrives on the streamed response, the result ends it."""
        import js
        from pyodide.ffi import to_js

        controller = js.AbortController.new()
        options = to_js(
            {
                "method": "POST",
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(values),
                "signal": controller.signal,
            },
            dict_converter=js.Object.fromEntries,
        )
        try:
            response = await js.fetch(CALL_ROUTE + self.name, options)
            if response.status != 200:
                raise ConnectionError(f"{self.name}: the server answered {response.status} {response.statusText}")
            reader = response.body.getReader()
            buffer = b""
            while True:
                chunk = await reader.read()
                if chunk.done:
                    break
                buffer += chunk.value.to_bytes()
                lines = buffer.split(b"\n")
                buffer = lines.pop()
                for line in lines:
                    message = json.loads(line)
                    if "w" in message:
                        writers[message["w"]].receive(message["v"])
                    else:
                        return result_of(message)
        except asyncio.CancelledError:
            # The server sees the connection close and sets its token.
            controller.abort()
            raise
        raise ConnectionError(f"{self.name}: the response ended without a result")


class _Writer:
    """What a running function holds for a ``WriteOnlyObservable`` parameter."""

    __slots__ = ("_codec", "_send")

    def __init__(self, codec: Codec, send: Callable[[Json], None]) -> None:
        self._codec = codec
        self._send = send

    @property
    def value(self) -> object:
        raise AttributeError("a WriteOnlyObservable cannot be read; the caller's Observable is not on this side")

    @value.setter
    def value(self, v: Any) -> None:
        self._send(self._codec.encode(v))


def _classes_in(hint: Any) -> list[type]:
    if isinstance(hint, type):
        return [hint]
    return [cls for arg in typing.get_args(hint) for cls in _classes_in(arg)]


def encode_error(error: BaseException) -> Json:
    """The wire form of an exception a function raised."""
    if isinstance(error, RemoteError):
        return {"type": error.type_name, "message": error.message, "builtin": False}
    return {"type": type(error).__qualname__, "message": str(error), "builtin": True}


def result_of(message: Json) -> Json:
    """The encoded result in a call's last message, or the exception it carries, raised.

    Args:
        message: ``{"r": result}`` or ``{"e": error}``, as :func:`encode_error` wrote it.
    """
    if "r" in message:
        return message["r"]
    error = message["e"]
    cls = getattr(builtins, error["type"], None) if error["builtin"] else None
    if isinstance(cls, type) and issubclass(cls, Exception):
        raise cls(error["message"])
    raise RemoteError(error["type"], error["message"])


_functions: dict[str, RemoteFunction[Any, Any]] = {}


def lookup(name: str) -> RemoteFunction[Any, Any] | None:
    """The ``@server`` or ``@worker`` function registered under *name*, or ``None``.

    Args:
        name: The function's module and name, dotted.
    """
    return _functions.get(name)


def register(function: RemoteFunction[P, R]) -> Callable[P, Coroutine[Any, Any, R]]:
    """Register *function* under its name and return what the app calls: a coroutine function of its signature."""
    _functions[function.name] = function

    @functools.wraps(function.fn)
    async def call(*args: P.args, **kwargs: P.kwargs) -> R:
        return await function.call(*args, **kwargs)

    call.__signature__ = function._caller_signature  # type: ignore[attr-defined]
    return call


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
    ``T | None``. An ``Enum`` or dataclass in the signature is defined in a
    module the page gets, not in a server-only one.

    Two parameter types are not data. ``WriteOnlyObservable[T]`` receives an
    ``Observable`` of the caller for the function to report progress into.
    ``CancelToken``, declared with a default and never passed by the caller,
    is set when the awaiting task is cancelled.

    An exception reaches the caller: a built-in one as itself, any other as
    :class:`RemoteError`.

    The function's module reaches the browser like any other, and the
    function's body never runs there. A module that must stay on the server
    calls :func:`~nuiitivet.remote.scope.server_only`.

    Args:
        fn: A plain ``def`` at the top level of a module in the app's
            directory, with every parameter and the return type annotated.

    Raises:
        TypeError: If *fn* breaks one of these rules.
    """
    return register(ServerFunction(fn))


def stub(fn: Callable[P, R]) -> Callable[P, Coroutine[Any, Any, R]]:
    """The page's stand-in for a ``@server`` function: the signature, with the call sent to the server.

    The web build writes one for each server function, in place of the
    module that holds it.

    Args:
        fn: A function with the server function's signature and no body.
    """
    return register(ServerFunction(fn, placed=False))


__all__ = [
    "CALL_ROUTE",
    "RemoteError",
    "RemoteFunction",
    "ServerFunction",
    "encode_error",
    "lookup",
    "register",
    "result_of",
    "server",
    "stub",
]
