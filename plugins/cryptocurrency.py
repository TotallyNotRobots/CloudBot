"""
cryptocurrency.py

A plugin that uses the CoinMarketCap JSON API to get values for cryptocurrencies.

Created By:
    - Luke Rogers <https://github.com/lukeroge>

License:
    GPL v3
"""
from datetime import datetime
from urllib.parse import quote_plus

import requests

from cloudbot import hook

API_URL = "https://api.coinmarketcap.com/v1/ticker/{}"


def get_request(ticker, currency):
    return requests.get(API_URL.format(quote_plus(ticker)), params={'convert': currency})


# aliases
@hook.command("bitcoin", "btc", autohelp=False)
def bitcoin(text):
    """ -- Returns current bitcoin value """
    # alias
    return crypto_command(" ".join(["bitcoin", text]))


@hook.command("litecoin", "ltc", autohelp=False)
def litecoin(text):
    """ -- Returns current litecoin value """
    # alias
    return crypto_command(" ".join(["litecoin", text]))


@hook.command("dogecoin", "doge", autohelp=False)
def dogecoin(text):
    """ -- Returns current dogecoin value """
    # alias
    return crypto_command(" ".join(["dogecoin", text]))


# main command
@hook.command("crypto", "cryptocurrency")
def crypto_command(text):
    """ <ticker> [currency] -- Returns current value of a cryptocurrency """
    args = text.split()
    ticker = args.pop(0)

    if not args:
        currency = 'USD'
    else:
        currency = args.pop(0).upper()

    try:
        request = get_request(ticker, currency)
        request.raise_for_status()
    except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError) as e:
        return "Could not get value: {}".format(e)

    data = request.json()

    if "error" in data:
        return "{}.".format(data['error'])

    data = data[0]

    updated_time = datetime.fromtimestamp(float(data['last_updated']))
    if (datetime.today() - updated_time).days > 2:
        # the API retains data for old ticker names that are no longer updated
        # in these cases we just return a "not found" message
        return "Currency not found."

    change = float(data['percent_change_24h'])
    if change > 0:
        change_str = "\x033 {}%\x0f".format(change)
    elif change < 0:
        change_str = "\x035 {}%\x0f".format(change)
    else:
        change_str = "{}%".format(change)

    if currency == 'GBP':
        currency_sign = '£'
    elif currency == 'EUR':
        currency_sign = '€'
    elif currency == 'USD':
        currency_sign = '$'
    else:
        currency_sign = ''

    try:
        converted_value = data['price_' + currency.lower()]
    except LookupError:
        return "Unable to convert to currency '{}'".format(currency)

    return "{} // \x0307{}{:,.2f}\x0f {} - {:,.7f} BTC // {} change".format(data['symbol'],
                                                                            currency_sign,
                                                                            float(converted_value),
                                                                            currency.upper(),
                                                                            float(data['price_btc']),
                                                                            change_str)
