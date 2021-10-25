import re
from datetime import datetime, timedelta
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest
from responses import Response

from cloudbot.bot import bot
from cloudbot.event import CommandEvent
from plugins import cryptocurrency
from tests.util import HookResult, wrap_hook_response


def test_parse():
    assert cryptocurrency.ResponseStatus._fields != cryptocurrency.Quote._fields
    cryptocurrency.Platform(  # nosec
        id=1,
        name="name",
        symbol="symbol",
        slug="slug",
        token_address="foobar",
    )
    assert len(cryptocurrency.Platform._fields) == 5
    data = {
        "status": {
            "timestamp": "ts",
            "error_code": 200,
            "error_message": None,
            "elapsed": 1,
            "credit_count": 1,
            "notice": None,
        }
    }

    obj = cryptocurrency.read_data(data, cryptocurrency.APIRequestResponse)
    assert obj.status.credit_count == 1
    assert cryptocurrency.serialize(obj) == data


class MatchAPIKey(Response):
    def __init__(self, method, url, api_key=None, **kwargs):
        super().__init__(method, url, **kwargs)
        self.api_key = api_key

    def matches(self, request):
        if self.api_key:
            assert request.headers["X-CMC_PRO_API_KEY"] == self.api_key

        return super().matches(request)


def init_response(
    mock_requests,
    fiat_map=True,
    quote=True,
    error_msg=None,
    check_api_key=False,
    pct_change=18.9,
    show_btc=True,
    price=50000000000.0,
):
    if check_api_key:
        cryptocurrency.init_api(bot.get())

    cryptocurrency.api.cache.clear()
    cryptocurrency.api.show_btc = show_btc
    now = datetime.now()

    iso_fmt = "%Y-%m-%dT%H:%M:%S.%f%z"

    mock_requests.add(
        MatchAPIKey(
            "GET",
            "https://pro-api.coinmarketcap.com/v1/cryptocurrency/map",
            api_key="APIKEY" if check_api_key else None,
            json={
                "status": {
                    "timestamp": now.strftime(iso_fmt),
                    "error_code": 200,
                    "elapsed": 1,
                    "credit_count": 1,
                },
                "data": [
                    {
                        "id": 1,
                        "name": "bitcoin",
                        "symbol": "BTC",
                        "slug": "bitcoin",
                        "is_active": 1,
                    },
                ],
            },
        )
    )

    if fiat_map:
        mock_requests.add(
            MatchAPIKey(
                "GET",
                "https://pro-api.coinmarketcap.com/v1/fiat/map",
                api_key="APIKEY" if check_api_key else None,
                json={
                    "status": {
                        "timestamp": now.strftime(iso_fmt),
                        "error_code": 200,
                        "elapsed": 1,
                        "credit_count": 1,
                    },
                    "data": [
                        {
                            "id": 1,
                            "name": "Dollar",
                            "sign": "$",
                            "symbol": "USD",
                        }
                    ],
                },
            )
        )

    if quote:
        response_data: Dict[str, Any] = {
            "1": {
                "id": 1,
                "name": "Bitcoin",
                "slug": "bitcoin",
                "symbol": "BTC",
                "circulating_supply": 100,
                "total_supply": 1000,
                "date_added": (now - timedelta(days=5)).strftime(iso_fmt),
                "num_market_pairs": 1,
                "cmc_rank": 1,
                "last_updated": (now - timedelta(hours=1)).strftime(iso_fmt),
                "tags": [],
                "quote": {
                    "USD": {
                        "price": price,
                        "volume_24h": 20,
                        "market_cap": 92,
                        "percent_change_1h": 14.5,
                        "percent_change_24h": pct_change,
                        "percent_change_7d": 24.5,
                        "last_updated": (now - timedelta(minutes=3)).strftime(
                            iso_fmt
                        ),
                    },
                },
            },
        }
        if show_btc:
            response_data["1"]["quote"]["BTC"] = {
                "price": 2,
                "volume_24h": 5,
                "market_cap": 97,
                "percent_change_1h": 12.5,
                "percent_change_24h": 17.4,
                "percent_change_7d": 54.1,
                "last_updated": (now - timedelta(minutes=6)).strftime(iso_fmt),
            }

        data = {
            "status": {
                "timestamp": now.strftime(iso_fmt),
                "error_code": 400 if error_msg else 200,
                "error_message": error_msg,
                "elapsed": 1,
                "credit_count": 1,
            },
        }
        if not error_msg:
            data["data"] = response_data

        mock_requests.add(
            MatchAPIKey(
                "GET",
                "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest?symbol=BTC&convert=USD"
                + ("%2CBTC" if show_btc else ""),
                api_key="APIKEY" if check_api_key else None,
                json=data,
            )
        )


