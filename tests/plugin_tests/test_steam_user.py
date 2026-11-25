from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from responses.matchers import query_param_matcher

from plugins import steam_user
from tests.util import get_data_path

if TYPE_CHECKING:
    from responses import RequestsMock


def _get_data(mock_requests: RequestsMock, user: str) -> dict[str, str | int]:
    datapath = get_data_path() / "steam_user" / f"{user}.xml"
    mock_requests.add(
        "GET",
        f"http://steamcommunity.com/id/{user}/",
        match=[query_param_matcher({"xml": 1})],
        body=datapath.read_bytes(),
    )
    return steam_user.get_data(user)


def test_get_user(mock_requests: RequestsMock) -> None:
    assert _get_data(mock_requests, "testuser") == {
        "name": "test user",
        "id_64": 76561198120430884,
        "state": "Offline",
        "id_32": "STEAM_0:0:80082578",
        "id_3": "U:1:160165156",
    }


def test_user_not_found(mock_requests: RequestsMock) -> None:
    with pytest.raises(
        steam_user.SteamError, match=r"^Could not get data for this user\.$"
    ):
        _get_data(mock_requests, "userthatdoesnotexist")
