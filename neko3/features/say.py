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
Repeats what you say. Simple, right?
"""
import neko3.converters
from neko3 import logging_utils
from neko3 import neko_commands


class SayCog(neko_commands.Cog, logging_utils.Loggable):
    @neko_commands.command(name="say", brief="Take a wild guess.")
    async def say_command(self, ctx, *, message: neko3.converters.clean_content):
        try:
            self.logger.info("%s made me say %r in %s#%s", ctx.author, message, ctx.guild, ctx.channel)
            await ctx.message.delete()
            await ctx.send(message)
        finally:
            return


def setup(bot):
    bot.add_cog(SayCog())
