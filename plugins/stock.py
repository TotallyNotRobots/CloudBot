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
        self.symbol = symbol


class AVApi:
    def __init__(self, api_key, url="https://www.alphavantage.co/query", user_agent=None):
        self.api_key = api_key
        self.url = url
        self.user_agent = user_agent

    def _request(self, **args):
        args['apikey'] = self.api_key
        response = requests.get(self.url, params=args)
        response.raise_for_status()
        return response.json()

    def _time_series(self, func, symbol, data_type='json', output_size='compact'):
        _data = self._request(
            function="time_series_{}".format(func).upper(), symbol=symbol, outputsize=output_size, datatype=data_type
        )
        try:
            return _data["Time Series ({})".format(func.title())], _data['Meta Data']['2. Symbol']
        except LookupError:
            raise StockSymbolNotFoundError(symbol)

    def lookup(self, symbol):
        _data, sym = self._time_series('daily', symbol)
        today = max(_data.keys())
        current_data = _data[today]
        current_data = {key.split(None, 1)[1]: Decimal(value) for key, value in current_data.items()}
        current_data['symbol'] = sym
        return current_data


api = None


@hook.onload
def create_api(bot):
    """
    :type bot: cloudbot.bot.CloudBot
    """
    global api
    try:
        key = bot.config["api_keys"]["alphavantage"]
    except LookupError:
        return

    api = AVApi(key, user_agent=bot.user_agent)


number_suffixes = "TBM"


def format_num(n):
    exp = int(math.floor(math.log10(n)) / 3)
    c = number_suffixes[-(exp - 1):][:1]
    return "{:,.2f}{}".format(n / (10 ** (exp * 3)), c)


@hook.command
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

    price = data['close']
    change = price - data['open']

    parts = [
        "{close:,.2f}",
    ]

    if price != 0 or change != 0:
        data['mcap'] = format_num(price * data['volume'])

        data['change'] = change

        data['pct_change'] = change / (price - change)

        if change < 0:
            change_str = "$(red){change:+,.2f} ({pct_change:.2%})$(clear)"
        else:
            change_str = "$(dgreen){change:+,.2f} ({pct_change:.2%})$(clear)"

        data['change_str'] = change_str.format_map(data)

        parts.extend([
            "{change_str}",
            "Day Open: {open:,.2f}",
            "Day Range: {low:,.2f} - {high:,.2f}",
            "Market Cap: {mcap}"
        ])

    return colors.parse("$(clear){} {}$(clear)".format(
        out, ' | '.join(parts)
    ).format_map(data))
