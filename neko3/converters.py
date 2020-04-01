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
A discord converter that can convert any form of mention into a corresponding
object (excluding emojis, as they don't count).

There is an additional implementation that will also accept raw snowflake
integers.
"""
import decimal
import re

import discord
from discord.ext import commands
from discord.ext import commands as _commands
from discord.ext.commands import MemberConverter
from discord.ext.commands import UserConverter

import neko3.functional


class GuildChannelConverter(commands.Converter):
    """
    Gets a guild channel
    """

    async def convert(self, ctx, body: str):
        for t in (commands.TextChannelConverter, commands.VoiceChannelConverter):
            try:
                return await t().convert(ctx, body)
            except Exception:
                pass

        raise commands.BadArgument(f"No channel matching `{body}` was found.")


class LowercaseCategoryConverter(commands.Converter):
    """
    Gets a category case insensitive. Discord doesn't show the name in the
    case the name is stored in; instead, it is transformed to uppercase. This
    makes this whole thing kind of useless to the user unless they can guess
    the correct permutation of character cases that was used.
    """

    async def convert(self, ctx, argument):
        argument = argument.lower()

        for category in ctx.guild.categories:
            if category.name.lower() == argument:
                return category

        raise commands.BadArgument(f"Category matching `{argument}` was not " "found.")


class CommandConverter(_commands.Converter):
    """Takes a fully qualified command name and returns the command object, if it exists."""

    async def convert(self, ctx, argument):
        c = ctx.bot.get_command(argument)
        if not c:
            raise _commands.BadArgument(f"Command `{argument}` was not found")
        else:
            return c


class CogConverter(_commands.Converter):
    """Takes a cog name and returns the cog, if it exists and is loaded."""

    async def convert(self, ctx, argument):
        try:
            return ctx.bot.cogs[argument]
        except KeyError as ex:
            raise _commands.BadArgument(f"{ex} was not loaded.")


class GuildChannelCategoryConverter(_commands.Converter):
    """
    Gets a guild channel or category.
    """

    async def convert(self, ctx, body: str):
        # If the input is in the format <#123> then it is a text channel.
        if body.startswith("<#") and body.endswith(">"):
            sf_str = body[2:-1]
            if sf_str.isdigit():
                sf = int(sf_str)
                channel = discord.utils.find(lambda c: c.id == sf, ctx.guild.channels)

                if channel:
                    return channel

            raise _commands.BadArgument(
                "Unable to access that channel. Make "
                "sure that it exists, and that I have "
                "access to it, and try again."
            )

        # Otherwise, it could be a text channel, a category or a voice channel.
        # We need to hunt for it manually.
        else:
            to_search = {*ctx.guild.channels, *ctx.guild.categories}
            channel = discord.utils.find(lambda c: c.name == body, to_search)
            if channel:
                return channel

            # Attempt case insensitive searching
            body = body.lower()
            channel = discord.utils.find(lambda c: c.name.lower() == body, to_search)
            if channel:
                return channel
            raise _commands.BadArgument("No channel matching input was found.")


class MentionConverter(_commands.Converter):
    """
    A converter that takes generic types of mentions.
    """

    async def convert(self, ctx, body: str):
        if body.startswith("<") and body.endswith(">"):
            tb = body[1:-1]

            if tb.startswith("@&"):
                return await _commands.RoleConverter().convert(ctx, body)
            elif tb.startswith("@") and tb[1:2].isdigit() or tb[1:2] == "!":
                return await _commands.MemberConverter().convert(ctx, body)
            elif tb.startswith("#"):
                return await _commands.TextChannelConverter().convert(ctx, body)
        else:
            try:
                return await _commands.EmojiConverter().convert(ctx, body)
            except Exception:
                pass

            try:
                return await GuildChannelCategoryConverter().convert(ctx, body)
            except Exception:
                pass

            try:
                return await _commands.PartialEmojiConverter().convert(ctx, body)
            except Exception:
                pass

        # Attempt to find in whatever we can look in. Don't bother looking
        # outside this guild though, as I plan to keep data between guilds
        # separate for privacy reasons.

        if ctx.guild:
            all_strings = [
                *ctx.guild.members,
                *ctx.guild.channels,
                *ctx.guild.categories,
                *ctx.guild.roles,
                *ctx.guild.emojis,
            ]

            def search(obj):
                if getattr(obj, "display_name", "") == body:
                    return True
                if str(obj) == body or obj.name == body:
                    return True
                return False

            # Match case first, as a role and member, say, may share the same
            # name barr the case difference, and this could lead to unwanted
            # or unexpected results. The issue is this will get slower as a
            # server gets larger, generally.
            result = discord.utils.find(search, all_strings)
            if not result:
                # Try again not matching case.
                def search(obj):
                    _body = body.lower()

                    if getattr(obj, "display_name", "").lower() == _body:
                        return True
                    if str(obj).lower() == _body:
                        return True
                    if obj.name.lower() == _body:
                        return True
                    return False

                result = discord.utils.find(search, all_strings)

            if not result:
                raise _commands.BadArgument(f"Could not resolve `{body}`")
            else:
                return result


class MentionOrSnowflakeConverter(MentionConverter):
    """
    A specialisation of MentionConverter that ensures that raw snowflakes can
    also be input. This returns the string if nothing was resolved.
    """

    async def convert(self, ctx, body: str):
        if body.isdigit():
            return int(body)
        else:
            try:
                return await super().convert(ctx, body)
            except _commands.BadArgument:
                return body


@neko3.functional.steal_docstring_from(_commands.Converter)
class BoolConverter(_commands.Converter):
    """Converts to a boolean."""

    async def convert(self, ctx, argument):
        if not isinstance(argument, (int, str, bool)):
            raise _commands.BadArgument("Invalid boolean value")
        else:
            if isinstance(argument, str):
                argument = argument.lower()

            try:
                return {
                    "0": False,
                    0: False,
                    "false": False,
                    "f": False,
                    "n": False,
                    "no": False,
                    "nope": False,
                    "nah": False,
                    "negative": False,
                    "unset": False,
                    "disable": False,
                    "disabled": False,
                    "unenable": False,
                    "unenabled": False,
                    False: False,
                    "1": True,
                    1: True,
                    "true": True,
                    "t": True,
                    "y": True,
                    "yes": True,
                    "ok": True,
                    "positive": True,
                    "set": True,
                    "enable": True,
                    "enabled": True,
                    True: True,
                }[argument]
            except KeyError:
                raise _commands.BadArgument(f"Did not recognise {argument} as a valid " "boolean argument")


@neko3.functional.steal_docstring_from(_commands.Converter)
class IntConverter(_commands.Converter):
    """Converts to an integer."""

    async def convert(self, ctx, argument):
        try:
            return int(argument)
        except Exception:
            raise _commands.BadArgument("Invalid integer value")


@neko3.functional.steal_docstring_from(_commands.Converter)
class FloatConverter(_commands.Converter):
    """Converts to a float."""

    async def convert(self, ctx, argument):
        try:
            return float(argument)
        except Exception:
            raise _commands.BadArgument("Invalid float value")


@neko3.functional.steal_docstring_from(_commands.Converter)
class DecimalConverter(_commands.Converter):
    """Converts to a multi-precision decimal."""

    async def convert(self, ctx, argument):
        try:
            return decimal.Decimal(argument)
        except Exception:
            raise _commands.BadArgument("Invalid integer value")


@neko3.functional.steal_docstring_from(_commands.clean_content)
class clean_content(_commands.clean_content):
    pass


class InsensitiveUserConverter(_commands.Converter):
    """
    Same as UserConverter, but this will fall back to attempting to match a user
    case insensitive if this fails before giving up.

    Procedure is as follows:
    1. Lookup using UserConverter
    2. Lookup using case insensitive username and discriminator
    3. Lookup using case insensitive username
    4. Lookup using ID globally on Discord.
    """

    async def convert(self, ctx, argument):
        try:
            return await UserConverter().convert(ctx, argument)
        except _commands.BadArgument:

            def predicate_user_and_discriminator(user):
                return user.name.lower() == argument[:-5].lower() and str(user.discriminator) == argument[-4:]

            def predicate_user(user):
                return user.name.lower() == argument.lower()

            result = None

            if len(argument) > 5 and argument[-5] == "#":
                result = discord.utils.find(predicate_user_and_discriminator, ctx.bot.users)

            if result is None:
                result = discord.utils.find(predicate_user, ctx.bot.users)

            if result is None:
                try:
                    result = await ctx.bot.fetch_user(int(argument))
                except Exception:
                    result = None

        if result is None:
            raise _commands.BadArgument('User "{}" not found'.format(argument))
        else:
            return result


class InsensitiveMemberConverter(_commands.Converter):
    """
    Same as MemberConverter, but this will fall back to attempting to match a user
    case insensitive if this fails before giving up.

    The procedure for this is as follows:

    1. Lookup using MemberConverter
    2. Lookup by ID
    3. Lookup by nickname insensitive
    4. Lookup by name#discrim insensitive
    5. Lookup by name insensitive
    6. Lookup by nick insensitive
    """

    async def convert(self, ctx, argument):
        if not ctx.guild:
            return await UserConverter().convert(ctx, argument)

        try:
            return await MemberConverter().convert(ctx, argument)
        except _commands.BadArgument:
            if argument.isdigit():
                try:
                    return await ctx.bot.fetch_user(int(argument))
                except discord.NotFound:
                    pass
            else:
                id_matcher = re.match(r"<@!?(\d+)>", argument)
                if id_matcher:
                    id = int(id_matcher.group(1))
                    try:
                        return await ctx.bot.fetch_user(id)
                    except discord.NotFound:
                        pass

            def predicate_user_and_discriminator(user):
                return user.name.lower() == argument[:-5].lower() and str(user.discriminator) == argument[-4:]

            search_pool = [*ctx.guild.members, *ctx.bot.users]

            def predicate_user(user):
                return user.name.lower() == argument.lower()

            def predicate_nick(user):
                return getattr(user, "nick", None) and user.nick.lower() == argument.lower()

            result = None

            if len(argument) > 5 and argument[-5] == "#":
                result = discord.utils.find(predicate_user_and_discriminator, search_pool)

            if result is None:
                result = discord.utils.find(predicate_user, search_pool)

            if result is None:
                result = discord.utils.find(predicate_nick, search_pool)

        if result is None:
            raise _commands.BadArgument('User "{}" not found'.format(argument))
        else:
            return result
