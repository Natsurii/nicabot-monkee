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
RTFM...kinda
"""
import inspect

import neko3.converters
from neko3 import logging_utils
from neko3 import neko_commands
from neko3 import pagination


class SourceCog(neko_commands.Cog, logging_utils.Loggable):
    @neko_commands.command(name="source", brief="Show the source for something in this bot")
    async def source_command(self, ctx, *, command):
        """Get the source code for a certain command, cog, or extension..."""
        try:
            try:
                command_obj = await neko3.converters.CommandConverter().convert(ctx, command)
                code = inspect.getsource(command_obj.callback)
                object_type = "command"
            except Exception:
                try:
                    code = inspect.getsource(type(ctx.bot.cogs[command]))
                    object_type = "cog"
                except Exception:
                    code = inspect.getsource(ctx.bot.extensions[command])
                    object_type = "extension"

            p = pagination.StringNavigatorFactory(
                prefix="```", suffix="```", max_lines=22, substitutions=[lambda s: s.replace("`", "′")]
            )
            p.add_line(f"# -*-*- Source for {command} {object_type}  -*-*-")

            p.disable_truncation()

            for line in code.split("\n"):
                p.add_line(line)

            p.start(ctx)
        except Exception:
            self.logger.exception("Failed to load source.")
            await ctx.send("No source was found...")


def setup(bot):
    bot.add_cog(SourceCog())
