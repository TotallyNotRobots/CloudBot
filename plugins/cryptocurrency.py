"""
cryptocurrency.py

A plugin that uses the CoinMarketCap JSON API to get values for cryptocurrencies.

Created By:
    - Luke Rogers <https://github.com/lukeroge>

License:
    GPL v3
"""

import time
from decimal import Decimal
from operator import itemgetter
from threading import RLock
from typing import (
    Any,
    Callable,
    ContextManager,
    Dict,
    Generic,
    List,
    Optional,
    Set,
    Type,
    TypeVar,
    Union,
    cast,
)

import requests
from pydantic import BaseModel, Field, computed_field
from requests import Response
from typing_extensions import Self
from yarl import URL

from cloudbot import hook
from cloudbot.bot import AbstractBot
from cloudbot.event import CommandEvent
from cloudbot.util import colors, web
from cloudbot.util.func_utils import call_with_args


class APIError(Exception):
    def __init__(self, msg: str) -> None:
        super().__init__(msg)
        self.msg = msg


class UnknownSymbolError(APIError):
    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.name = name


class UnknownFiatCurrencyError(APIError):
    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.name = name


class APIResponse:
    def __init__(
        self,
        api: "CoinMarketCapAPI",
        data: "UntypedResponse",
        response: Response,
    ) -> None:
        self.api = api
        self.data = data
        self.response = response

    @classmethod
    def from_response(cls, api: "CoinMarketCapAPI", response: Response) -> Self:
        return cls(
            api, UntypedResponse.model_validate(response.json()), response
        )


_ModelT = TypeVar("_ModelT", bound="ApiModel")


class ApiModel(BaseModel, extra="forbid"):
    def cast_to(self, new_type: Type[_ModelT]) -> _ModelT:
        return new_type.model_validate(
            self.model_dump(mode="json", by_alias=True)
        )


class ResponseStatus(ApiModel):
    timestamp: str
    error_code: int
    elapsed: int
    credit_count: int
    error_message: Optional[str] = None
    notice: Optional[str] = None


class APIRequestResponse(ApiModel):
    status: ResponseStatus


class UntypedResponse(APIRequestResponse, extra="allow"):
    data: Any = None


class Platform(ApiModel):
    platform_id: int = Field(alias="id")
    name: str
    symbol: str
    slug: str
    token_address: str


class Quote(ApiModel):
    price: float
    volume_24h: float
    market_cap: float
    percent_change_1h: Union[int, float]
    percent_change_24h: Union[int, float]
    percent_change_7d: Union[int, float]
    last_updated: str
    volume_24h_reported: Optional[float] = None
    volume_7d: Optional[float] = None
    volume_7d_reported: Optional[float] = None
    volume_30d: Optional[float] = None
    volume_30d_reported: Optional[float] = None


class CryptoCurrency(ApiModel):
    currency_id: int = Field(alias="id")
    name: str
    symbol: str
    slug: str
    circulating_supply: float
    total_supply: float
    date_added: str
    num_market_pairs: int
    cmc_rank: int
    last_updated: str
    tags: List[str]
    quote: Dict[str, Quote]
    max_supply: Optional[float] = None
    market_cap_by_total_supply: Optional[float] = None
    platform: Optional[Platform] = None


class QuoteRequestResponse(APIRequestResponse):
    data: Dict[str, CryptoCurrency]


class FiatCurrency(ApiModel):
    id: int
    name: str
    sign: str
    symbol: str


class FiatCurrencyMap(APIRequestResponse):
    data: List[FiatCurrency]

    @computed_field  # type: ignore[misc]
    @property
    def symbols(self) -> Dict[str, str]:
        return {currency.symbol: currency.sign for currency in self.data}


class CryptoCurrencyEntry(ApiModel):
    id: int
    name: str
    symbol: str
    slug: str
    is_active: int
    first_historical_data: Optional[str] = None
    last_historical_data: Optional[str] = None
    platform: Optional[Platform] = None
    status: Optional[str] = None


class CryptoCurrencyMap(APIRequestResponse):
    data: List[CryptoCurrencyEntry]
    status: ResponseStatus

    @computed_field  # type: ignore[misc]
    @property
    def names(self) -> Set[str]:
        return {currency.symbol for currency in self.data}


BAD_FIELD_TYPE_MSG = (
    "field {field!r} expected type {exp_type!r}, got type {act_type!r}"
)


_T = TypeVar("_T")
_K = TypeVar("_K")
_V = TypeVar("_V")


class CacheEntry(Generic[_T]):
    def __init__(self, value: _T, expire: float) -> None:
        self.value = value
        self.expire = expire


class Cache(Generic[_K, _V]):
    def __init__(self, lock_cls: Type[ContextManager[Any]] = RLock) -> None:
        self._data: Dict[_K, CacheEntry[_V]] = {}
        self._lock = lock_cls()

    def clear(self) -> None:
        self._data.clear()

    def put(self, key: _K, value: _V, ttl: float) -> CacheEntry[_V]:
        with self._lock:
            self._data[key] = out = CacheEntry(value, time.time() + ttl)
            return out

    def get(self, key: _K) -> Optional[CacheEntry[_V]]:
        with self._lock:
            try:
                entry = self._data[key]
            except KeyError:
                return None

            if time.time() >= entry.expire:
                del self._data[key]
                return None

            return entry


