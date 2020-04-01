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
Press RespectPaid to pay respects.
"""
import asyncio
import contextlib
import dataclasses
import typing

import discord
from discord.ext import commands

from neko3 import aggregates
from neko3 import algorithms
from neko3 import embeds
from neko3 import fuzzy_search
from neko3 import neko_commands
from neko3 import string

# Last for 2 hours otherwise.
F_TIMEOUT = 2 * 60 * 60

# Set to True to enable `f' being a valid trigger for the command without
# a prefix.
ENABLE_NAKED = True

# Set to True to enable responding to reactions to the original trigger
# response
ENABLE_REACT = True

# How many messages to allow before rehoisting in chat.
REHOIST_AFTER = 5

# Max members to name in the embed before we switch to numbers to stop the
# embed being so big.
MAX_NAMED_MEMBERS = 15

# Minimum threshold for fuzzywuzzy closeness to determine two reasons as being
# implied to be the same thing, just either typo-ed or whatever.
FUZZY_SENSITIVITY_THRESH = 80


@dataclasses.dataclass()
class RespectPaid:
    members: aggregates.MutableOrderedSet
    message: discord.Message
    colour: int
    ctx: neko_commands.Context
    reason: typing.Optional[str]

    @property
    def channel(self):
        return self.ctx.channel


async def destroy_bucket_later(self, bucket):
    with contextlib.suppress():
        await asyncio.sleep(F_TIMEOUT)

        # If still active
        if bucket.message.id == self.buckets[bucket.channel].message.id:
            # Get up-to-date message state.
            msg = await bucket.channel.fetch_message(bucket.message.id)
            embed = msg.embeds[0]
            embed.colour = discord.Colour.greyple()
            embed.set_footer(text="Timed out...")
            await msg.edit(embed=embed)
            await msg.clear_reactions()
            del self.buckets[bucket.channel]


class RespectsCog(neko_commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.buckets: typing.Dict[discord.TextChannel, RespectPaid] = {}

    if ENABLE_NAKED:

        @neko_commands.Cog.listener()
        async def on_message(self, message):
            if message.content.lower() == "f" and message.guild:
                message.content = self.bot.command_prefix + "f"
                ctx = await self.bot.get_context(message)
                try:
                    await self.f.invoke(ctx)
                finally:
                    return

    if ENABLE_REACT:

        @neko_commands.Cog.listener()
        async def on_reaction_add(self, reaction: discord.Reaction, user: discord.Member):
            if user == self.bot.user:
                return

            channel = reaction.message.channel
            b = self.buckets.get(channel)

            if b is None:
                return

            c1 = b.message.id == reaction.message.id
            c2 = reaction.message.guild is not None
            c3 = user not in b.members
            c4 = reaction.emoji == "\N{REGIONAL INDICATOR SYMBOL LETTER F}"

            if all((c1, c2, c3, c4)):
                await self.append_to_bucket(b, user)
                message: discord.Message = reaction.message
                await message.remove_reaction(reaction, user)

    @staticmethod
    async def append_to_bucket(bucket, user):
        bucket.members.add(user)

        if 1 < len(bucket.members) <= MAX_NAMED_MEMBERS:
            first = bucket.members[:-1]
            last = bucket.members[-1]

            first = list(map(str, first))
            last = str(last) if last else ""

            message = ", ".join(first) + f" and {last} paid their respects"
        elif len(bucket.members) > MAX_NAMED_MEMBERS:
            message = f"{len(bucket.members)} people paid their respects"
        else:
            assert len(bucket.members) > 0, "Somehow appending first member, which is not allowed..."
            message = f"{bucket.members[0]} paid their respects"

        if bucket.reason:
            message += f" for {bucket.reason}"

        message = string.trunc(message)

        embed = embeds.Embed(description=message, colour=bucket.colour)

        # If the message is valid and exists, edit it. Otherwise,
        if bucket.message:
            await bucket.message.edit(embed=embed)
        else:
            bucket.message = await bucket.ctx.send(embed=embed)

        if ENABLE_REACT:
            await bucket.message.add_reaction("\N{REGIONAL INDICATOR SYMBOL LETTER F}")

    @commands.guild_only()
    @commands.cooldown(1, 60, commands.BucketType.member)
    @neko_commands.command(name="f", brief="Pay your respects.")
    async def f_command(self, ctx: neko_commands.Context, *, reason=None):
        colour = discord.Colour.blurple().value

        await ctx.message.delete()
        bucket = self.buckets.get(ctx.channel)

        if bucket:
            msg = bucket.message.id

            # Get the last 10 recent messages. If the bucket message
            # is in there, then update, else, delete the old message if
            # possible and then resend the new one. If the bucket is too
            # old, start anew.
            most_recent = await ctx.channel.history(limit=REHOIST_AFTER).flatten()
            new_msg = algorithms.find(lambda m: m.id == msg, most_recent)

            if bucket.reason and reason:
                is_matching_reason = fuzzy_search.deep_ratio(bucket.reason, reason)
                # if close match, e.g. there was a slight typo.
                is_matching_reason = is_matching_reason > FUZZY_SENSITIVITY_THRESH
            else:
                is_matching_reason = bucket.reason == reason or reason is None

            if new_msg:
                bucket.message = new_msg
            else:
                try:
                    await bucket.message.delete()
                    bucket.message = None
                except discord.NotFound:
                    if ctx.channel in self.buckets:
                        del self.buckets[ctx.channel]
                    bucket = None

            # If user gave a different reason, restart.
            if is_matching_reason:
                return await self.append_to_bucket(bucket, ctx.author)
            else:
                if ctx.channel in self.buckets:
                    try:
                        embed = bucket.message.embeds[0]
                        embed.colour = discord.Colour.greyple()
                        embed.set_footer(text=f"{ctx.author} changed the subject! For shame!")
                        await bucket.message.edit(embed=embed)
                        await bucket.message.clear_reactions()
                        del self.buckets[ctx.channel]
                    except Exception:
                        pass
                    finally:
                        bucket = None

        message = None

        if not bucket:
            if reason is None:
                message = await ctx.send(
                    embed=embeds.Embed(description=f"{ctx.author} paid their respects", colour=colour)
                )
            else:
                # Replace square brackets with a full-width variant. This will
                # stop the link formatting being triggered. This prevents
                # dickheads from smuggling dodgy links into chat hidden by
                # a seemingly innocent string via this bot.
                reason = reason.replace("[", "［").replace("]", "］")

                message = await ctx.send(
                    embed=embeds.Embed(
                        description=f"{ctx.author} paid their respects for" f" {string.trunc(reason, 1980)}",
                        colour=colour,
                    )
                )

        if ENABLE_REACT:
            await message.add_reaction("\N{REGIONAL INDICATOR SYMBOL LETTER F}")

        f_bucket = RespectPaid(aggregates.MutableOrderedSet({ctx.author}), message, colour, ctx, reason)

        self.buckets[ctx.channel] = f_bucket
        # noinspection PyAsyncCall
        asyncio.create_task(destroy_bucket_later(self, f_bucket))


def setup(bot):
    bot.add_cog(RespectsCog(bot))
