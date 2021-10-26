"""
cryptocurrency.py

A plugin that uses the CoinMarketCap JSON API to get values for cryptocurrencies.

Created By:
    - Luke Rogers <https://github.com/lukeroge>

License:
    GPL v3
"""
import inspect
import time
import warnings
from decimal import Decimal
from numbers import Real
from operator import itemgetter
from threading import RLock
from typing import Any, Dict, List, Optional, Tuple, Type, TypeVar, Union, cast

import requests
from requests import Response
from yarl import URL

from cloudbot import hook
from cloudbot.util import colors, web
from cloudbot.util.func_utils import call_with_args


class APIError(Exception):
    def __init__(self, msg: str):
        super().__init__(msg)
        self.msg = msg


class UnknownSymbolError(APIError):
    def __init__(self, name: str):
        super().__init__(name)
        self.name = name


class UnknownFiatCurrencyError(APIError):
    def __init__(self, name: str):
        super().__init__(name)
        self.name = name


class APIResponse:
    def __init__(
        self, api, data: "UntypedResponse", response: Response
    ) -> None:
        self.api = api
        self.data = data
        self.response = response

    @classmethod
    def from_response(cls, api: "CoinMarketCapAPI", response: Response):
        return cls(api, read_data(response.json(), UntypedResponse), response)


class SchemaField:
    empty = object()

    def __init__(self, name: str, field_type: Type, default=empty):
        self.name = name
        self.field_type = field_type
        self.default = default


def _get_fields(init_func):
    signature = inspect.signature(init_func)
    for parameter in signature.parameters.values():
        if parameter.annotation is parameter.empty:
            continue

        if parameter.default is parameter.empty:
            default = SchemaField.empty
        else:
            default = parameter.default

        yield SchemaField(parameter.name, parameter.annotation, default)


class SchemaMeta(type):
    def __new__(cls, name, bases, members):
        if members.setdefault("_abstract", False):
            super_fields = ()
            for base in bases:
                if not getattr(base, "_abstract", False) and isinstance(
                    base, cls
                ):
                    super_fields = getattr(base, "_fields")
                    break

            members["_fields"] = super_fields
        else:
            members["_fields"] = tuple(_get_fields(members["__init__"]))

        return type.__new__(cls, name, bases, members)


T = TypeVar("T", bound="Schema")


class Schema(metaclass=SchemaMeta):
    # noinspection PyUnusedName
    _abstract = True
    _fields = ()

    def __init__(self, **kwargs):
        self.unknown_fields = {}
        self.unknown_fields.update(kwargs)

    def cast_to(self, new_type: Type[T]) -> T:
        return read_data(serialize(self), new_type)


class ResponseStatus(Schema):
    def __init__(
        self,
        timestamp: str,
        error_code: int,
        elapsed: int,
        credit_count: int,
        error_message: str = None,
        notice: str = None,
    ):
        super().__init__()
        self.timestamp = timestamp
        self.error_code = error_code
        self.error_message = error_message
        self.elapsed = elapsed
        self.credit_count = credit_count
        self.notice = notice


class APIRequestResponse(Schema):
    def __init__(self, status: ResponseStatus):
        super().__init__()
        self.status = status


class UntypedResponse(APIRequestResponse):
    def __init__(self, status: ResponseStatus, data: Any = None):
        super().__init__(status)
        self.data = data


class Platform(Schema):
    # noinspection PyShadowingBuiltins
    def __init__(
        self, id: int, name: str, symbol: str, slug: str, token_address: str
    ):
        super().__init__()
        self.id = id
        self.name = name
        self.symbol = symbol
        self.slug = slug
        self.token_address = token_address


class Quote(Schema):
    def __init__(
        self,
        price: Real,
        volume_24h: Real,
        market_cap: Real,
        percent_change_1h: Real,
        percent_change_24h: Real,
        percent_change_7d: Real,
        last_updated: str,
        volume_24h_reported: Real = None,
        volume_7d: Real = None,
        volume_7d_reported: Real = None,
        volume_30d: Real = None,
        volume_30d_reported: Real = None,
    ):
        super().__init__()
        self.price = price
        self.volume_24h = volume_24h
        self.volume_24h_reported = volume_24h_reported
        self.volume_7d = volume_7d
        self.volume_7d_reported = volume_7d_reported
        self.volume_30d = volume_30d
        self.volume_30d_reported = volume_30d_reported
        self.market_cap = market_cap
        self.percent_change_1h = percent_change_1h
        self.percent_change_24h = percent_change_24h
        self.percent_change_7d = percent_change_7d
        self.last_updated = last_updated


