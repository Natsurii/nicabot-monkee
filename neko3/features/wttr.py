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
Gets the weather in ASCII.
"""
import asyncio
import urllib.parse as urlparse

import bs4
from discord.ext import commands

import neko3.cog
from neko3 import neko_commands


def url_factory(query):
    quoted = urlparse.quote(query)
    return f"http://wttr.in/{quoted}?T2nq"


class WttrCog(neko3.cog.CogBase):
    @commands.cooldown(1, 30.0, commands.BucketType.channel)
    @neko_commands.command(name="weather", aliases=["wttr"], brief="Check the weather.")
    async def weather_command(self, ctx, *, query="London"):
        """
        Get the weather for a given location, or London by default.
        """
        query = query[:30]

        async with ctx.typing():
            async with self.acquire_http_session() as session:
                async with session.get(url_factory(query)) as resp:
                    resp.raise_for_status()
                    soup = bs4.BeautifulSoup(await resp.text(), features="html.parser")
                    data = soup.find(name="body").find("pre").text

        m = await ctx.send(f"```scala\n{data}\n```\n")

        async def closable():
            emoji = "\N{SQUARED OK}"
            try:

                def predicate(r, u):
                    return r.message.id == m.id and r.emoji == emoji and u == ctx.author

                await m.add_reaction(emoji)
                await ctx.bot.wait_for("reaction_add", check=predicate, timeout=180)

                # If we reach here, the reaction was hit.
                await m.delete()
                await ctx.message.delete()
            except asyncio.TimeoutError:
                try:
                    await m.remove_reaction(emoji, ctx.bot.user)
                except Exception:
                    self.logger.warning("Could not remove reaction")
            except Exception:
                self.logger.exception("Error waiting for reaction add")

        ctx.bot.loop.create_task(closable())


def setup(bot):
    bot.add_cog(WttrCog(bot))
