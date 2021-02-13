import logging
from enum import Enum
from typing import List, Mapping, Optional

import attr

logger = logging.getLogger(__name__)


class ModeType(Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    Status = 1


PARAM_MODE_TYPES = (ModeType.A, ModeType.B, ModeType.Status)


@attr.s(hash=True)
class ChannelMode:
    """
    An IRC channel mode
    """

    character = attr.ib(type=str)
    type = attr.ib(type=ModeType)

    def has_param(self, adding: bool) -> bool:
        return self.type in PARAM_MODE_TYPES or (
            self.type is ModeType.C and adding
        )


@attr.s(hash=True)
class ModeChange:
    """
    Represents a single change of a mode
    """

    char = attr.ib(type=str)
    adding = attr.ib(type=bool)
    param = attr.ib(type=Optional[str])
    info = attr.ib(type=ChannelMode)

    @property
    def is_status(self):
        return self.info.type is ModeType.Status


@attr.s(hash=True)
class StatusMode(ChannelMode):
    """
    An IRC status mode
    """

    prefix = attr.ib(type=str)
    level = attr.ib(type=int)

    @classmethod
    def make(cls, prefix: str, char: str, level: int) -> "StatusMode":
        return cls(
            prefix=prefix, level=level, character=char, type=ModeType.Status
        )


def parse_mode_string(
    modes: str, params: List[str], server_modes: Mapping[str, ChannelMode]
) -> List[ModeChange]:
    new_modes = []
    params = params.copy()
    adding = True
    for c in modes:
        if c == "+":
            adding = True
        elif c == "-":
            adding = False
        else:
            mode_info = server_modes.get(c)
            if mode_info and mode_info.has_param(adding):
                param = params.pop(0)
            else:
                param = None

            new_modes.append(
                ModeChange(char=c, adding=adding, param=param, info=mode_info)
            )

    return new_modes
