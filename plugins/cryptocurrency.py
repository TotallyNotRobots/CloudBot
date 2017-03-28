"""
cryptocurrency.py

A plugin that uses the CoinMarketCap JSON API to get values for cryptocurrencies.

Created By:
    - Luke Rogers <https://github.com/lukeroge>

Special Thanks:
    - https://coinmarketcap-nexuist.rhcloud.com/

License:
    GPL v3
"""
from datetime import datetime
from urllib.parse import quote_plus

import requests

from cloudbot import hook

API_URL = "https://coinmarketcap-nexuist.rhcloud.com/api/{}"


# aliases
@hook.command("bitcoin", "btc", autohelp=False)
def bitcoin(text):
    """ -- Returns current bitcoin value """
    # alias
    return crypto_command(" ".join(["btc", text]))


@hook.command("litecoin", "ltc", autohelp=False)
def litecoin(text):
    """ -- Returns current litecoin value """
    # alias
    return crypto_command(" ".join(["ltc", text]))


@hook.command("dogecoin", "doge", autohelp=False)
def dogecoin(text):
    """ -- Returns current dogecoin value """
    # alias
    return crypto_command(" ".join(["doge", text]))


# main command
@hook.command("crypto", "cryptocurrency")
def crypto_command(text):
    """ <ticker> [currency] -- Returns current value of a cryptocurrency """
    args = text.split()
    ticker = args.pop(0)

    try:
        if not args:
            currency = 'usd'
        else:
            currency = args.pop(0).lower()

        encoded = quote_plus(ticker)
        request = requests.get(API_URL.format(encoded))
        request.raise_for_status()
    except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError) as e:
        return "Could not get value: {}".format(e)

    data = request.json()

    if "error" in data:
        return "{}.".format(data['error'])

    updated_time = datetime.fromtimestamp(float(data['timestamp']))
    if (datetime.today() - updated_time).days > 2:
        # the API retains data for old ticker names that are no longer updated
        # in these cases we just return a "not found" message
        return "Currency not found."

    change = float(data['change'])
    if change > 0:
        change_str = "\x033 {}%\x0f".format(change)
    elif change < 0:
        change_str = "\x035 {}%\x0f".format(change)
    else:
        change_str = "{}%".format(change)

    if currency == 'gbp':
        currency_sign = '£'
    elif currency == 'eur':
        currency_sign = '€'
    else:
        currency_sign = '$'

    return "{} // \x0307{}{:,.2f}\x0f {} - {:,.7f} BTC // {} change".format(data['symbol'].upper(),
                                                                            currency_sign,
                                                                            float(data['price'][currency]),
                                                                            currency.upper(),
                                                                            float(data['price']['btc']),
                                                                            change_str)
