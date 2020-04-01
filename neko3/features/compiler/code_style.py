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
A few utils to fixing code input and validating it.
"""
import asyncio
import os
import shutil
import tempfile
import textwrap
import time

import neko3.cog
from neko3 import neko_commands
from neko3 import pagination
from . import utils


class CodeStyleCog(neko3.cog.CogBase):
    @neko_commands.group(invoke_without_command=True)
    async def fix(self, ctx, *, code=None):
        """
        Provides several options for reformatting Python source code for
        several specific style guides.

        - [PEP8](https://www.python.org/dev/peps/pep-0008/) `fix pep8`
        - [black code style](https://github.com/ambv/black) `fix black`
        - [Google Python style](https://github.com/google/styleguide) `fix google`
        - [Chromium Python style](https://www.chromium.org/chromium-os/python-style-guidelines) `fix chromium`
        - Facebook Python style - this is an alterred PEP8, as provided by YAPF.

        These tools rely on the `black`, `pep8ify`, and Google's `yapf` Python
        packages.

        Additionally, I have provided a `md` command that provides simple fixing
        of nested code blocks, since Discord loves to break those.
        """
        if code is None:
            await neko_commands.send_usage(ctx)
        else:
            await self.black.callback(self, ctx, code=code)

    async def run_black(self, mid, code):
        """Runs black, outputs the resulting code and logs in a tuple.."""
        name = f"{mid}{time.perf_counter() * 1000:.0f}.py"

        # noinspection PyProtectedMember
        f = os.path.join(tempfile._candidate_tempdir_list()[0], name)

        await self.run_in_thread_pool(shutil.rmtree, [f], {"ignore_errors": True})

        async with self.async_open(f, "w") as fp:
            await fp.write(code)

        args = [f, "--py36", "--line-length", "80"]

        p = await asyncio.create_subprocess_exec(
            "black", *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
        )
        stdout, _ = await p.communicate()

        async with self.async_open(f, "r") as fp:
            code = await fp.read()

        await self.run_in_thread_pool(shutil.rmtree, [f], {"ignore_errors": True})

        return code, stdout.decode()

    async def run_pep8ify(self, mid, code):
        """Runs PEP8ify, outputs the resulting code and logs in a tuple.."""
        name = f"{mid}{time.perf_counter() * 1000:.0f}.py"

        # noinspection PyProtectedMember
        f = os.path.join(tempfile._candidate_tempdir_list()[0], name)

        await self.run_in_thread_pool(shutil.rmtree, [f], {"ignore_errors": True})

        async with self.async_open(f, "w") as fp:
            await fp.write(code)

        args = ["--print-function", "--list-fixes", "-f", "all", "-f", "maximum_line_length", "-n", "-w", f]

        p = await asyncio.create_subprocess_exec(
            "pep8ify", *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
        )
        stdout, _ = await p.communicate()

        async with self.async_open(f, "r") as fp:
            code = await fp.read()

        await self.run_in_thread_pool(shutil.rmtree, [f], {"ignore_errors": True})

        return code, stdout.decode()

    async def run_yapf(self, mid, style, code):
        """Runs YAPF, outputs the resulting code and logs in a tuple.."""
        name = f"{mid}{time.perf_counter() * 1000:.0f}.py"

        # noinspection PyProtectedMember
        f = os.path.join(tempfile._candidate_tempdir_list()[0], name)

        await self.run_in_thread_pool(shutil.rmtree, [f], {"ignore_errors": True})

        async with self.async_open(f, "w") as fp:
            await fp.write(code)

        args = ["--style", style.upper(), "-i", f]

        p = await asyncio.create_subprocess_exec(
            "yapf", *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
        )
        stdout, _ = await p.communicate()

        async with self.async_open(f, "r") as fp:
            code = await fp.read()

        await self.run_in_thread_pool(shutil.rmtree, [f], {"ignore_errors": True})

        return code, stdout.decode()

    async def blackify(self, ctx, code):
        """
        Blacks up the code given. If this is not successful, an error message
        is sent to the ctx, and None is returned. Otherwise, the fixed code is
        output instead.
        """
        code = utils.largest_block_re.search(code)
        if not code:
            await ctx.send("There is no code block there...", delete_after=10)
            return None

        code = code.group(1)
        if code.startswith("py"):
            code = code[3:]

        if code.startswith("python"):
            code = code[7:]

        code = textwrap.dedent(code)

        async with ctx.typing():
            return await self.run_black(ctx.message.id, code)

    @staticmethod
    def formatify(code, style, ctx, author):
        code, logs = code

        spf = pagination.StringNavigatorFactory(max_lines=None, prefix="```py", suffix="```")
        spf += f"# Using the {style} code-style\n"
        spf += code.replace("```", "ˋˋˋ")
        spf.add_page_break()
        spf += logs

        # Swap authors.
        temp = ctx.author
        # Lets both the invoker and the message being targeted edit by default
        ctx.author = author
        nav = spf.build(ctx)
        nav.owner = temp

        return nav

    @staticmethod
    async def parsify(ctx, input):
        if input == "^":
            m = await ctx.channel.history(limit=2).flatten()
            if m:
                m = m[-1]
                await ctx.message.delete()
            else:
                await ctx.send("Cannot detect a previous message.", delete_after=5)
                return None

            input = m.content
            ctx.message = m
            ctx.author = m.author
        elif input.isdigit():
            message = await ctx.channel.fetch_message(input)
            if not message:
                await ctx.send("That message cannot be found.", delete_after=5)
                return None
            else:
                input = message.content

        return input

    @fix.command(brief="Blackifies the code", aliases=["blackd"])
    async def black(self, ctx, *, code):
        """
        Runs the given code block under black to reformat it.

        If you just provide `^`, then the previous message is used instead.

        Code **must** be provided in code blocks, either way.

        Run `blackd` to delete the original message additionally.
        """
        author = ctx.author

        code = await self.parsify(ctx, code)

        if not code:
            return

        code = await self.blackify(ctx, code)

        if not code:
            return

        nav = self.formatify(code, "black", ctx, author)

        if ctx.invoked_with == "blackd":
            await ctx.message.delete()

        nav.start()

    @fix.command(brief="PEP8ifies the code", aliases=["pep8d"])
    async def pep8(self, ctx, *, code):
        """
        Runs the given code block under PEP8ify to reformat it.

        If you just provide `^`, then the previous message is used instead.

        Code **must** be provided in code blocks, either way.

        Run `pep8d` to delete the original message additionally.
        """
        author = ctx.author

        code = await self.parsify(ctx, code)

        if not code:
            return

        code = await self.pep8ify(ctx, code)

        if not code:
            return

        nav = self.formatify(code, "PEP8", ctx, author)

        if ctx.invoked_with == "pep8d":
            await ctx.message.delete()

        nav.start()

    @fix.command(brief="Runs the code through yapf to get Google-style formatting", aliases=["googled"])
    async def google(self, ctx, *, code):
        """
        Runs the given code block through the YAPF reformatter to conform to Google's
        official Python style guide.

        If you just provide `^`, then the previous message is used instead.

        Code **must** be provided in code blocks, either way.

        Run `googled` to delete the original message additionally.
        """
        author = ctx.author

        code = await self.parsify(ctx, code)

        if not code:
            return

        code = await self.yapfdify(ctx, "google", code)

        if not code:
            return

        nav = self.formatify(code, "Google", ctx, author)

        if ctx.invoked_with == "googled":
            await ctx.message.delete()

        nav.start()

    @fix.command(brief="Runs the code through yapf to get Chromium formatting", aliases=["chromiumd"])
    async def chromium(self, ctx, *, code):
        """
        Runs the given code block through the YAPF reformatter to conform to Google's
        official Python style guide.

        If you just provide `^`, then the previous message is used instead.

        Code **must** be provided in code blocks, either way.

        Run `chromiumd` to delete the original message additionally.
        """
        author = ctx.author

        code = await self.parsify(ctx, code)

        if not code:
            return

        code = await self.yapfdify(ctx, "chromium", code)

        if not code:
            return

        nav = self.formatify(code, "Chromium Project", ctx, author)

        if ctx.invoked_with == "chromiumd":
            await ctx.message.delete()

        nav.start()

    @fix.command(brief="Runs the code through yapf to get Facebook-style formatting", aliases=["facebookd"])
    async def facebook(self, ctx, *, code):
        """
        Runs the given code block through the YAPF reformatter to conform to Facebook's
        official Python style guide.

        If you just provide `^`, then the previous message is used instead.

        Code **must** be provided in code blocks, either way.

        Run `facebookifyd` to delete the original message additionally.
        """
        author = ctx.author

        code = await self.parsify(ctx, code)

        if not code:
            return

        code = await self.yapfdify(ctx, "facebook", code)

        if not code:
            return

        nav = self.formatify(code, "Facebook", ctx, author)

        if ctx.invoked_with == "facebookd":
            await ctx.message.delete()

        nav.start()
