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
Rextester cog interface.
"""
import neko3.cog
import neko3.converters
from neko3 import neko_commands
from neko3 import pagination
from . import utils
from .toolchains import rextester


class RextesterCog(neko3.cog.CogBase):
    @neko_commands.group(
        name="rextester",
        invoke_without_command=True,
        aliases=["rxt", "cc", "compile"],
        brief="Attempts to execute the code using [rextester.](http://rextester.com)",
    )
    async def rextester_group(self, ctx, *, source):
        """
        Attempts to execute some code by detecting the language in the
        syntax highlighting. You MUST format the code using markdown-formatted
        code blocks. Please, please, PLEASE read this before saying "it is
        broken!"

        This provides many more languages than coliru does, however, it is
        mainly untested and will probably break in a lot of places. It also
        has much less functionality. Many languages have to be formatted
        in a specific way or have specific variable names or namespaces.

        Run `cc help` to view a list of the supported languages, or
        `cc help <lang>` to view the help for a specific language.
        """
        code_block = utils.code_block_re.search(source)

        if not code_block or len(code_block.groups()) < 2:
            booklet = pagination.StringNavigatorFactory()
            booklet.add_line(
                "I couldn't detect a valid language in your "
                "syntax highlighting... try again by editing "
                "your initial message."
            )
            booklet = booklet.build(ctx)
            return await utils.start_and_listen_to_edit(ctx, booklet)

        # Extract the code
        language, source = code_block.groups()
        language = language.lower()

        if language not in rextester.Language.__members__:
            booklet = pagination.StringNavigatorFactory()
            booklet.add_line("Doesn't look like I support that language. " "Run `coliru help` for a list.")

            booklet = booklet.build(ctx)
            return await utils.start_and_listen_to_edit(ctx, booklet)

        booklet = pagination.StringNavigatorFactory(prefix="```markdown", suffix="```", max_lines=15)

        lang_no = rextester.Language.__members__[language]

        async with ctx.typing():
            response = await rextester.execute(lang_no, source)

        if response.errors:
            booklet.add_line("> ERRORS:")
            booklet.add_line(response.errors)

        if response.warnings:
            booklet.add_line("> WARNINGS:")
            booklet.add_line(response.warnings)

        if response.result:
            booklet.add_line("> OUTPUT:")
            booklet.add_line(response.result)

        booklet.add_line(f"Interpreted as {language.lower()} source; {response.stats}")

        if response.files:
            booklet.add_line(f"- {len(response.files)} file(s) included. Bug my dev to implement this properly!")

        booklet = booklet.build(ctx)
        await utils.start_and_listen_to_edit(ctx, booklet)

    @rextester_group.command(name="help", brief="Shows help for supported languages.")
    async def help_command(self, ctx, *, language: neko3.converters.clean_content = None):
        """
        Shows all supported languages and their markdown highlighting
        syntax expected to invoke them correctly.
        """
        if not language:
            booklet = pagination.StringNavigatorFactory(max_lines=20)
            booklet.add_line("**Supported languages**")

            for lang in sorted(rextester.Language.__members__.keys()):
                lang = lang.lower()
                booklet.add_line(f"- {lang.title()} -- `{ctx.prefix}rxt " f"ˋˋˋ{lang} ...`")
            booklet.start(ctx)
        else:
            await ctx.send("There is nothing here yet. The developer has been shot as a result.")
