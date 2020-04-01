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
C and C++ utilities.
"""
import asyncio
import re  # Regex
import typing  # Type checking

import bs4  # HTML parser

import neko3.cog
from neko3 import errors, algorithms
from neko3 import neko_commands
from neko3 import pagination

# CppReference stuff
result_path = re.compile(r"^/w/c(pp)?/", re.I)


class SearchResult:
    def __init__(self, text, href):
        self.text = text
        self.href = href

    def __str__(self):
        return f"`{self.text}`"


# 25th Apr 2018: Certificate issues on HTTPS, so using
# HTTP instead.
base_cppr = "http://en.cppreference.com"
base_cppr_https = "https://en.cppreference.com"
search_cppr = base_cppr_https + "/mwiki/index.php"


class CppCog(neko3.cog.CogBase):
    async def results(self, ctx, *terms):
        """Gathers the results for the given search terms from Cppreference."""
        params = {"search": "|".join(terms)}

        async with self.acquire_http_session() as conn:
            with algorithms.TimeIt() as timer:
                async with conn.get(search_cppr, params=params) as resp:
                    self.logger.info("GET %s", resp.url)
                    if resp.status != 200:
                        raise errors.HttpError(resp)

                    url = str(resp.url)
                    if url.startswith(base_cppr_https):
                        href = url[len(base_cppr_https) :]
                    else:
                        href = url[len(base_cppr) :]

                    resp = await resp.text()

        await ctx.send(f"Response from server took {timer.time_taken * 1_000:,.2f}ms", delete_after=3)

        # Parse the HTML response.
        tree = bs4.BeautifulSoup(resp, features="html.parser")

        self.logger.info(href)

        if href.startswith("/w/"):
            # Assume we are redirected to the first result page
            # only.
            title = tree.find(name="h1")
            title = title.title if title else resp.url
            return [SearchResult(title, href)]

        self.logger.info("coalescing search results")

        search_result_lists: typing.List[bs4.Tag] = tree.find_all(
            name="div", attrs={"class": "mw-search-result-heading"}
        )

        # Discard anything in search results without an inner link
        search_results = []
        for i, sr_list in enumerate(search_result_lists, start=1):
            self.logger.info("reading sublist %s", i)
            results: typing.List[bs4.Tag] = sr_list.find_all(
                name="a", attrs={"href": result_path, "title": lambda t: t}
            )

            search_results.extend(results)

        c = []
        cpp = []
        other = []

        for link in search_results:
            href = link["href"]
            name = link.text
            if href.startswith("/w/c/"):
                # A C library link
                name = f"[C] {name}"
                self.logger.info("Found C result %s %s", name, href)
                c.append(SearchResult(name, href))

            elif href.startswith("/w/cpp/"):
                # This is a C++ library link.
                name = f"[C++] {name}"
                self.logger.info("Found C++ result %s %s", name, href)
                cpp.append(SearchResult(name, href))
            else:
                # This is an "other" link.
                name = f"[Other] {name}"
                self.logger.info("Found other result %s %s", name, href)
                other.append(SearchResult(name, href))

        return [*c, *cpp, *other]

    async def get_information(self, ctx, href):
        """
        Gets information for the given search result.
        """
        url = base_cppr + href

        async with self.acquire_http_session() as conn:
            with algorithms.TimeIt() as timer:
                async with conn.get(url) as resp:
                    self.logger.info("GET %s", url)
                    resp.raise_for_status()

                    # Make soup.
                    bs = bs4.BeautifulSoup(await resp.text(), features="html.parser")

        await ctx.send(f"Response from server took {timer.time_taken * 1_000:,.2f}ms", delete_after=3)

        header = bs.find(name="tr", attrs={"class": "t-dsc-header"})
        if header:
            header = header.text
        else:
            header = ""

        taster_tbl: bs4.Tag = bs.find(name="table", attrs={"class": "t-dcl-begin"})

        if taster_tbl:
            tasters = taster_tbl.find_all(name="span", attrs={"class": lambda c: c is not None and "mw-geshi" in c})

            if tasters:
                # Fixes some formatting
                for i, taster in enumerate(tasters):
                    taster = taster.text.split("\n")
                    taster = "\n".join(t.rstrip() for t in taster)
                    taster = taster.replace("\n\n", "\n")
                    tasters[i] = taster

            # Remove tasters from DOM
            taster_tbl.replace_with(bs4.Tag(name="empty"))
        else:
            tasters = []

        h1 = bs.find(name="h1").text

        # Get the description
        desc = bs.find(name="div", attrs={"id": "mw-content-text"})

        if desc:
            # first_par_node = desc.find(name='p')
            # description = first_par_node.text + '\n'
            # sibs = first_par_node.find_next_siblings()
            # for sib in sibs:
            #    description += sib.text + '\n'
            description = "\n".join(
                p.text
                for p in desc.find_all(name="p")
                if not p.text.strip().endswith(":")
                and not p.text.strip().startswith("(")
                and not p.text.strip().endswith(")")
            )
        else:
            description = ""

        return url, h1, tasters, header, description

    @neko_commands.command(
        name="cppref",
        brief="Searches en.cppreference.com for the given criteria.",
        aliases=["cref", "cpp"],
        examples=["std::string", "stringstream"],
    )
    async def cpp_reference_command(self, ctx, *terms):

        self.logger.info("Searching for terms %s", terms)
        try:
            async with ctx.typing():
                results = await self.results(ctx, *terms)
        except Exception as ex:
            self.logger.exception("search error", exc_info=ex)
            return await ctx.send(
                "CppReference did something unexpected. If this keeps "
                "happening, contact Esp with the following info: \n\n"
                f"{type(ex).__qualname__}: {ex!s}"
            )

        if not results:
            self.logger.info("no results")
            return await ctx.send("No results were found.", delete_after=10)

        if len(results) > 1:
            # Show an option picker
            try:
                self.logger.info("waiting for input")
                result = await pagination.option_picker(*results, ctx=ctx, max_lines=20)
            except asyncio.TimeoutError:
                return

            if result == pagination.NoOptionPicked():
                self.logger.info("no option picked")
                return
        else:
            result = results[0]

        # Fetch the result page.

        async with ctx.typing():
            try:
                self.logger.info("searching for info from %s", result.href)
                url, h1, tasters, header, desc = await self.get_information(ctx, result.href)
            except Exception as ex:
                self.logger.exception("An exception occurred", exc_info=ex)
                return await ctx.send("An error was encountered and a duck was shot.")

            binder = pagination.StringNavigatorFactory(max_lines=50)

            binder.disable_truncation()
            binder.add_line(f"**{h1}**\n<{url}>")
            if header:
                binder.add_line(f"\n`{header}`")

            if tasters:
                for taster in tasters:
                    binder.add_line(f"```cpp\n{taster}\n```")
            binder.enable_truncation()

            if desc:
                binder.add_line(desc.replace("*", "∗"))

        binder.start(ctx)


def setup(bot):
    bot.add_cog(CppCog(bot))
