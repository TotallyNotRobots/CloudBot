from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, TypeVar

from typing_extensions import ParamSpec

if TYPE_CHECKING:
    from collections.abc import Callable


class EventMessage(Protocol):
    def __call__(self, message: str, target: str | None = None) -> None: ...


class EventAdminLog(Protocol):
    def __call__(self, message: str, broadcast: bool = False) -> None: ...


class EventReply(Protocol):
    def __call__(self, *messages: str, target: str | None = None) -> None: ...


class EventAction(Protocol):
    def __call__(self, message: str, target: str | None = None) -> None: ...


class EventCtcp(Protocol):
    def __call__(
        self, message: str, ctcp_type: str, target: str | None = None
    ) -> None: ...


class EventNotice(Protocol):
    def __call__(self, message: str, target: str | None = None) -> None: ...


class EventIsNickValid(Protocol):
    def __call__(self, nick: str) -> bool: ...


class EventNoticeDoc(Protocol):
    def __call__(self, target: str | None = None) -> None: ...


class EventHasPermission(Protocol):
    def __call__(self, permission: str, notice: bool = True) -> bool: ...


P = ParamSpec("P")
T = TypeVar("T")


class EventAsyncCall(Protocol):
    async def __call__(
        self, func: Callable[P, T], *args: P.args, **kwargs: P.kwargs
    ) -> T: ...


class EventCheckPermission(Protocol):
    async def __call__(self, permission: str, notice: bool = True) -> bool: ...


class EventCheckPermissions(Protocol):
    async def __call__(self, *perms: str, notice: bool = True) -> bool: ...
