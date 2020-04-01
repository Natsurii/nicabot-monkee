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
Lets the user run `!!` to reinvoke the previous command.
"""
from discord.ext import commands

from neko3 import neko_commands


class BangBangCog(neko_commands.Cog):
    def __init__(self):
        self.user2context = {}
        super().__init__()

    @neko_commands.Cog.listener()
    async def on_command(self, ctx):
        """Cache the last-executed commands."""
        if ctx.command != self.reinvoke_command:
            self.user2context[ctx.author] = ctx

    @commands.cooldown(3, 10, commands.BucketType.user)
    @commands.check(lambda ctx: not ctx.author.bot)
    @neko_commands.command(name="!!", brief="Reinvoke the last command.")
    async def reinvoke_command(self, ctx: neko_commands.Context):
        if ctx.author not in self.user2context:
            await ctx.send("No command history. Perhaps the bot restarted?", delete_after=10)
        else:
            await self.user2context[ctx.author].reinvoke(call_hooks=True)


def setup(bot):
    bot.add_cog(BangBangCog())