class CryptoCurrency(Schema):
    # noinspection PyShadowingBuiltins
    def __init__(
        self,
        id: int,
        name: str,
        symbol: str,
        slug: str,
        circulating_supply: Real,
        total_supply: Real,
        date_added: str,
        num_market_pairs: int,
        cmc_rank: int,
        last_updated: str,
        tags: List[str],
        quote: Dict[str, Quote],
        max_supply: Real = None,
        market_cap_by_total_supply: Real = None,
        platform: Platform = None,
    ):
        super().__init__()
        self.id = id
        self.name = name
        self.symbol = symbol
        self.slug = slug
        self.circulating_supply = circulating_supply
        self.total_supply = total_supply
        self.max_supply = max_supply
        self.market_cap_by_total_supply = market_cap_by_total_supply
        self.date_added = date_added
        self.num_market_pairs = num_market_pairs
        self.cmc_rank = cmc_rank
        self.last_updated = last_updated
        self.tags = tags
        self.platform = platform
        self.quote = quote


class QuoteRequestResponse(APIRequestResponse):
    def __init__(self, data: Dict[str, CryptoCurrency], status: ResponseStatus):
        super().__init__(status)
        self.data = data


class FiatCurrency(Schema):
    # noinspection PyShadowingBuiltins
    def __init__(self, id: int, name: str, sign: str, symbol: str):
        super().__init__()
        self.id = id
        self.name = name
        self.sign = sign
        self.symbol = symbol


class FiatCurrencyMap(APIRequestResponse):
    def __init__(self, data: List[FiatCurrency], status: ResponseStatus):
        super().__init__(status)
        self.data = data

        self.symbols = {
            currency.symbol: currency.sign for currency in self.data
        }


class CryptoCurrencyEntry(Schema):
    # noinspection PyShadowingBuiltins
    def __init__(
        self,
        id: int,
        name: str,
        symbol: str,
        slug: str,
        is_active: int,
        first_historical_data: str = None,
        last_historical_data: str = None,
        platform: Platform = None,
        status: str = None,
    ) -> None:
        super().__init__()
        self.id = id
        self.name = name
        self.symbol = symbol
        self.slug = slug
        self.is_active = is_active
        self.status = status
        self.first_historical_data = first_historical_data
        self.last_historical_data = last_historical_data
        self.platform = platform


class CryptoCurrencyMap(APIRequestResponse):
    def __init__(self, data: List[CryptoCurrencyEntry], status: ResponseStatus):
        super().__init__(status)
        self.data = data

        self.names = set(currency.symbol for currency in self.data)


BAD_FIELD_TYPE_MSG = (
    "field {field!r} expected type {exp_type!r}, got type {act_type!r}"
)


def sentinel(name: str):
    try:
        storage = getattr(sentinel, "_sentinels")
    except AttributeError:
        storage = {}
        setattr(sentinel, "_sentinels", storage)

    try:
        return storage[name]
    except KeyError:
        storage[name] = obj = object()
        return obj


_unset = sentinel("unset")


class TypeAssertError(TypeError):
    def __init__(self, obj, cls):
        super().__init__()
        self.cls = cls
        self.obj = obj


class MissingSchemaField(KeyError):
    pass


class ParseError(ValueError):
    pass


def _assert_type(obj, cls, display_cls=_unset):
    if display_cls is _unset:
        display_cls = cls

    if not isinstance(obj, cls):
        raise TypeAssertError(obj, display_cls)


def _hydrate_object(_value, _cls):
    if _cls is Any:
        return _value

    if isinstance(_cls, type) and issubclass(_cls, Schema):
        _assert_type(_value, dict)
        return read_data(_value, _cls)

    try:
        typing_cls = _cls.__origin__  # type: ignore[union-attr]
    except AttributeError:
        pass
    else:
        type_args = _cls.__args__  # type: ignore[union-attr]
        if issubclass(typing_cls, list):
            _assert_type(_value, list, _cls)

            return [_hydrate_object(v, type_args[0]) for v in _value]

        if issubclass(typing_cls, dict):
            _assert_type(_value, dict, _cls)

            return {
                _hydrate_object(k, type_args[0]): _hydrate_object(
                    v, type_args[1]
                )
                for k, v in _value.items()
            }

        # pragma: no cover
        raise TypeError("Can't match typing alias {!r}".format(typing_cls))

    _assert_type(_value, _cls)

    return _value


def read_data(data: Dict, schema_cls: Type[T]) -> T:
    fields: Tuple[SchemaField, ...] = schema_cls._fields

    out: Dict[str, Any] = {}
    field_names: List[str] = []

    for schema_field in fields:
        try:
            param_type = schema_field.field_type
            name = schema_field.name
            field_names.append(name)
            try:
                value = data[name]
            except KeyError as e:
                if schema_field.default is schema_field.empty:
                    raise MissingSchemaField(name) from e

                value = schema_field.default

            if value is None and schema_field.default is None:
                out[name] = value
                continue

            try:
                out[name] = _hydrate_object(value, param_type)
            except TypeAssertError as e:
                raise TypeError(
                    BAD_FIELD_TYPE_MSG.format(
                        field=name, exp_type=e.cls, act_type=type(e.obj)
                    )
                ) from e
        except (MissingSchemaField, TypeAssertError, ParseError) as e:
            raise ParseError(
                "Unable to parse schema {!r}".format(schema_cls.__name__)
            ) from e

    obj = schema_cls(**out)

    obj.unknown_fields.update(
        {key: data[key] for key in data if key not in field_names}
    )

    if obj.unknown_fields:
        warnings.warn(
            "Unknown fields: {} while parsing schema {!r}".format(
                list(obj.unknown_fields.keys()), schema_cls.__name__
            )
        )

    return obj


