#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Nekozilla is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Nekozilla is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Nekozilla.  If not, see <https://www.gnu.org/licenses/>.


"""
Previews embeds using either YAML or JSON.

Shoutout to @zOmbie1919nl#1919 for the idea <3
"""
import json
import re

import yaml

from neko3 import cog
from neko3 import neko_commands

code_block = re.compile(r"^```(\w+)\s*([\w\W]*)```$")

parser_map = {"json": json.loads, "yaml": lambda s: yaml.load(s, Loader=yaml.SafeLoader)}


class EmbedFacade(dict):
    """Special facade that allows a dict to be used as if it were an embed."""

    def to_dict(self):
        return self


class EmbedPreviewer(cog.CogBase):
    @neko_commands.command(name="embed", brief="Preview an embed")
    async def embed_command(self, ctx, *, code):
        """
        Takes a JSON string or an equivalent YAML string that corresponds to the
        structure described in the Discord developer documentation for Embeds.
        
        See https://discordapp.com/developers/docs/resources/channel#embed-object
        """
        try:
            matcher = code_block.match(code)
            if not matcher:
                raise SyntaxError("Please use either `yaml` or `json` as your syntax highlighting of choice.")

            lang, content = matcher.group(1), matcher.group(2)

            parser = parser_map[lang]

            data = parser(content)

            if "color" in data and isinstance(data["color"], str):
                try:
                    data["color"] = int(data["color"], 10)
                except ValueError:
                    data["color"] = int(data["color"], 16)

            raw_embed = EmbedFacade(data)
            await ctx.send(embed=raw_embed)
        except Exception as ex:
            error = f"{type(ex).__name__}: {ex}"
            await ctx.send(error[:2000])


def setup(bot):
    bot.add_cog(EmbedPreviewer(bot))
