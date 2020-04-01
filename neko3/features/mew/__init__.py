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
Implementation of the Mew command and cog.
"""
import io
import os
import random

import aiofiles
import discord
from discord.ext import commands

from neko3 import configuration_files
from neko3 import files
from neko3 import fuzzy_search
from neko3 import logging_utils
from neko3 import neko_commands

# Relative to this directory.
bindings_file = "bindings"
images_directory = files.in_here("images")


class MewReactsCog(neko_commands.Cog, logging_utils.Loggable):
    """Reactions cog."""

    def __init__(self):
        bindings = configuration_files.get_from_here(bindings_file).sync_get()

        # Attempt to locate all files to ensure paths are valid.
        potential_targets = set()
        for im_list in bindings.values():
            [potential_targets.add(im) for im in im_list]

        targets_to_path = {}

        for target in potential_targets:
            path = os.path.join(images_directory, target)
            if os.path.exists(path) and os.path.isfile(path):
                self.logger.debug(f"Discovered {path}.")
                targets_to_path[target] = path
            else:
                self.logger.warning(f"Could not find {path}. Excluding image.")

        self.images = {}

        for react_name, binding_list in bindings.items():
            valid_list = []
            for image in binding_list:
                if image in targets_to_path and image not in valid_list:
                    valid_list.append(targets_to_path[image])

            if not valid_list:
                self.logger.warning(f"I am disabling {react_name} due to lack " "of _existing_ files.")
            else:
                self.images[react_name.lower()] = valid_list

        super().__init__()

    @commands.cooldown(rate=5, per=30.0, type=commands.BucketType.channel)
    @neko_commands.command(
        name="mew",
        brief="A bunch of reaction images I liked. Call with no argument for " "usage info.",
        examples=["gg", "sleepy", "owo"],
        aliases=["mewd"],
    )
    async def mew_command(self, ctx, *, react=""):
        """
        Posts a reaction. Run without any commands to see a list of reactions.

        Run `mewd` to destroy the calling message.
        """
        with ctx.typing():
            react = react.lower()

            # If the react is there, then send it!
            match, _ = fuzzy_search.extract_best(react, self.images, scoring_algorithm=fuzzy_search.deep_ratio)

            if react and match:
                try:
                    if ctx.invoked_with == "mewd":
                        await ctx.message.delete()
                    file_name = random.choice(self.images[match])

                    async with aiofiles.open(file_name, "rb") as afp:
                        bytes_obj = io.BytesIO(await afp.read())
                        bytes_obj.seek(0)

                    await ctx.send(file=discord.File(bytes_obj, file_name))
                except FileNotFoundError:
                    self.logger.exception("File not found...")
                    await ctx.send(
                        "Something broke and the dev " "was shot. Please try again later ^w^", delete_after=15
                    )
            # Otherwise, if the react doesn't exist, or wasn't specified, then
            # list the reacts available.
            elif not react:
                self.mew_command.reset_cooldown(ctx)
                await ctx.author.send(
                    "**Mew reactions:**\n\n"
                    + " ".join(map(lambda n: f"`{n}`", sorted(self.images)))
                    + ".\n\nThanks to Zcissors for providing the emotes and "
                    "command alias configurations."
                )
                await ctx.send(f"{ctx.author.mention}: Check your DMs!", delete_after=10)
            else:
                self.mew_command.reset_cooldown(ctx)
                await ctx.send(
                    f"{ctx.author.mention}: That one wasn't found. Run without a name to get a "
                    "list sent to you via DMs.",
                    delete_after=15,
                )


def setup(bot):
    bot.add_cog(MewReactsCog())
