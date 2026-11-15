from typing import TYPE_CHECKING, cast
from unittest.mock import MagicMock

if TYPE_CHECKING:
    from cloudbot.event import CommandEvent, Event
    from cloudbot.event_functions import (
        EventAction,
        EventAdminLog,
        EventAsyncCall,
        EventCheckPermission,
        EventCheckPermissions,
        EventCtcp,
        EventHasPermission,
        EventIsNickValid,
        EventMessage,
        EventNotice,
        EventNoticeDoc,
        EventReply,
    )


def test_event_action_type() -> None:
    _: EventAction = cast("Event", MagicMock()).action


def test_event_admin_log_type() -> None:
    _: EventAdminLog = cast("Event", MagicMock()).admin_log


def test_event_async_call_type() -> None:
    _: EventAsyncCall = cast("Event", MagicMock()).async_call


def test_event_check_permission_type() -> None:
    _: EventCheckPermission = cast("Event", MagicMock()).check_permission


def test_event_check_permissions_type() -> None:
    _: EventCheckPermissions = cast("Event", MagicMock()).check_permissions


def test_event_ctcp_type() -> None:
    _: EventCtcp = cast("Event", MagicMock()).ctcp


def test_event_has_permission_type() -> None:
    _: EventHasPermission = cast("Event", MagicMock()).has_permission


def test_event_is_nick_valid_type() -> None:
    _: EventIsNickValid = cast("Event", MagicMock()).is_nick_valid


def test_event_message_type() -> None:
    _: EventMessage = cast("Event", MagicMock()).message


def test_event_notice_type() -> None:
    _: EventNotice = cast("Event", MagicMock()).notice


def test_event_notice_doc_type() -> None:
    _: EventNoticeDoc = cast("CommandEvent", MagicMock()).notice_doc


def test_event_reply_type() -> None:
    _: EventReply = cast("Event", MagicMock()).reply
