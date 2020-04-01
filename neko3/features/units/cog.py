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
Listens to messages on all channels, and tests if any substrings can be found
that appear to be units of measurement.

A reaction is then added to the corresponding message for a given period of
time. Interacting with it will trigger the main layer of logic in this
extension.

On a positive hit, we convert those into an SI representation and then back to
every commonly used possibility.
"""
import asyncio
import collections

import neko3.cog
from neko3 import neko_commands
from neko3 import theme
from . import conversions
from . import models
from . import parser
from . import tokenizer

# Wait 30 minutes.
TIME_TO_WAIT = 30 * 60
REACTION = "\N{STRAIGHT RULER}"
MAX = 6


class UnitCog(neko3.cog.CogBase):
    checks = (
        # Do not respond to bots
        lambda m: not m.author.bot,
        # Do not respond to code blocks
        lambda m: "```" not in m.content,
        # Do not respond to DMs.
        lambda m: bool(m.guild),
    )

    # @commands.Cog.listener()
    # async def on_message(self, message):
    #     """Delegates the incoming message parsing to a thread-pool worker."""
    #     if not all(c(message) for c in self.checks):
    #         return
    #     else:
    #         e = await self.run_in_io_executor(self.worker,  [message])
    #
    #         if e:
    #             await self.await_result_request(message, e)

    @neko_commands.command(name="convert", brief="Performs conversions on the given input.", aliases=["conv"])
    async def convert_command(self, ctx, *, query=None):
        """
        If no input is given, the previous message in chat is inspected.
        """
        try:
            if query is None:
                # Get channel history until we find the message before the
                # one corresponding to the invoked context.
                is_next, message = False, None
                async for message in ctx.channel.history(limit=None):
                    if is_next:
                        break
                    elif message.id == ctx.message.id:
                        is_next = True

                if is_next:
                    query = message.content
                else:
                    raise ValueError("No valid message found in history.")

            e = await self.run_in_thread_pool(self.worker, [ctx, query])
            await ctx.send(embed=e)

        except ValueError as ex:
            await ctx.send(str(ex), delete_after=10)

    @staticmethod
    def worker(ctx, message):
        """Calculates all conversions on a separate thread."""
        # Parse potential matches by pattern matching.
        tokens = list(tokenizer.tokenize(message))

        if not tokens:
            raise ValueError("No potential unit matches found.")

        # Parse real unit measurements that we can convert.
        quantities = list(parser.parse(*tokens))

        if not quantities:
            raise ValueError("No actual unit matches found.")

        # Get any conversions
        equivalents = collections.OrderedDict()

        for quantity in quantities:
            compatible = conversions.get_compatible_models(quantity.unit, ignore_self=True)

            # Convert to SI first.
            si = quantity.unit.to_si(quantity.value)

            this_equivalents = tuple(models.ValueModel(c.from_si(si), c) for c in compatible)

            equivalents[quantity] = this_equivalents

        embed = theme.generic_embed(ctx)

        mass_msg_added = False

        for original, equivalents in list(equivalents.items())[:MAX]:
            equiv_str = []
            for equivalent in equivalents:
                equivalent = models.pretty_print(
                    equivalent.value,
                    equivalent.name,
                    use_long_suffix=True,
                    use_std_form=not original.unit.never_use_std_form,
                    none_if_rounds_to_zero=True,
                )
                equiv_str.append(equivalent)

            equiv_str = list(filter(bool, equiv_str))

            if not equiv_str:
                continue

            embed.add_field(
                name=models.pretty_print(
                    original.value,
                    original.name,
                    use_long_suffix=True,
                    use_std_form=not original.unit.never_use_std_form,
                    none_if_rounds_to_zero=False,
                ),
                value="\n".join(equiv_str),
                inline=True,
            )

            if original.unit.unit_type == models.UnitCategoryModel.FORCE_MASS:
                if not mass_msg_added:
                    mass_msg_added = True
                    embed.set_footer(
                        text="This example assumes that mass measurements are "
                        "accelerating at 1G. Likewise, acceleration "
                        "assumes that it applies to 1kg mass."
                    )

        if not len(embed.fields):
            del embed
            raise ValueError("No valid or non-zero conversions found.")

        return embed

    async def await_result_request(self, original_message, embed):
        try:
            # Run asynchronously to be more responsive.
            self.bot.loop.create_task(original_message.add_reaction(REACTION))

            def predicate(reaction, user):
                c1 = reaction.message.id == original_message.id
                c2 = reaction.emoji == REACTION
                c3 = not user.bot

                return all((c1, c2, c3))

            _, user = await self.bot.wait_for("reaction_add", check=predicate, timeout=TIME_TO_WAIT)

            m = await original_message.channel.fetch_message(original_message.id)

            for reaction in m.reactions:
                if reaction.emoji == REACTION:
                    async for r_user in reaction.users():
                        if r_user == self.bot.user or r_user == user:
                            await m.remove_reaction(reaction.emoji, r_user)

            await original_message.channel.send(embed=embed)
        except asyncio.TimeoutError:
            self.logger.info("timed out and continued without a result")
        except Exception as ex:
            self.logger.exception("Unexpected error", exc_info=ex)
