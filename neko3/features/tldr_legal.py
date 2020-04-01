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
Uses webscraping to search tldrlegal for human-readable information on
software licenses, et cetera.
"""
import asyncio
from dataclasses import dataclass
from typing import List
from typing import Tuple

import aiohttp
import bs4

import neko3.cog
from neko3 import algorithms
from neko3 import embeds
from neko3 import neko_commands
from neko3 import pagination
from neko3 import string

base_url = "https://tldrlegal.com/"


@dataclass()
class License:
    name: str
    brief: str
    can: List[Tuple[str, str]]
    cant: List[Tuple[str, str]]
    must: List[Tuple[str, str]]
    url: str


class TldrLegalCog(neko3.cog.CogBase):
    @staticmethod
    def get_results_from_html(html: str) -> List[Tuple[str, str]]:
        """
        Parses the given HTML as search results for TLDR legal, returning
        a list of tuples for each result: each tuple has the name and URL.
        """
        soup = bs4.BeautifulSoup(html, features="html.parser")

        results = soup.find_all(attrs={"class": "search-result flatbox"})

        pages = []

        for result in results:
            link: bs4.Tag = result.find(name="a")
            url = f'{base_url}{link["href"]}'
            name = link.text
            pages.append((name, url))

        return pages

    @staticmethod
    def get_license_info(url: str, html: str) -> License:
        """
        Parses a license info page to get the info regarding said license as an
        object.
        """
        soup = bs4.BeautifulSoup(html, features="html.parser")

        name = soup.find(name="h1", attrs={"class": "page-title"}).text
        summary = soup.find(name="div", attrs={"class": "summary-content"})

        if not summary:
            raise ValueError("No quick summary is available.")

        summary = summary.text.strip()

        # Get the results license-root div.
        results = soup.find(name="div", attrs={"id": "license_root"})

        can_tag = results.find(name="ul", attrs={"class": "bucket-list green"})
        cant_tag = results.find(name="ul", attrs={"class": "bucket-list red"})
        must_tag = results.find(name="ul", attrs={"class": "bucket-list blue"})

        def remove_title_li(tag: bs4.Tag):
            # Pop the title
            tag.find(name="li", attrs={"class": "list-header"}).extract()

        remove_title_li(can_tag)
        remove_title_li(cant_tag)
        remove_title_li(must_tag)

        def get_head_body_pairs(tag: bs4.Tag):
            return (tag.find(attrs={"class": "attr-head"}).text, tag.find(attrs={"class": "attr-body"}).text)

        can = [get_head_body_pairs(li) for li in can_tag.find_all(name="li")]
        cant = [get_head_body_pairs(li) for li in cant_tag.find_all(name="li")]
        must = [get_head_body_pairs(li) for li in must_tag.find_all(name="li")]

        return License(name, summary, can, cant, must, url)

    @neko_commands.group(
        name="tldrlegal",
        brief="Search for license info on tldrlegal.",
        aliases=["legal", "license", "licence"],
        invoke_without_command=True,
    )
    async def tldr_legal_group(self, ctx, *, search):
        await self.tldr_legal_logic(ctx, search, False)

    @tldr_legal_group.command(
        name="more", brief="Search for a license on tldrlegal, and give " "more information in the results."
    )
    async def more_command(self, ctx, *, search):
        await self.tldr_legal_logic(ctx, search, True)

    async def tldr_legal_logic(self, ctx, query, verbose):
        """
        Helper to prevent code duplication.
        """
        async with aiohttp.ClientSession() as session:

            # Get search results
            async with session.get(f"{base_url}search", params={"q": query}) as resp:
                if resp.status != 200:
                    return await ctx.send(f"tldrlegal said {resp.reason!r}")

                results = self.get_results_from_html(await resp.text())

            count = len(results)

            if count == 0:
                return await ctx.send("Nothing was found.", delete_after=15)
            elif count == 1:
                # Get the URL
                page = results[0]
            else:
                string_results = [o[0].replace("*", "∗") for o in results]

                try:
                    page = await pagination.option_picker(*string_results, ctx=ctx)

                    if page == pagination.NoOptionPicked():
                        return
                    else:
                        # Reverse index.
                        page = results[string_results.index(page)]
                except asyncio.TimeoutError:
                    return await ctx.send("Took too long...")

            # Get the info into an object.

            try:
                async with session.get(page[1]) as resp:
                    if resp.status != 200:
                        return await ctx.send(f"tldrlegal said {resp.reason!r}")
                    license_info = self.get_license_info(page[1], await resp.text())
            except ValueError as ex:
                return await ctx.send(ex)

        # Generate embed and send.
        embed = embeds.Embed(
            title=license_info.name,
            description=string.trunc(license_info.brief),
            colour=algorithms.rand_colour(),
            url=license_info.url,
        )
        embed.set_footer(
            text="Disclaimer: This is only a short summary of the"
            " Full Text. No information on TLDRLegal is"
            " legal advice."
        )

        def fmt(prs):
            if verbose:
                s = string.trunc("\n".join(f"**{n}** {d}" for n, d in prs), 1024)
            else:
                s = string.trunc("\n".join(f"- {n}" for n, _ in prs), 1024)

            # Prevents errors for empty bodies.
            return s or "—"

        embed.add_field(name="__CAN__", value=fmt(license_info.can), inline=not verbose)
        embed.add_field(name="__CANNOT__", value=fmt(license_info.cant), inline=not verbose)
        embed.add_field(name="__MUST__", value=fmt(license_info.must), inline=not verbose)

        if not verbose:
            embed.add_field(
                name="\u200b", value="_Run again using `tldrlegal more <query>` " "to get a longer explanation!_"
            )

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(TldrLegalCog(bot))
