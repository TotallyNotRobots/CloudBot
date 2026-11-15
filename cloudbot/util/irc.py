from __future__ import annotations

import logging
from enum import Enum
from typing import TYPE_CHECKING

import attrs

if TYPE_CHECKING:
    from collections.abc import Mapping

    from typing import Self

logger = logging.getLogger(__name__)


class ModeType(Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    Status = 1


PARAM_MODE_TYPES = (ModeType.A, ModeType.B, ModeType.Status)


@attrs.define(hash=True)
class ChannelMode:
    """
    An IRC channel mode
    """

    character: str
    type: ModeType

    def has_param(self, adding: bool) -> bool:
        return self.type in PARAM_MODE_TYPES or (
            self.type is ModeType.C and adding
        )


@attrs.define(hash=True)
class ModeChange:
    """
    Represents a single change of a mode
    """

    char: str
    adding: bool
    param: str | None
    info: ChannelMode | None

    @property
    def is_status(self) -> bool:
        if not self.info:
            return False

        return self.info.type == ModeType.Status


@attrs.define(hash=True)
class StatusMode(ChannelMode):
    """
    An IRC status mode
    """

    prefix: str
    level: int

    @classmethod
    def make(cls, prefix: str, char: str, level: int) -> Self:
        return cls(
            prefix=prefix, level=level, character=char, type=ModeType.Status
        )


def parse_mode_string(
    modes: str, params: list[str], server_modes: Mapping[str, ChannelMode]
) -> list[ModeChange]:
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
            if not mode_info:
                logger.warning("No ModeInfo found for %s", c)

            if mode_info and mode_info.has_param(adding):
                param = params.pop(0)
            else:
                param = None

            new_modes.append(
                ModeChange(char=c, adding=adding, param=param, info=mode_info)
            )

    return new_modes
