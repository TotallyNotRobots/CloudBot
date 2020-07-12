from cloudbot import bot
from plugins import google_cse
from tests.util.mock_bot import MockConfig


def test_cse_no_api_key(mock_requests, mock_api_keys):
    mock_api_keys.return_value = None
    expected = "This command requires a Google Developers Console API key."
    assert google_cse.gse("foo") == expected


def test_cse_no_cse_id(mock_requests, mock_api_keys):
    _bot = bot.bot.get()
    _bot.config = MockConfig(_bot)
    _bot.config.add_api_key("google_dev_key", "foobar")

    expected = "This command requires a custom Google Search Engine ID."
    assert google_cse.gse("foo") == expected


def test_cse_no_results(mock_requests, mock_api_keys):
    mock_requests.add(
        "GET",
        "https://www.googleapis.com/customsearch/v1?cx=APIKEY&q=foo&key=APIKEY",
        json={},
    )
    assert google_cse.gse("foo") == "No results found."


def test_cse(mock_requests, mock_api_keys):
    mock_requests.add(
        "GET",
        "https://www.googleapis.com/customsearch/v1?cx=APIKEY&q=foo&key=APIKEY",
        json={"items": [{"title": "foobar", "snippet": "baz", "link": "bing"}]},
    )
    assert google_cse.gse("foo") == 'bing -- \x02foobar\x02: "baz"'
