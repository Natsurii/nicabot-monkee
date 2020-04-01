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
Cog providing Coliru commands.
"""
import io

import neko3.cog
import neko3.converters
from neko3 import neko_commands
from neko3 import pagination
from . import utils
from .toolchains import coliru


class ColiruCog(neko3.cog.CogBase):
    @neko_commands.group(
        invoke_without_command=True,
        name="coliru",
        brief="Attempts to execute the given code using " "[coliru](http://coliru.stacked-crooked.com).",
    )
    async def coliru_group(self, ctx, *, code):
        """
        Attempts to execute some code by detecting the language in the
        syntax highlighting. You MUST format the code using markdown-formatted
        code blocks. Please, please, PLEASE read this before saying "it is
        broken!"

        Run `coliru help` to view a list of the supported languages, or
        `coliru help <lang>` to view the help for a specific language.

        If you want to upload more than one file, or you wish to specify a
        custom build routine or flags, see `coliru a`.
        """

        code = utils.code_block_re.search(code)

        if not code or len(code.groups()) < 2:
            booklet = pagination.StringNavigatorFactory()
            booklet.add_line(
                "I couldn't detect a valid language in your "
                "syntax highlighting... try again by editing "
                "your initial message."
            )

            booklet = booklet.build(ctx)

            return await utils.start_and_listen_to_edit(ctx, booklet)

        # Extract the code
        language, source = code.groups()
        language = language.lower()

        try:
            with ctx.typing():
                output = await coliru.targets[language](source)
        except KeyError:
            booklet = pagination.StringNavigatorFactory()
            booklet.add_line(
                f"That language ({language}) is not yet supported"
                " by this toolchain. Feel free to edit your"
                " message if you wish to do something else."
            )
            booklet = booklet.build(ctx)

            return await utils.start_and_listen_to_edit(ctx, booklet)

        else:
            booklet = pagination.StringNavigatorFactory(prefix="```markdown", suffix="```", max_lines=25)

            booklet.add_line(f"Interpreting as {language!r} source.")

            for line in output.split("\n"):
                booklet.add_line(line)

            if ctx.invoked_with in ("ccd", "colirud"):
                await neko_commands.try_delete(ctx)

            if len(output.strip()) == 0:
                await ctx.send("No output...")
                return

            booklet = booklet.build(ctx)

            return await utils.start_and_listen_to_edit(ctx, booklet)

    @coliru_group.command(name="help", brief="Shows help for supported languages.")
    async def help_command(self, ctx, *, language: neko3.converters.clean_content = None):
        """
        Shows all supported languages and their markdown highlighting
        syntax expected to invoke them correctly.
        """
        if not language:
            output = "**Supported languages**\n"
            for lang in sorted(coliru.languages):
                output += f"- {lang.title()} -- `{ctx.prefix}cc " f"ˋˋˋ{coliru.languages[lang.lower()][0]} " f"...`\n"
            await ctx.send(output)
        else:
            try:
                lang = language.lower()

                help_text = coliru.docs[language]
                help_text += "\n\n"
                help_text += "Invoke using syntax highlighted code blocks with " "one of the following names:\n"
                help_text += ", ".join(f"`{x}`" for x in coliru.languages[lang])

                await ctx.send(help_text)
            except KeyError:
                await ctx.send(f"Could not find anything for `{language}`")

    @coliru_group.command(
        name="advanced",
        brief="Allows fine-tuned customisation of how a job is " "run, at the loss of some of the simplicity.",
        usage="ˋbash commandˋ [ˋfile_nameˋ ˋˋˋcodeˋˋˋ]*",
    )
    async def advanced_command(self, ctx, *, code):
        """
        This tool enables you to specify more than one file, in any supported
        language on Coliru. It also lets you upload source code files.

        Advanced code execution will first pool all source files into the
        current working directory in the sandbox. It will then proceed to
        execute the build/run command: this is the first argument, and should
        be enclosed in single back-ticks. The execute command can be something
        as simple as `make`, or as complicated as you like. You must invoke
        all of your logic you wish to perform from this argument, however.

        It is worth noting that this build script WILL be executed as Bash
        commands.

        For small programs, it may be as simple as invoking the interpreter
        or compiler, and then running the output. However, if you have much
        more complicated input, it is advisable to invoke something like a
        Makefile and call your logic from that.
        """

        try:
            # Get the first block as the command.
            command = utils.inline_block_re.search(code)

            if not command:
                raise ValueError("No command was given.")

            command = command.groups()[0]

            rest = code[len(command) :].lstrip()

            # Get files:
            files = []
            for m in utils.file_name_and_block_re.findall(rest):
                files.append(m)

            for attachment in ctx.message.attachments:
                with io.StringIO() as buff:
                    attachment.save(buff)
                    buff = buff.getvalue()

                files.append((attachment.filename, buff))

            if len(files) == 0:
                raise ValueError("Expected one or more source files.")

            # Map to sourcefile objects
            files = [coliru.SourceFile(*file) for file in files]

            # Main file
            main = coliru.SourceFile(".run.sh", command)

            # Generate the coliru API client instance.
            c = coliru.Coliru("bash .run.sh", main, *files, verbose=True)

            async with self.acquire_http_session() as http:
                output = await c.execute(http)

            booklet = pagination.StringNavigatorFactory(prefix="```markdown", suffix="```", max_lines=25)

            for line in output.split("\n"):
                booklet.add_line(line)

            if ctx.invoked_with in ("ccd", "colirud"):
                await neko_commands.try_delete(ctx)

            if len(output.strip()) == 0:
                await ctx.send("No output...")
                return

            booklet = booklet.build(ctx)

            return await utils.start_and_listen_to_edit(ctx, booklet)

        except IndexError:
            return await ctx.send("Invalid input format.")
        except ValueError as ex:
            return await ctx.send(str(ex))
