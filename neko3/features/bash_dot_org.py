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
Gets a random quote from bash.org
"""
import random

import aiohttp
import bs4

import neko3.cog
from neko3 import neko_commands
from neko3 import pagination
from neko3 import theme


async def get_random_quote():
    async with aiohttp.ClientSession() as session:
        async with session.get("http://bash.org/?random1") as resp:
            resp.raise_for_status()
            raw = await resp.text()

    soup = bs4.BeautifulSoup(raw, features="html.parser")
    quotes = soup.find_all(attrs={"class": "qt"})
    quote = random.choice(quotes)
    return quote.text.replace('`', '\N{MODIFIER LETTER GRAVE ACCENT}')


class BashDotOrgCog(neko3.cog.CogBase):
    @neko_commands.command(name="bash", brief="Gets a quote from bash.org")
    async def bash_command(self, ctx):
        async with ctx.typing():
            quote = await get_random_quote()

        @pagination.embed_generator(max_chars=2048)
        def embed_generator(pag, page, index):
            return theme.generic_embed(ctx, title="Random bash.org quote", description=page, url="http://bash.org")

        pag = pagination.EmbedNavigatorFactory(max_lines=10, factory=embed_generator)
        for line in quote.split("\n"):
            pag.add_line(line)
        pag.start(ctx)


def setup(bot):
    bot.add_cog(BashDotOrgCog(bot))
