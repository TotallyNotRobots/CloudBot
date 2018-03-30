"""
Simple IRC line parser

Backported from async-irc (https://github.com/snoonetIRC/async-irc.git)
"""

import re
from abc import ABC, abstractmethod
from collections import OrderedDict

TAGS_SENTINEL = '@'
TAGS_SEP = ';'
TAG_VALUE_SEP = '='

PREFIX_SENTINEL = ':'
PREFIX_USER_SEP = '!'
PREFIX_HOST_SEP = '@'

PARAM_SEP = ' '
TRAIL_SENTINEL = ':'

CAP_SEP = ' '
CAP_VALUE_SEP = '='

PREFIX_RE = re.compile(r':?(?P<nick>.+?)(?:!(?P<user>.+?))?(?:@(?P<host>.+?))?')

TAG_VALUE_ESCAPES = {
    '\\s': ' ',
    '\\:': ';',
    '\\r': '\r',
    '\\n': '\n',
    '\\\\': '\\',
}

TAG_VALUE_UNESCAPES = {
    unescaped: escaped
    for escaped, unescaped in TAG_VALUE_ESCAPES.items()
}


class Parseable(ABC):
    """Abstract class for parseable objects"""

    @abstractmethod
    def __str__(self):
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def parse(text):
        """Parse the object from a string"""
        raise NotImplementedError


class Cap(Parseable):
    """Represents a CAP entity as defined in IRCv3.2"""

    def __init__(self, name, value=None):
        self.name = name
        self.value = value or None

    def __str__(self):
        if self.value:
            return CAP_VALUE_SEP.join((self.name, self.value))
        return self.name

    def __eq__(self, other):
        if isinstance(other, Cap):
            return self.name == other.name

        return NotImplemented

    def __hash__(self):
        return hash((self.name, self.value))

    @staticmethod
    def parse(text):
        """Parse a CAP entity from a string"""
        name, _, value = text.partition(CAP_VALUE_SEP)
        return Cap(name, value)


class CapList(Parseable, list):
    """Represents a list of CAP entities"""

    def __str__(self):
        return CAP_SEP.join(map(str, self))

    @staticmethod
    def parse(text):
        """Parse a list of CAPs from a string"""
        return CapList(map(Cap.parse, text.split(CAP_SEP)))


class MessageTag(Parseable):
    """
    Basic class to wrap a message tag
    """

    def __init__(self, name, value=None):
        self.name = name
        self.value = value

    @staticmethod
    def unescape(value):
        """
        Replace the escaped characters in a tag value with their literals
        :param value: Escaped string
        :return: Unescaped string
        """
        new_value = ""
        found = False
        for i in range(len(value)):
            if found:
                found = False
                continue

            if value[i] == '\\':
                if i + 1 >= len(value):
                    raise ValueError("Unexpected end of string while parsing: {}".format(value))

                new_value += TAG_VALUE_ESCAPES[value[i:i + 2]]
                found = True
            else:
                new_value += value[i]

        return new_value

    @staticmethod
    def escape(value):
        """
        Replace characters with their escaped variants
        :param value: The raw string
        :return: The escaped string
        """
        return "".join(TAG_VALUE_UNESCAPES.get(c, c) for c in value)

    def __str__(self):
        if self.value:
            return "{}{}{}".format(
                self.name, TAG_VALUE_SEP, self.escape(self.value)
            )

        return self.name

    @staticmethod
    def parse(text):
        """
        Parse a tag from a string
        :param text: The basic tag string
        :return: The MessageTag object
        """
        name, _, value = text.partition(TAG_VALUE_SEP)
        if value:
            value = MessageTag.unescape(value)

        return MessageTag(name, value or None)


class TagList(Parseable, OrderedDict):
    """Object representing the list of message tags on a line"""

    def __init__(self, tags) -> None:
        super().__init__((tag.name, tag) for tag in tags)

    def __str__(self):
        return TAGS_SENTINEL + TAGS_SEP.join(map(str, self.values()))

    @staticmethod
    def parse(text):
        """
        Parse the list of tags from a string
        :param text: The string to parse
        :return: The parsed object
        """
        return TagList(
            map(MessageTag.parse, filter(None, text.split(TAGS_SEP)))
        )


class Prefix(Parseable):
    """
    Object representing the prefix of a line
    """

    def __init__(self, nick, user=None, host=None):
        self.nick = nick
        self.user = user
        self.host = host

    @property
    def mask(self):
        """
        The complete n!u@h mask
        """
        m = self.nick
        if self.user:
            m += PREFIX_USER_SEP + self.user

        if self.host:
            m += PREFIX_HOST_SEP + self.host

        return m

    def __str__(self):
        if self:
            return PREFIX_SENTINEL + self.mask

        return ""

    def __bool__(self):
        return bool(self.nick)

    @staticmethod
    def parse(text):
        """
        Parse the prefix from a string
        :param text: String to parse
        :return: Parsed Object
        """
        if not text:
            return Prefix('')

        match = PREFIX_RE.fullmatch(text)
        assert match, "Prefix did not match prefix pattern"
        nick, user, host = match.groups()
        return Prefix(nick, user, host)


class ParamList(Parseable, list):
    """
    An object representing the parameter list from a line
    """

    def __init__(self, seq, has_trail=False):
        super().__init__(seq)
        self.has_trail = has_trail or (self and PARAM_SEP in self[-1])

    def __str__(self):
        if self.has_trail and self[-1][0] != TRAIL_SENTINEL:
            return PARAM_SEP.join(self[:-1] + [TRAIL_SENTINEL + self[-1]])

        return PARAM_SEP.join(self)

    @staticmethod
    def parse(text):
        """
        Parse a list of parameters
        :param text: The list of parameters
        :return: The parsed object
        """
        args = []
        has_trail = False
        while text:
            if text[0] == TRAIL_SENTINEL:
                args.append(text[1:])
                has_trail = True
                break

            arg, _, text = text.partition(PARAM_SEP)
            if arg:
                args.append(arg)

        return ParamList(args, has_trail=has_trail)


class Message(Parseable):
    """
    An object representing a parsed IRC line
    """

    def __init__(self, tags=None, prefix=None, command=None, parameters=None):
        self.tags = tags
        self.prefix = prefix
        self.command = command
        self.parameters = parameters

    @property
    def parts(self):
        """The parts that make up this message"""
        return self.tags, self.prefix, self.command, self.parameters

    def __str__(self):
        return PARAM_SEP.join(map(str, filter(None, self.parts)))

    def __bool__(self):
        return any(self.parts)

    @staticmethod
    def parse(text):
        """Parse an IRC message in to objects"""
        if isinstance(text, bytes):
            text = text.decode()

        tags = ''
        prefix = ''
        if text.startswith(TAGS_SENTINEL):
            tags, _, text = text.partition(PARAM_SEP)

        if text.startswith(PREFIX_SENTINEL):
            prefix, _, text = text.partition(PARAM_SEP)

        command, _, params = text.partition(PARAM_SEP)
        tags = TagList.parse(tags[1:])
        prefix = Prefix.parse(prefix[1:])
        command = command.upper()
        params = ParamList.parse(params)
        return Message(tags, prefix, command, params)
