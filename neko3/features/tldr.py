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
Wraps around TLDR Pages to provide an interface simpler than manpages.
"""
import aiohttp

import neko3.cog
from neko3 import embeds
from neko3 import neko_commands
from neko3 import pagination


def scrub_tags(text):
    return text


class TldrCog(neko3.cog.CogBase):
    @neko_commands.command(name="tldr", brief="Shows TLDR pages (like man, but simpler).")
    async def tldr_command(self, ctx, *, page: str):
        """
        Similar to man pages, this shows information on how to use a command,
        the difference being that this is designed to be human readable.

        Usage:

        - tldr gcc
        - tldr gcc

        If unspecified, we check all platforms. This will take a little longer
        to respond.
        """
        supported_platforms = ("common", "linux", "osx", "sunos", "windows")

        if any(x in page for x in "#?/"):
            return await ctx.send("Invalid page name.", delete_after=10)

        url = "https://raw.githubusercontent.com/tldr-pages/tldr/master/pages/"

        async with aiohttp.ClientSession() as session:
            for platform in supported_platforms:
                async with session.get(f"{url}{platform}/{page}.md") as resp:
                    content = await resp.text()
                    if 200 <= resp.status < 300:
                        break

                if resp.status != 200:
                    return await ctx.send(f"Error: {resp.reason}.", delete_after=10)

            content = "".join(content).splitlines()

        if not content:
            raise RuntimeError("No response from GitHub. Is the page empty?")
        elif len(content) == 1:
            raise RuntimeError("No body, only a title. Is the page empty?")

        # First line is title if it starts with '#'
        if content[0].startswith("#"):
            title = content.pop(0)[1:].lstrip() + f" ({platform})"
        else:
            title = f"{page} ({platform.title()})"

        paginator = pagination.Paginator()
        last_line_was_bullet = False

        for line in content:
            # Removes the blank line between bullets and code examples.
            if last_line_was_bullet and not line.lstrip().startswith("- "):
                if not line.strip():
                    last_line_was_bullet = False
                    continue
            elif line.lstrip().startswith(" "):
                last_line_was_bullet = True

            paginator.add_line(line)

        pages = []
        for page in paginator.pages:
            page = scrub_tags(page)

            if page.strip():
                pages.append(embeds.Embed(title=title, description=page))

        booklet = pagination.EmbedNavigator(ctx=ctx, pages=pages)
        await booklet.start()


def setup(bot):
    bot.add_cog(TldrCog(bot))
