import pytest
import json

from cloudbot.util import web
from plugins.pastebins import sharey


def test_register() -> None:
    sharey.register()

    assert web.pastebins.get("sharey") is not None

    sharey.unregister()

    assert web.pastebins.get("sharey") is None


def test_paste(mock_requests) -> None:
    sharey.register()

    paster = web.pastebins["sharey"]

    mock_requests.add(
        "POST", "https://sharey.org/api/paste", json={"url": "https://sharey.org/foobar"}
    )
    assert paster.paste("test data", "txt") == "https://sharey.org/foobar?txt"
    sharey.unregister()


def test_data_params(mock_requests) -> None:
    sharey.register()

    body = None

    def req_cb(req):
        nonlocal body
        body = req.body
        return 200, {}, json.dumps({"url": "https://sharey.org/foobar"})

    paster = web.pastebins["sharey"]
    mock_requests.add_callback("POST", "https://sharey.org/api/paste", callback=req_cb)
    assert paster.paste("test data", "txt") == "https://sharey.org/foobar?txt"
    assert json.loads(body) == {"content": "test data"}
    sharey.unregister()


def test_paste_json_input(mock_requests) -> None:
    sharey.register()

    body = None

    def req_cb(req):
        nonlocal body
        body = req.body
        return 200, {}, json.dumps({"url": "https://sharey.org/foobar"})

    paster = web.pastebins["sharey"]
    mock_requests.add_callback("POST", "https://sharey.org/api/paste", callback=req_cb)
    assert paster.paste('{"foo": "bar"}', "txt") == "https://sharey.org/foobar?txt"
    assert json.loads(body) == {"foo": "bar"}
    sharey.unregister()


def test_paste_error(mock_requests) -> None:
    sharey.register()

    paster = web.pastebins["sharey"]

    with pytest.raises(web.ServiceError):
        paster.paste("test data", "txt")

    mock_requests.add(
        "POST",
        "https://sharey.org/api/paste",
        status=500,
    )

    with pytest.raises(web.ServiceHTTPError):
        paster.paste("test data", "txt")

    sharey.unregister()
