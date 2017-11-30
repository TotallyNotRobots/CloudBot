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

API_URL = "https://api.coinmarketcap.com/v1/ticker/{}?convert={}"


# aliases
@hook.command("bitcoin", "btc", autohelp=False)
def bitcoin(text, reply):
    """ -- Returns current bitcoin value """
    # alias
    return crypto_command(" ".join(["bitcoin", text]), reply)


@hook.command("litecoin", "ltc", autohelp=False)
def litecoin(text, reply):
    """ -- Returns current litecoin value """
    # alias
    return crypto_command(" ".join(["litecoin", text]), reply)


@hook.command("dogecoin", "doge", autohelp=False)
def dogecoin(text, reply):
    """ -- Returns current dogecoin value """
    # alias
    return crypto_command(" ".join(["dogecoin", text]), reply)


# main command
@hook.command("crypto", "cryptocurrency")
def crypto_command(text, reply):
    """ <ticker> [currency] -- Returns current value of a cryptocurrency """
    args = text.split()
    ticker = args.pop(0)

    try:
        if not args:
            currency = 'USD'
        else:
            currency = args.pop(0).upper()

        encoded_ticker = quote_plus(ticker)
        encoded_currency = quote_plus(currency)
        request = requests.get(API_URL.format(encoded_ticker, encoded_currency))
        request.raise_for_status()
    except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError) as e:
        reply("Could not get value: {}".format(e))
        raise

    data = request.json()

    if "error" in data:
        return "{}.".format(data['error'])

    updated_time = datetime.fromtimestamp(float(data[0]['last_updated']))
    if (datetime.today() - updated_time).days > 2:
        # the API retains data for old ticker names that are no longer updated
        # in these cases we just return a "not found" message
        return "Currency not found."

    change = float(data[0]['percent_change_24h'])
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

    return "{} // \x0307{}{:,.2f}\x0f {} - {:,.7f} BTC // {} change".format(data[0]['symbol'],
                                                                            currency_sign,
                                                                            float(data[0]['price_' + currency.lower()]),
                                                                            currency.upper(),
                                                                            float(data[0]['price_btc']),
                                                                            change_str)
