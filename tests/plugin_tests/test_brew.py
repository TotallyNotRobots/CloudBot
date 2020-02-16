from unittest.mock import MagicMock

from tests.util.mock_bot import MockBot


def test_no_results(mock_requests, unset_bot):
    from cloudbot.bot import bot

    bot.set(MockBot({"api_keys": {"brewerydb": "APIKEY"}}))
    mock_requests.add(
        'GET',
        'http://api.brewerydb.com/v2/search'
        '?format=json&key=APIKEY&type=beer&withBreweries=Y&q=some+text',
        match_querystring=True,
        json={"totalResults": 0},
    )
    from plugins import brew

    reply = MagicMock()
    result = brew.brew('some text', reply)

    reply.assert_not_called()

    assert result == 'No results found.'
