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
Commit logs from Last Night
"""
import datetime
import random

import aiohttp
import bs4

import neko3.cog
from neko3 import neko_commands
from neko3 import theme


class CommitLogsFromLastNightCog(neko3.cog.CogBase):
    @neko_commands.command(name="commit", aliases=["clfln"], brief="Gets a random commit log from last night.")
    async def commit_command(self, ctx):
        async with ctx.typing():
            async with aiohttp.ClientSession() as session:
                async with session.get("http://www.commitlogsfromlastnight.com/") as resp:
                    resp.raise_for_status()
                    data = await resp.text()

            soup = bs4.BeautifulSoup(data, features="html5lib")

            posts: bs4.Tag = soup.find("tbody").find_all("tr")
            post: bs4.Tag = random.choice(list(posts))

            committer = post.find(attrs={"class": "commiter"}).text
            avatar_link = post.find(attrs={"class": "avatarlink"})["href"]
            avatar = post.find(attrs={"class": "avatar"})["src"]

            date = post.find(attrs={"class": "date"}).text
            date = datetime.datetime.strptime(date, "%d/%m/%y %I:%M %p")

            commit = post.find(attrs={"class": "commit"})
            message = commit.text
            link = commit["href"]

        embed = theme.generic_embed(
            ctx, title="Commit Logs From Last Night", description=message, url=link, timestamp=date
        )
        embed.set_author(name=committer, url=avatar_link)
        embed.set_thumbnail(url=avatar)
        embed.set_footer(text="because real hackers pivot two hours before their demo")

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(CommitLogsFromLastNightCog(bot))
