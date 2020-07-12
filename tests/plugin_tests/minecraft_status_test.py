from unittest.mock import MagicMock

import pytest
import requests

from cloudbot.event import CommandEvent
from plugins import minecraft_status
from tests.util import wrap_hook_response


def test_mcstatus(mock_requests):
    event = CommandEvent(
        channel="#foo",
        hook=MagicMock(),
        conn=MagicMock(),
        bot=MagicMock(),
        triggered_command="mcstatus",
        cmd_prefix=".",
        text="",
    )
    res = []
    mock_requests.add("GET", "http://status.mojang.com/check", status=404)
    with pytest.raises(requests.HTTPError):
        wrap_hook_response(minecraft_status.mcstatus, event, res)

    error_res = (
        "(None) Unable to get Minecraft server status: 404 Client Error: "
        "Not Found for url: http://status.mojang.com/check"
    )
    assert res == [("message", ("#foo", error_res,),)]

    mock_requests.replace(
        "GET",
        "http://status.mojang.com/check",
        json=[
            {"minecraft.net": "red"},
            {"session.minecraft.net": "yellow"},
            {"account.mojang.com": "green"},
            {"authserver.mojang.com": "green"},
            {"sessionserver.mojang.com": "red"},
            {"api.mojang.com": "green"},
            {"textures.minecraft.net": "green"},
            {"mojang.com": "red"},
        ],
    )
    res = wrap_hook_response(minecraft_status.mcstatus, event)
    expected = (
        "\x0f\x02Online\x02: account.mj, api.mj, authserver.mj, "
        "textures.mc \x02Issues\x02: session.mc \x02Offline\x02: "
        "minecraft.net, mojang.com, sessionserver.mj"
    )
    assert res == [("return", expected,)]
