"""
cryptocurrency.py

A plugin that uses the CoinMarketCap JSON API to get values for cryptocurrencies.

Created By:
    - Luke Rogers <https://github.com/lukeroge>

License:
    GPL v3
"""
import asyncio
from collections import defaultdict
from datetime import datetime, timedelta
from operator import itemgetter
from threading import RLock

import requests
from requests import Session
from yarl import URL

from cloudbot import hook
from cloudbot.event import CommandEvent
from cloudbot.util import colors, web
from cloudbot.util.func_utils import call_with_args

CURRENCY_SYMBOLS = {
    'USD': '$',
    'GBP': '£',
    'EUR': '€',
}


class APIError(Exception):
    pass


class APIRateLimitError(APIError):
    pass


class TickerNotFound(APIError):
    def __init__(self, name):
        self.currency = name


class CurrencyConversionError(APIError):
    def __init__(self, in_name, out_name):
        self.in_name = in_name
        self.out_name = out_name


class CMCApi:
    def __init__(self, user_agent=None, url="https://api.coinmarketcap.com/v1"):
        self.url = URL(url)
        self._request_times = []

        self._cache = defaultdict(dict)
        self._lock = RLock()
        self._now = datetime.now()

        self._session = Session()

        self.set_user_agent(user_agent)

    def set_user_agent(self, user_agent=None):
        if user_agent is None:
            user_agent = requests.utils.default_user_agent()

        with self._lock:
            self._session.headers['User-Agent'] = user_agent

    def close(self):
        self._session.close()

    def _request(self, endpoint, params=None):
        self._request_times[:] = [t for t in self._request_times if (self._now - t) < timedelta(minutes=1)]
        if len(self._request_times) > 10:
            raise APIRateLimitError

        with self._session.get(self.url / endpoint, params=params) as response:
            self._request_times.append(self._now)
            response.raise_for_status()
            return response.json()

    def _update(self, key, obj):
        old_obj = self._cache[key.lower()]
        if old_obj.get("last_updated") != obj["last_updated"]:
            old_obj.clear()

        old_obj.update(obj)

    def _handle_obj(self, *objs):
        with self._lock:
            for obj in objs:
                self._update(obj["id"], obj)
                self._update(obj["symbol"], obj)

    def _get_currency_data(self, id_or_symbol, out_currency="USD"):
        self._now = datetime.now()
        old_data = self._cache[id_or_symbol.lower()]
        _id = old_data.get("id", id_or_symbol)
        last_updated = datetime.fromtimestamp(float(old_data.get('last_updated', "0")))
        diff = self._now - last_updated
        price_key = "price_" + out_currency.lower()
        if diff > timedelta(minutes=5) or price_key not in old_data:
            responses = self._request("ticker/" + _id.lower(), params={'limit': 0, 'convert': out_currency})
            self._handle_obj(*responses)
            data = self._cache[id_or_symbol.lower()]
            last_updated = datetime.fromtimestamp(float(data.get('last_updated', "0")))
            diff = self._now - last_updated
            if diff > timedelta(days=2):
                raise TickerNotFound(id_or_symbol)
            elif price_key not in data:
                raise CurrencyConversionError(data["symbol"], out_currency)

            return self._cache[id_or_symbol.lower()]

        return old_data

    def update_cache(self):
        with self._lock:
            self._now = datetime.now()
            data = self._request("ticker", params={'limit': 0})
            self._handle_obj(*data)

    def get_currency_data(self, id_or_symbol, out_currency="USD"):
        with self._lock:
            data = self._get_currency_data(id_or_symbol, out_currency)
            return data

    @property
    def currencies(self):
        return self._cache.values()


api = CMCApi()


class Alias:
    __slots__ = ("name", "cmds")

    def __init__(self, name, *cmds):
        self.name = name
        if name not in cmds:
            cmds = (name,) + cmds

        self.cmds = cmds


ALIASES = (
    Alias('bitcoin', 'btc'),
    Alias('litecoin', 'ltc'),
    Alias('dogecoin', 'doge'),
)


def alias_wrapper(alias):
    def func(text, event):
        event.text = alias.name + " " + text
        return call_with_args(crypto_command, event)

    func.__doc__ = """- Returns the current {} value""".format(alias.name)
    func.__name__ = alias.name + "_alias"

    return func


def init_aliases():
    for alias in ALIASES:
        _hook = alias_wrapper(alias)
        globals()[_hook.__name__] = hook.command(*alias.cmds, autohelp=False)(_hook)


@hook.onload
@hook.periodic(3600)
def update_cache(bot):
    api.set_user_agent(bot.user_agent)
    api.update_cache()


@hook.on_unload
def close_api():
    api.close()


# main command
@hook.command("crypto", "cryptocurrency")
def crypto_command(text):
    """<ticker> [currency] - Returns current value of a cryptocurrency"""
    args = text.split()
    ticker = args.pop(0)

    if not args:
        currency = 'USD'
    else:
        currency = args.pop(0).upper()

    try:
        data = api.get_currency_data(ticker, currency.upper())
    except TickerNotFound as e:
        return "Unable to find ticker for '{}'".format(e.currency)
    except CurrencyConversionError as e:
        return "Unable to convert '{}' to '{}'".format(e.in_name, e.out_name)
    except APIRateLimitError:
        return "API rate limit reached, please try again later"

    change = float(data['percent_change_24h'])
    if change > 0:
        change_str = "$(dark_green) {}%$(clear)".format(change)
    elif change < 0:
        change_str = "$(dark_red) {}%$(clear)".format(change)
    else:
        change_str = "{}%".format(change)

    currency_sign = CURRENCY_SYMBOLS.get(currency, '')

    converted_value = data['price_' + currency.lower()]

    return colors.parse("{} ({}) // $(orange){}{:,.2f}$(clear) {} - {:,.7f} BTC // {} change".format(
        data['symbol'], data['id'], currency_sign, float(converted_value), currency.upper(),
        float(data['price_btc']), change_str
    ))


@hook.command("currencies", "currencylist", autohelp=False)
def currency_list():
    currencies = sorted(set((obj["symbol"], obj["id"]) for obj in api.currencies), key=itemgetter(0))
    lst = [
        '{: <10} {}'.format(symbol, name) for symbol, name in currencies
    ]
    lst.insert(0, 'Symbol     Name')

    return "Available currencies: " + web.paste('\n'.join(lst))


init_aliases()
