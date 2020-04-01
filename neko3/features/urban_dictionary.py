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
Urban Dictionary support.
"""
import re
import urllib.parse as urlparse

import neko3.cog
from neko3 import neko_commands
from neko3 import pagination
from neko3 import string
from neko3 import theme

urban_random = "http://api.urbandictionary.com/v0/random"
urban_search = "http://api.urbandictionary.com/v0/define"


class UrbanDictionaryCog(neko3.cog.CogBase):
    """Urban dictionary cog."""

    link_regex = re.compile(r"\[(?P<phrase>[^\]]+?)\]")
    ud_link = r"[{0}](https://www.urbandictionary.com/define.php?{1})"
    no_brackets = r"\g<phrase>"

    def format_links(self, string, max_size):
        link_match = self.link_regex.findall(string)
        linked_str = string
        for match in link_match:
            url_safe_arg = urlparse.urlencode({"term": match})
            url = self.ud_link.format(match, url_safe_arg)
            linked_str = linked_str.replace(f"[{match}]", url)

        if len(linked_str) > max_size:
            return self.link_regex.sub(self.no_brackets, string)

        return linked_str

    def format_urban_definition(self, ctx, definition: dict):
        """
        Takes an UrbanDictionary word response and formats an embed
        to represent the output, before returning it.
        """

        # Adds ellipses to the end and truncates if a string is too long.
        def dots(string, limit=1024):
            return string if len(string) < limit else string[: limit - 3] + "..."

        title = definition["word"].title()
        defn = dots(definition["definition"], 2000)

        # Remove embedded URLS to stop Discord following them.
        defn = defn.replace("https://", "").replace("http://", "")
        # [] signify phrases linking to elsewhere.
        defn = self.format_links(defn, 2000)

        # Sanitise backticks and place in a code block if applicable.
        example = dots(definition["example"].replace("`", "’"))
        if example:
            example = self.format_links(example, 1024)
            example = dots(example, 1024)

        author = definition["author"]
        yes = definition["thumbs_up"]
        no = definition["thumbs_down"]
        permalink = definition["permalink"]

        embed = theme.generic_embed(
            ctx=ctx,
            title=f"{title} -- {author} (\N{THUMBS UP SIGN} {yes} \N{THUMBS DOWN SIGN} {no})",
            description=string.trunc(defn),
            colour=0xFFFF00,
            url=permalink,
        )

        if example:
            embed.add_field(name="Example", value=example)

        if "tags" in definition and definition["tags"]:
            tags = ", ".join(sorted({*definition["tags"]}))
            embed.set_footer(text=string.trunc(tags))
        return embed

    @neko_commands.command(
        name="urban",
        brief="Looks up a definition on Urban Dictionary.",
        examples=["java", ""],
        aliases=["ud", "udd", "urband", "urbandictionary"],
    )
    async def urban_dictionary_command(self, ctx: neko_commands.Context, *, phrase: str = None):
        """If no phrase is given, we pick some random ones to show."""

        async with self.acquire_http_session() as session:
            with ctx.typing():
                # Get the response
                if phrase:
                    params = {"term": phrase}
                    url = urban_search
                else:
                    params = {}
                    url = urban_random 

                async with session.get(url, params=params) as resp:
                    resp.raise_for_status()
                    # Decode the JSON.
                    resp = (await resp.json())["list"]

        if len(resp) == 0:
            return await ctx.send("No results. You sure that is a thing?", delete_after=15)

        embeds = [self.format_urban_definition(ctx, word) for word in resp]

        # If we have more than one result, make a FSM from the pages.
        if ctx.invoked_with in ("udd", "urband"):
            await neko_commands.try_delete(ctx)

        pagination.EmbedNavigator(ctx=ctx, pages=embeds).start()


def setup(bot):
    bot.add_cog(UrbanDictionaryCog(bot))