class CoinMarketCapAPI:
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: str = "https://pro-api.coinmarketcap.com/v1/",
    ) -> None:
        self.api_key = api_key
        self.show_btc = False
        self.api_url = URL(api_url)
        self.cache = Cache[str, ApiModel]()

    @property
    def request_headers(self) -> Dict[str, Optional[str]]:
        return {
            "Accepts": "application/json",
            "X-CMC_PRO_API_KEY": self.api_key,
        }

    def get_currency_sign(self, currency: str) -> str:
        return self.get_fiat_currency_map().symbols[currency]

    def get_quote(self, symbol: str, currency: str = "USD") -> CryptoCurrency:
        symbol = symbol.upper()
        if symbol not in self.get_crypto_currency_map().names:
            raise UnknownSymbolError(symbol)

        if currency not in self.get_fiat_currency_map().symbols:
            raise UnknownFiatCurrencyError(currency)

        if self.show_btc:
            convert = f"{currency},BTC"
        else:
            convert = currency

        data = self.request(
            "cryptocurrency/quotes/latest",
            symbol=symbol.upper(),
            convert=convert,
        ).data.cast_to(QuoteRequestResponse)

        _, out = data.data.popitem()
        return out

    def get_fiat_currency_map(self) -> FiatCurrencyMap:
        return self._request_cache(
            "fiat_currency_map", "fiat/map", FiatCurrencyMap, 86400
        )

    def get_crypto_currency_map(self) -> CryptoCurrencyMap:
        return self._request_cache(
            "crypto_currency_map",
            "cryptocurrency/map",
            CryptoCurrencyMap,
            86400,
        )

    def _request_cache(
        self, name: str, endpoint: str, fmt: Type[_ModelT], ttl: int
    ) -> _ModelT:
        out = self.cache.get(name)
        if out is None:
            currencies = self.request(endpoint).data.cast_to(fmt)
            out = self.cache.put(name, currencies, ttl)

        return cast(_ModelT, out.value)

    def request(self, endpoint: str, **params: str) -> APIResponse:
        url = str(self.api_url / endpoint)
        with requests.get(
            url, headers=self.request_headers, params=params
        ) as response:
            api_response = APIResponse.from_response(self, response)
            self.check(api_response)

        return api_response

    def check(self, response: APIResponse) -> None:
        msg = response.data.status.error_message
        if msg:
            raise APIError(msg)


api = CoinMarketCapAPI()


def get_plugin_config(conf: Dict[str, Any], name: str, default: _T) -> _T:
    try:
        return cast(_T, conf["plugins"]["cryptocurrency"][name])
    except LookupError:
        return default


@hook.on_start()
def init_api(bot: "AbstractBot") -> None:
    api.api_key = bot.config.get_api_key("coinmarketcap")

    # Enabling this requires a paid CoinMarketCap API plan
    api.show_btc = get_plugin_config(bot.config, "show_btc", False)


class Alias:
    __slots__ = ("name", "cmds")

    def __init__(self, symbol: str, *cmds: str) -> None:
        self.name = symbol
        if symbol not in cmds:
            cmds += (symbol,)

        self.cmds = cmds


def alias_wrapper(alias: Alias) -> Callable[[str, CommandEvent], str]:
    def func(text: str, event: CommandEvent) -> str:
        event.text = alias.name + " " + text
        return call_with_args(crypto_command, event)

    func.__doc__ = f"""- Returns the current {alias.name} value"""
    func.__name__ = alias.name + "_alias"

    return func


# main command
@hook.command("crypto", "cryptocurrency")
def crypto_command(text: str, event: CommandEvent) -> str:
    """<symbol> [currency] - Returns current value of a cryptocurrency"""
    args = text.split()
    ticker = args.pop(0)

    if args:
        currency = args.pop(0).upper()
    else:
        currency = "USD"

    try:
        data = api.get_quote(ticker, currency)
    except UnknownFiatCurrencyError as e:
        return f"Unknown fiat currency {e.name!r}"
    except UnknownSymbolError as e:
        return f"Unknown cryptocurrency {e.name!r}"
    except APIError:
        event.reply("Unknown API error")
        raise

    quote = data.quote[currency]
    change = quote.percent_change_24h
    if change > 0:
        change_str = colors.parse("$(dark_green)+{}%$(clear)").format(change)
    elif change < 0:
        change_str = colors.parse("$(dark_red){}%$(clear)").format(change)
    else:
        change_str = f"{change}%"

    currency_sign = api.get_currency_sign(currency)

    if api.show_btc:
        btc_quote = data.quote["BTC"]
        btc = f"- {float(btc_quote.price):,.7f} BTC "
    else:
        btc = ""

    num_format = format_price(quote.price)

    return colors.parse(
        "{} ({}) // $(orange){}{}$(clear) {} " + btc + "// {} change"
    ).format(
        data.symbol,
        data.slug,
        currency_sign,
        num_format,
        currency,
        change_str,
    )


def format_price(price: Union[int, float]) -> str:
    price = float(price)
    if price < 1:
        precision = max(2, min(10, len(str(Decimal(str(price)))) - 2))
        num_format = "{:01,.{}f}".format(price, precision)
    else:
        num_format = f"{price:,.2f}"

    return num_format


@hook.command("currencies", "currencylist", autohelp=False)
def currency_list() -> str:
    """- List all available currencies from the API"""
    currency_map = api.get_crypto_currency_map()
    currencies = sorted(
        {(obj.symbol, obj.name) for obj in currency_map.data},
        key=itemgetter(0),
    )
    lst = [f"{symbol: <10} {name}" for symbol, name in currencies]
    lst.insert(0, "Symbol     Name")

    return "Available currencies: " + web.paste("\n".join(lst))


def make_alias(alias: Alias) -> Callable[[str, CommandEvent], str]:
    _hook = alias_wrapper(alias)
    return hook.command(*alias.cmds, autohelp=False)(_hook)


btc_alias = make_alias(Alias("btc", "bitcoin"))
ltc_alias = make_alias(Alias("ltc", "litecoin", "ltc"))
doge_alias = make_alias(Alias("doge", "dogecoin"))
