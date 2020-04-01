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
Cog providing the `r` command.
"""
import io

import discord

import neko3.cog
from neko3 import neko_commands
from neko3 import pagination
from . import utils
from .toolchains import cranr


class RCog(neko3.cog.CogBase):
    @neko_commands.command(
        name="r",
        aliases=["cranr"],
        brief="Executes a given R-code block, showing the output" " and any graphs that were plotted.",
    )
    async def r_command(self, ctx, *, source):
        """
        Use the following to highlight your syntax:

        ```
        n.r
        ˋˋˋr
        
        t = (1:625) / 100\n
        x <- cos(t)\n
        y <- sin(t)\n
        plot(x, y)\n
        ˋˋˋ
        ```
        """
        code_block = utils.code_block_re.search(source)
        if code_block:
            source = code_block.group(2)

        with ctx.typing():
            result = await cranr.eval_r(source)

        binder = pagination.StringNavigatorFactory(prefix="```markdown", suffix="```", max_lines=40)

        # Last line is some error about rm not working.
        for line in result.output.split("\n"):
            if line == "sh: 1: rm: Permission denied":
                continue
            binder.add_line(line)

        binder.add_line(f"RESULT: {result.result.title()}")
        binder.add_line(f"STATE: {result.state.title()}")
        if result.fail_reason:
            binder.add_line(f"FAILURE REASON: {result.fail_reason}")

        booklet = binder.build(ctx)

        additionals = []

        for i in range(0, min(6, len(result.images))):
            with io.BytesIO(result.images[i][0]) as bio:
                bio.seek(0)
                f = discord.File(bio, f"output_{i + 1}.png")
                additionals.append(await ctx.send(file=f))

        await utils.start_and_listen_to_edit(ctx, booklet, *additionals)
