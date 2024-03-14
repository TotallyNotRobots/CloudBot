# Plugin by Infinity - <https://github.com/infinitylabs/UguuBot>
import requests
from sqlalchemy import Column, String, Table, select
from yarl import URL

from cloudbot import hook
from cloudbot.util import colors, database
from cloudbot.util.http import parse_soup

table = Table(
    "horoscope",
    database.metadata,
    Column("nick", String, primary_key=True),
    Column("sign", String),
)

BASE_URL = URL("https://www.horoscope.com/us/horoscopes/general/")
DAILY_URL = BASE_URL / "horoscope-general-daily-today.aspx"

SIGN_MAP = {
    "aries": "1",
    "taurus": "2",
    "gemini": "3",
    "cancer": "4",
    "leo": "5",
    "virgo": "6",
    "libra": "7",
    "scorpio": "8",
    "sagittarius": "9",
    "capricorn": "10",
    "aquarius": "11",
    "pisces": "12",
}


def get_sign(db, nick):
    row = db.execute(
        select([table.c.sign]).where(table.c.nick == nick.lower())
    ).fetchone()
    if not row:
        return None

    return row[0]


def set_sign(db, nick, sign):
    res = db.execute(
        table.update()
        .values(sign=sign.lower())
        .where(table.c.nick == nick.lower())
    )
    if res.rowcount == 0:
        db.execute(table.insert().values(nick=nick.lower(), sign=sign.lower()))

    db.commit()


def parse_input(text):
    """
    >>> parse_input('')
    (None, False)
    >>> parse_input('aries')
    ('aries', False)
    >>> parse_input('aries dontsave')
    ('aries', True)
    """
    if not text:
        return None, False

    args = text.split()
    sign = args.pop(0)

    dontsave = "dontsave" in args

    return sign, dontsave


def parse_or_lookup(text, db, nick, event):
    sign, dontsave = parse_input(text)

    if not sign:
        sign = get_sign(db, nick)
        if not sign:
            event.notice_doc()
            return None, None

        sign = sign.strip().lower()

    if sign not in SIGN_MAP:
        event.notice("Unknown sign: {}".format(sign))
        return None, None

    return sign, dontsave


class HoroscopeParseError(Exception):
    def __init__(self, msg, content):
        super().__init__(msg)
        self.content = content


def parse_page(content):
    """Parse the horoscope page

    >>> parse_page('')
    Traceback (most recent call last):
        [...]
    plugins.horoscope.HoroscopeParseError: Unable to parse horoscope
    >>> parse_page('<div class="main-horoscope"><div>hello world</div></div>')
    Traceback (most recent call last):
        [...]
    plugins.horoscope.HoroscopeParseError: Unable to parse horoscope
    >>> parse_page('<div class="main-horoscope"><p>hello world</p></div>')
    'hello world'
    """
    soup = parse_soup(content)
    container = soup.find("div", class_="main-horoscope")
    if not container:
        raise HoroscopeParseError("Unable to parse horoscope", content)

    para = container.p
    if not para:
        raise HoroscopeParseError("Unable to parse horoscope", content)

    return para.text


@hook.command(autohelp=False)
def horoscope(text, db, bot, nick, event):
    """[sign] - get your horoscope"""

    headers = {"User-Agent": bot.user_agent}

    sign, dontsave = parse_or_lookup(text, db, nick, event)

    if not sign:
        return

    params = {"sign": SIGN_MAP[sign]}

    try:
        with requests.get(
            str(DAILY_URL), params=params, headers=headers
        ) as request:
            request.raise_for_status()
    except (
        requests.exceptions.HTTPError,
        requests.exceptions.ConnectionError,
    ) as e:
        event.reply("Could not get horoscope: {}. URL Error".format(e))
        raise

    try:
        horoscope_text = parse_page(request.text)
    except HoroscopeParseError:
        event.reply("Unable to parse horoscope posting")
        raise

    result = colors.parse("$(b){}$(b) {}").format(sign, horoscope_text)

    if text and not dontsave:
        set_sign(db, nick, sign)

    event.message(result)
