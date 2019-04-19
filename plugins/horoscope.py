# Plugin by Infinity - <https://github.com/infinitylabs/UguuBot>

import requests
from bs4 import BeautifulSoup
from sqlalchemy import Column, String, Table, select

from cloudbot import hook
from cloudbot.util import database, colors

table = Table(
    'horoscope',
    database.metadata,
    Column('nick', String, primary_key=True),
    Column('sign', String)
)

URL = "http://www.horoscope.com/us/horoscopes/general/horoscope-general-daily-today.aspx"

SIGN_MAP = {
    'aries': '1',
    'taurus': '2',
    'gemini': '3',
    'cancer': '4',
    'leo': '5',
    'virgo': '6',
    'libra': '7',
    'scorpio': '8',
    'sagittarius': '9',
    'capricorn': '10',
    'aquarius': '11',
    'pisces': '12',
}


def get_sign(db, nick):
    row = db.execute(select([table.c.sign]).where(table.c.nick == nick.lower())).fetchone()
    if not row:
        return None

    return row[0]


def set_sign(db, nick, sign):
    res = db.execute(table.update().values(sign=sign.lower()).where(table.c.nick == nick.lower()))
    if res.rowcount == 0:
        db.execute(table.insert().values(nick=nick.lower(), sign=sign.lower()))

    db.commit()


@hook.command(autohelp=False)
def horoscope(text, db, bot, nick, event):
    """[sign] - get your horoscope"""

    headers = {'User-Agent': bot.user_agent}

    # check if the user asked us not to save his details
    dontsave = text.endswith(" dontsave")
    if dontsave:
        sign = text[:-9].strip().lower()
    else:
        sign = text.strip().lower()

    if not sign:
        sign = get_sign(db, nick)
        if not sign:
            event.notice_doc()
            return

        sign = sign.strip().lower()

    if sign not in SIGN_MAP:
        event.notice("Unknown sign: {}".format(sign))
        return

    params = {
        "sign": SIGN_MAP[sign]
    }

    try:
        request = requests.get(URL, params=params, headers=headers)
        request.raise_for_status()
    except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError) as e:
        event.reply("Could not get horoscope: {}. URL Error".format(e))
        raise

    soup = BeautifulSoup(request.text)

    horoscope_text = soup.find("main", class_="main-horoscope").find("p").text
    result = colors.parse("$(b){}$(b) {}").format(sign, horoscope_text)

    if text and not dontsave:
        set_sign(db, nick, sign)

    event.message(result)
