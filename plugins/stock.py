"""
Gets basic stock stats from the AlphaVantage API

Authors:
    - linuxdaemon <linuxdaemon@snoonet.org>
"""
import math
from decimal import Decimal

import requests

from cloudbot import hook
from cloudbot.util import colors


class APIError(Exception):
    pass


class StockSymbolNotFoundError(APIError):
    def __init__(self, symbol):
        super().__init__(symbol)
        self.symbol = symbol


class AVApi:
    def __init__(
        self,
        api_key=None,
        url="https://www.alphavantage.co/query",
        user_agent=None,
    ):
        self.api_key = api_key
        self.url = url
        self.user_agent = user_agent

    def __bool__(self):
        return bool(self.api_key)

    def _request(self, **args):
        args["apikey"] = self.api_key
        response = requests.get(self.url, params=args)
        response.raise_for_status()
        return response.json()

    def _time_series(
        self, func, symbol, data_type="json", output_size="compact"
    ):
        _data = self._request(
            function="time_series_{}".format(func).upper(),
            symbol=symbol,
            outputsize=output_size,
            datatype=data_type,
        )
        try:
            return (
                _data["Time Series ({})".format(func.title())],
                _data["Meta Data"]["2. Symbol"],
            )
        except LookupError as e:
            raise StockSymbolNotFoundError(symbol) from e

    def lookup(self, symbol):
        _data, sym = self._time_series("daily", symbol)
        today = max(_data.keys())
        current_data = _data[today]
        current_data = {
            key.split(None, 1)[1]: Decimal(value)
            for key, value in current_data.items()
        }
        current_data["symbol"] = sym
        return current_data


api = AVApi()

number_suffixes = ["", "", "M", "B", "T"]


def _get_group_count(num):
    if not num:
        return 0

    n = math.floor(math.log10(abs(num))) // 3
    if n <= 0:
        return 0

    return n


def format_money(n):
    idx = min(_get_group_count(n), len(number_suffixes))
    c = number_suffixes[idx]
    if c:
        exp = idx * 3
        n = n / (10 ** exp)

    return "{:,.2f}{}".format(n, c)


@hook.on_start()
def setup_api(bot):
    api.api_key = bot.config.get_api_key("alphavantage")
    api.user_agent = bot.user_agent


@hook.command()
def stock(text):
    """<symbol> - Get stock information from the AlphaVantage API"""
    if not api:
        return "This command requires an AlphaVantage API key from https://alphavantage.co"

    symbol = text.strip().split()[0]

    try:
        data = api.lookup(symbol)
    except StockSymbolNotFoundError as e:
        return "Unknown stock symbol {!r}".format(e.symbol)

    out = "$(bold){symbol}$(bold):"

    price = data["close"]
    change = price - data["open"]

    parts = [
        "{close:,.2f}",
    ]

    if price != 0 or change != 0:
        data["mcap"] = format_money(price * data["volume"])

        data["change"] = change

        data["pct_change"] = change / (price - change)

        if change < 0:
            change_str = "$(red){change:+,.2f} ({pct_change:.2%})$(clear)"
        else:
            change_str = "$(dgreen){change:+,.2f} ({pct_change:.2%})$(clear)"

        data["change_str"] = change_str.format_map(data)

        parts.extend(
            [
                "{change_str}",
                "Day Open: {open:,.2f}",
                "Day Range: {low:,.2f} - {high:,.2f}",
                "Market Cap: {mcap}",
            ]
        )

    return colors.parse(
        "$(clear){} {}$(clear)".format(out, " | ".join(parts)).format_map(data)
    )