def serialize(obj):
    if isinstance(obj, Schema):
        out = {}
        for field in obj._fields:  # type: SchemaField
            val = getattr(obj, field.name)
            out[field.name] = serialize(val)

        if obj.unknown_fields:
            out.update(obj.unknown_fields)

        return out

    if isinstance(obj, list):
        return [serialize(o) for o in obj]

    if isinstance(obj, dict):
        return {k: serialize(v) for k, v in obj.items()}

    return obj


class CacheEntry:
    def __init__(self, value, expire):
        self.value = value
        self.expire = expire


class Cache:
    def __init__(self, lock_cls=RLock):
        self._data = {}
        self._lock = lock_cls()

    def clear(self):
        self._data.clear()

    def put(self, key, value, ttl) -> CacheEntry:
        with self._lock:
            self._data[key] = out = CacheEntry(value, time.time() + ttl)
            return out

    def get(self, key: str) -> Optional[CacheEntry]:
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
        api_key: str = None,
        api_url: str = "https://pro-api.coinmarketcap.com/v1/",
    ) -> None:
        self.api_key = api_key
        self.show_btc = False
        self.api_url = URL(api_url)
        self.cache = Cache()

    @property
    def request_headers(self):
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
            convert = "{},BTC".format(currency)
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
        self, name: str, endpoint: str, fmt: Type[T], ttl: int
    ) -> T:
        out = self.cache.get(name)
        if out is None:
            currencies = self.request(endpoint).data.cast_to(fmt)
            out = self.cache.put(name, currencies, ttl)

        return out.value

    def request(self, endpoint: str, **params) -> APIResponse:
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


def get_plugin_config(conf, name, default):
    try:
        return conf["plugins"]["cryptocurrency"][name]
    except LookupError:
        return default


@hook.onload()
def init_api(bot):
    api.api_key = bot.config.get_api_key("coinmarketcap")

    # Enabling this requires a paid CoinMarketCap API plan
    api.show_btc = get_plugin_config(bot.config, "show_btc", False)


class Alias:
    __slots__ = ("name", "cmds")

    def __init__(self, symbol, *cmds):
        self.name = symbol
        if symbol not in cmds:
            cmds += (symbol,)

        self.cmds = cmds


ALIASES = (
    Alias("btc", "bitcoin"),
    Alias("ltc", "litecoin"),
    Alias("doge", "dogecoin"),
)


def alias_wrapper(alias):
    def func(text, event):
        event.text = alias.name + " " + text
        return call_with_args(crypto_command, event)

    func.__doc__ = """- Returns the current {} value""".format(alias.name)
    func.__name__ = alias.name + "_alias"

    return func


# main command
@hook.command("crypto", "cryptocurrency")
def crypto_command(text, event):
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
        return "Unknown fiat currency {!r}".format(e.name)
    except UnknownSymbolError as e:
        return "Unknown cryptocurrency {!r}".format(e.name)
    except APIError:
        event.reply("Unknown API error")
        raise

    quote = data.quote[currency]
    change = cast(Union[int, float], quote.percent_change_24h)
    if change > 0:
        change_str = colors.parse("$(dark_green)+{}%$(clear)").format(change)
    elif change < 0:
        change_str = colors.parse("$(dark_red){}%$(clear)").format(change)
    else:
        change_str = "{}%".format(change)

    currency_sign = api.get_currency_sign(currency)

    if api.show_btc:
        btc_quote = data.quote["BTC"]
        btc = "- {:,.7f} BTC ".format(float(btc_quote.price))
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


def format_price(price: Union[int, float, Real]) -> str:
    price = float(price)
    if price < 1:
        precision = max(2, min(10, -Decimal(str(price)).as_tuple().exponent))
        num_format = "{:01,.{}f}".format(price, precision)
    else:
        num_format = "{:,.2f}".format(price)

    return num_format


@hook.command("currencies", "currencylist", autohelp=False)
def currency_list():
    """- List all available currencies from the API"""
    currency_map = api.get_crypto_currency_map()
    currencies = sorted(
        set((obj.symbol, obj.name) for obj in currency_map.data),
        key=itemgetter(0),
    )
    lst = ["{: <10} {}".format(symbol, name) for symbol, name in currencies]
    lst.insert(0, "Symbol     Name")

    return "Available currencies: " + web.paste("\n".join(lst))


def make_alias(alias):
    _hook = alias_wrapper(alias)
    return hook.command(*alias.cmds, autohelp=False)(_hook)


btc_alias = make_alias(Alias("btc", "bitcoin"))
ltc_alias = make_alias(Alias("ltc", "litecoin"))
doge_alias = make_alias(Alias("doge", "dogecoin"))
