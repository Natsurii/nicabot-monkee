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
Gets information on various Python modules.
"""
import contextlib
import io
import xmlrpc.client as xmlrpcclient
from urllib import parse

from discord.ext import commands

import neko3.cog
from neko3 import algorithms
from neko3 import neko_commands
from neko3 import pagination
from neko3 import string
from neko3 import theme


class PyCog(neko3.cog.CogBase):
    @neko_commands.command(name="py", aliases=["python"], brief="Shows Python documentation.")
    async def py_command(self, ctx, member):
        """Gets some help regarding the given Python member, if it exists..."""

        with io.StringIO() as buff:
            with contextlib.redirect_stdout(buff):
                with contextlib.redirect_stderr(buff):
                    help(member)
            data = buff.getvalue().splitlines()

        bb = pagination.StringNavigatorFactory(max_lines=20, prefix="```markdown", suffix="```")

        for line in data:
            line = line.replace("`", "′")
            bb.add_line(line)

        bb.start(ctx)

    @neko_commands.group(
        name="pypi",
        invoke_without_command=True,
        aliases=["pip", "pip3"],
        brief="Searches PyPI for the given package name.",
    )
    async def pypi_group(self, ctx, package: commands.clean_content):
        """
        Input must be two or more characters wide.
        """
        if len(package) < 2:
            return await ctx.send("Please provide at least two characters.", delete_after=10)

        def executor(*_, **__):
            # https://wiki.python.org/moin/PyPIXmlRpc
            # This is deprecated. Who cares?
            client = xmlrpcclient.ServerProxy("https://pypi.python.org/pypi")
            return client.search({"name": package})

        try:
            with ctx.typing():
                results = await self.run_in_thread_pool(executor)

            if len(results) == 0:
                raise IndexError

            book = pagination.EmbedNavigatorFactory(max_lines=None)

            head = f"**__Search results for `{package}`__**\nRun `n.pypi i {{package}}` for full details on a package\n"
            for i, result in enumerate(results[:50]):
                if not i % 5:
                    book.add_page_break()
                    book.add_line(head)

                name = result["name"]
                link = f"https://pypi.org/project/{parse.quote(name)}"
                ver = result["version"]
                summary = result["summary"]
                summary = summary and f"_{summary}_" or ""
                NL = "\n"
                book.add_line(f"**[{name}]({link})\N{EM SPACE}v{ver}**\n{summary}{NL if summary else ''}")

            booklet = book.build(ctx)
            if len(booklet) > 1:
                booklet.start()
            else:
                await self.info_command.callback(self, ctx, package)
        except IndexError:
            await ctx.send("No results were found...", delete_after=10)

    @pypi_group.command(name="info", brief="Shows info for a specific PyPI package.", aliases=["i", "in"])
    async def info_command(self, ctx, package: commands.clean_content):
        """
        Shows a summary for the given package name on PyPI, if there is one.
        """
        url = f"https://pypi.org/pypi/{parse.quote(package)}/json"

        # Seems like aiohttp is screwed up and will not parse these URLS.
        # Requests is fine though. Guess I have to use that...
        with ctx.typing():
            async with self.acquire_http_session() as http:
                async with http.get(url=url) as resp:
                    result = (await resp.json()) if 200 <= resp.status < 300 else None

        if result:
            data = result["info"]

            name = f'{data["name"]} v{data["version"]}'
            url = data["package_url"]
            summary = data.get("summary", "_No summary was provided_")
            author = data.get("author")
            serial = result.get("last_serial", "No serial")
            if isinstance(serial, int):
                serial = f"Serial #{serial}"

            # Shortens the classifier strings.
            classifiers = data.get("classifiers", [])
            if classifiers:
                fixed_classifiers = []
                for classifier in classifiers:
                    print()
                    if "::" in classifier:
                        _, _, classifier = classifier.rpartition("::")
                    classifier = f"`{classifier.strip()}`"
                    fixed_classifiers.append(classifier)
                classifiers = ", ".join(sorted(fixed_classifiers))

            other_attrs = {
                "License": data.get("license"),
                "Platform": data.get("platform"),
                "Homepage": data.get("home_page"),
                "Requires Python version": data.get("requires_python"),
                "Classifiers": classifiers,
            }

            embed = theme.generic_embed(
                ctx, title=name, description=string.trunc(summary, 2048), url=url, colour=algorithms.rand_colour()
            )

            if author:
                embed.set_author(name=f"{author}")
            embed.set_footer(text=f"{serial}")

            for attr, value in other_attrs.items():
                if not value:
                    continue

                embed.add_field(name=attr, value=value)

            await ctx.send(embed=embed)

        else:
            await ctx.send(f"PyPI said: {resp.reason}", delete_after=10)


def setup(bot):
    bot.add_cog(PyCog(bot))