def test_api(mock_requests, mock_api_keys):
    bot.config["plugins"] = {}
    init_response(mock_requests, check_api_key=True)

    result = cryptocurrency.api.get_quote("BTC", "USD")

    assert result.name == "Bitcoin"
    assert not result.unknown_fields
    assert result.total_supply == 1000
    assert result.circulating_supply == 100


class SomeSchema(cryptocurrency.Schema):
    def __init__(self, a: List[List[Dict[str, List[str]]]]):
        super().__init__()
        self.a = a


def test_schema():
    cryptocurrency.read_data({"a": [[{"a": ["1"]}]]}, SomeSchema)


class ConcreteSchema(cryptocurrency.Schema):
    def __init__(self, a: str) -> None:
        super().__init__()
        self.a = a


class AbstractSchema(ConcreteSchema):
    _abstract = True


class OtherConcreteSchema(AbstractSchema):
    def __init__(self, a: str, b: str):
        super().__init__(a)
        self.b = b


def test_complex_schema():
    cryptocurrency.read_data({"a": "hello", "b": "world"}, OtherConcreteSchema)


def test_invalid_schema_type():
    with pytest.raises(
        TypeError,
        match="field 'a' expected type <class 'str'>, got type <class 'int'>",
    ):
        cryptocurrency.read_data({"a": 1, "b": "world"}, OtherConcreteSchema)


def test_schema_missing_field():
    with pytest.raises(cryptocurrency.ParseError) as exc:
        cryptocurrency.read_data({"b": "hello"}, OtherConcreteSchema)

    assert isinstance(exc.value.__cause__, cryptocurrency.MissingSchemaField)


class NestedSchema(cryptocurrency.Schema):
    def __init__(self, a: OtherConcreteSchema) -> None:
        super().__init__()
        self.a = a


def test_schema_nested_exceptions():
    with pytest.raises(cryptocurrency.ParseError) as exc:
        cryptocurrency.read_data({"a": {"b": "hello"}}, NestedSchema)

    assert isinstance(exc.value.__cause__, cryptocurrency.ParseError)
    assert isinstance(
        exc.value.__cause__.__cause__, cryptocurrency.MissingSchemaField
    )


def test_schema_unknown_fields():
    input_data = {"a": {"a": "hello", "b": "world"}, "c": 1}
    with pytest.warns(
        UserWarning,
        match=re.escape(
            "Unknown fields: ['c'] while parsing schema 'NestedSchema'"
        ),
    ):
        obj = cryptocurrency.read_data(input_data, NestedSchema)

    assert cryptocurrency.serialize(obj) == input_data


def test_cache(freeze_time):
    c = cryptocurrency.Cache()
    c.put("foo", "bar", 30)

    # Object with a lifespan of 30 seconds should die at 30 seconds
    freeze_time.tick(timedelta(seconds=29))
    assert c.get("foo") is not None
    assert c.get("foo").value == "bar"
    freeze_time.tick()
    assert c.get("foo") is None


@pytest.mark.parametrize(
    "price,out",
    [
        (1, "1.00"),
        (50000, "50,000.00"),
        (10.2548, "10.25"),
        (0.1, "0.10"),
        (0.0241, "0.0241"),
        (0.00241, "0.00241"),
        (0.000241, "0.000241"),
        (0.0000241, "0.0000241"),
        (0.001231549654135151564, "0.0012315497"),
    ],
)
def test_format_price(price, out):
    assert cryptocurrency.format_price(price) == out


