"""
textgen.py

A class used to quickly generate random strings.

Created By:
    - Luke Rogers <https://github.com/lukeroge>

Maintainer:
    - Luke Rogers <https://github.com/lukeroge>

License:
    BSD license

    Copyright (c) 2013-2015 Luke Rogers and CloudBot Contributors
    All rights reserved.

    Redistribution and use in source and binary forms, with or without modification,
    are permitted provided that the following conditions are met:

        1. Redistributions of source code must retain the above copyright notice,
           this list of conditions and the following disclaimer.

        2. Redistributions in binary form must reproduce the above copyright
           notice, this list of conditions and the following disclaimer in the
           documentation and/or other materials provided with the distribution.

        3. Neither the name of CloudBot nor the names of its contributors may be used
           to endorse or promote products derived from this software without
           specific prior written permission.

    THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
    ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
    WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
    DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
    ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
    (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
    LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
    ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
    (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
    SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

from __future__ import annotations

import copy
import random
import re
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Self

from pydantic import BaseModel, Field, model_validator

if TYPE_CHECKING:
    from pathlib import Path

TEMPLATE_RE = re.compile(r"{(.+?)\}")


class TemplateConfig(BaseModel):
    templates: list[str] | None = None
    target_templates: list[str] | None = None
    parts: dict[str, list[str | tuple[str, int]]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def check_templates(self) -> Self:
        if not self.templates and not self.target_templates:
            raise ValueError(
                "Either templates or target_templates must be specified"
            )

        return self

    @classmethod
    def from_json_file(cls, path: Path) -> Self:
        return cls.model_validate_json(path.read_text(encoding="utf-8"))

    def make_generator(
        self,
        *,
        has_target: bool = False,
        default_templates: list[int] | None = None,
        variables: dict[str, str] | None = None,
    ) -> TextGenerator:
        if has_target and self.target_templates is not None:
            templates = self.target_templates
        elif self.templates is not None:
            templates = self.templates
        else:
            raise ValueError(
                "Target not set and only target_templates are specified"
            )

        return TextGenerator(
            templates=templates,
            parts=self.parts,
            default_templates=default_templates,
            variables=variables,
        )


Parts = Mapping[str, Sequence[str | list[str | int] | tuple[str, int]]]


class TextGenerator:
    def __init__(
        self,
        templates: list[str],
        parts: Parts,
        default_templates: list[int] | None = None,
        variables: dict[str, str] | None = None,
    ) -> None:
        self.templates: list[str] = templates
        self.default_templates: list[int] | None = default_templates
        self.parts: Parts = parts
        self.variables: dict[str, str] | None = variables

    def get_part(self, required_part: str, part_list: Parts) -> str:
        _parts = part_list[required_part]
        _weighted_parts: list[tuple[str, int]] = []
        # this uses way too much code, but I wrote it at like 6am

        for _part in _parts:
            if isinstance(_part, (list, tuple)):
                __part, __weight = _part
                if not isinstance(__part, str) or not isinstance(__weight, int):
                    raise TypeError(
                        "Parts must be a string or a 2-element list or tuple with a string followed by an int"
                    )

                _weighted_parts.append((__part, __weight))
            else:
                __part = _part
                _weighted_parts.append((__part, 5))

        population = [val for val, cnt in _weighted_parts for _ in range(cnt)]
        return random.choice(population)

    def generate_string(self, template: int | None = None) -> str:
        """
        Generates one string using the specified templates.
        If no templates are specified, use a random template from the default_templates list.
        """
        if self.default_templates:
            text = self.templates[
                template or random.choice(self.default_templates)
            ]
        else:
            text = random.choice(self.templates)

        # make a copy of parts for this string generation
        _parts = {k: list(v) for k, v in copy.deepcopy(self.parts).items()}

        # get a list of all text parts we need
        required_parts: list[str] = TEMPLATE_RE.findall(text)

        # do magic
        for required_part in required_parts:
            # get the part
            try:
                replacement = self.get_part(required_part, _parts)
            except KeyError:
                continue

            # remove the used part
            for _part in _parts[required_part]:
                if isinstance(_part, (list, tuple)) and _part[0] == replacement:
                    _parts[required_part].remove(_part)
                elif _part == replacement:
                    _parts[required_part].remove(_part)

            text = text.replace(f"{{{required_part}}}", replacement, 1)

        # replace static variables in the template with provided values
        if self.variables:
            for key, value in list(self.variables.items()):
                text = text.replace(f"{{{key}}}", value)

        return text

    def generate_strings(self, amount: int) -> list[str]:
        return [self.generate_string() for _ in range(amount)]

    def get_template(self, template: int) -> str:
        return self.templates[template]