def test_crypto_cmd(mock_requests):
    init_response(mock_requests)

    conn = MagicMock()
    conn.config = {}
    conn.bot = None

    event = CommandEvent(
        text="BTC USD",
        cmd_prefix=".",
        triggered_command="crypto",
        hook=MagicMock(),
        bot=conn.bot,
        conn=conn,
        channel="#foo",
        nick="foobaruser",
    )
    res = wrap_hook_response(cryptocurrency.crypto_command, event)

    assert res == [
        HookResult(
            return_type="return",
            value="BTC (bitcoin) // \x0307$50,000,000,000.00\x0f USD - 2.0000000 BTC // \x0303+18.9%\x0f change",
        )
    ]


def _run_alias():
    conn = MagicMock()
    conn.config = {}
    conn.bot = None

    event = CommandEvent(
        text="",
        cmd_prefix=".",
        triggered_command="btc",
        hook=MagicMock(),
        bot=conn.bot,
        conn=conn,
        channel="#foo",
        nick="foobaruser",
    )
    return wrap_hook_response(cryptocurrency.btc_alias, event)


def test_btc_alias(mock_requests):
    init_response(mock_requests)

    res = _run_alias()

    assert res == [
        HookResult(
            return_type="return",
            value="BTC (bitcoin) // \x0307$50,000,000,000.00\x0f USD - 2.0000000 BTC // \x0303+18.9%\x0f change",
        )
    ]


def test_btc_alias_neg_change(mock_requests):
    init_response(mock_requests, pct_change=-14.5)

    res = _run_alias()

    assert res == [
        HookResult(
            return_type="return",
            value="BTC (bitcoin) // \x0307$50,000,000,000.00\x0f USD - 2.0000000 BTC // \x0305-14.5%\x0f change",
        )
    ]


def test_btc_alias_no_change(mock_requests):
    init_response(mock_requests, pct_change=0)

    res = _run_alias()

    assert res == [
        (
            "return",
            "BTC (bitcoin) // \x0307$50,000,000,000.00\x0f USD - 2.0000000 BTC // 0% change",
        )
    ]


def test_no_show_btc(mock_requests):
    show_btc = cryptocurrency.get_plugin_config({}, "show_btc", False)
    init_response(mock_requests, show_btc=show_btc)

    res = _run_alias()

    assert res == [
        (
            "return",
            "BTC (bitcoin) // \x0307$50,000,000,000.00\x0f USD // \x0303+18.9%\x0f change",
        )
    ]


def test_crypto_cmd_bad_symbol(mock_requests):
    init_response(mock_requests, fiat_map=False, quote=False)

    conn = MagicMock()
    conn.config = {}
    conn.bot = None

    event = CommandEvent(
        text="ABC USD",
        cmd_prefix=".",
        triggered_command="crypto",
        hook=MagicMock(),
        bot=conn.bot,
        conn=conn,
        channel="#foo",
        nick="foobaruser",
    )
    res = wrap_hook_response(cryptocurrency.crypto_command, event)

    assert res == [HookResult("return", "Unknown cryptocurrency 'ABC'")]


def test_crypto_cmd_bad_fiat(mock_requests):
    init_response(mock_requests, quote=False)

    conn = MagicMock()
    conn.config = {}
    conn.bot = None

    event = CommandEvent(
        text="BTC ABC",
        cmd_prefix=".",
        triggered_command="crypto",
        hook=MagicMock(),
        bot=conn.bot,
        conn=conn,
        channel="#foo",
        nick="foobaruser",
    )
    res = wrap_hook_response(cryptocurrency.crypto_command, event)

    assert res == [HookResult("return", "Unknown fiat currency 'ABC'")]


def test_cmd_api_error(mock_requests):
    init_response(mock_requests, error_msg="FooBar")
    conn = MagicMock()
    conn.config = {}
    conn.bot = None

    event = CommandEvent(
        text="BTC USD",
        cmd_prefix=".",
        triggered_command="crypto",
        hook=MagicMock(),
        bot=conn.bot,
        conn=conn,
        channel="#foo",
        nick="foobaruser",
    )
    res: List[HookResult] = []
    with pytest.raises(cryptocurrency.APIError, match="FooBar"):
        wrap_hook_response(cryptocurrency.crypto_command, event, res)

    assert res == [
        HookResult("message", ("#foo", "(foobaruser) Unknown API error"))
    ]


def test_list_currencies(patch_paste, mock_requests):
    init_response(mock_requests, fiat_map=False, quote=False)
    cryptocurrency.currency_list()
    patch_paste.assert_called_with("Symbol     Name\nBTC        bitcoin")
