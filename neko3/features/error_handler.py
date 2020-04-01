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

import asyncio
import contextlib
import datetime
import inspect
import traceback
import uuid

import discord
from discord.ext import commands

from neko3 import cog
from neko3 import fuzzy_search


def mark_as_handler(ex_type, *ex_types):
    def decorator(func):
        assert asyncio.iscoroutinefunction(func), "Handler must be a coroutine function"
        setattr(func, "__error_handler_for__", [ex_type, *ex_types])
        return func

    return decorator


def is_handler(obj):
    try:
        return all(issubclass(cls, Exception) for cls in obj.__error_handler_for__)
    except AttributeError:
        return False


# These are exception types we can safely print out to the user in a message with no checking.
MANAGED_EXCEPIONS = [
    commands.NotOwner,
    commands.MissingRequiredArgument,
    commands.BadArgument,
    commands.BotMissingPermissions,
    commands.MissingPermissions,
    commands.NoPrivateMessage,
    commands.TooManyArguments,
    discord.Forbidden,
    discord.NotFound,
]


class ErrorHandlerCog(cog.CogBase):
    def __init__(self, bot):
        super().__init__(bot)
        self.handlers = {}
        for _, handler in inspect.getmembers(self, is_handler):
            for ex_t in handler.__error_handler_for__:
                self.handlers[ex_t] = handler

        self.logger.info("Registered exception handlers for %s scenarios", len(self.handlers))

    @cog.CogBase.listener()
    async def on_command_error(self, ctx, error):
        self.logger.debug("Handling exception", exc_info=error)

        cause = error.__cause__ if error.__cause__ and not isinstance(error, commands.BadArgument) else error

        for klass in type(cause).mro():
            c = klass in self.handlers
            if c:
                return await self.handlers[klass](ctx, cause)

    @mark_as_handler(commands.CommandNotFound)
    async def on_command_not_found(self, ctx, error):
        command = ctx.message.content[len(ctx.prefix) :].strip()
        possible_matches = fuzzy_search.extract(
            command, ctx.bot.all_commands, scoring_algorithm=fuzzy_search.deep_ratio, min_score=60, max_results=5
        )

        if possible_matches:
            message = "Command not found. However, I did find commands with similar names:\n"
            message += "\n".join(f"> `{ctx.prefix}{match}`" for match, _ in possible_matches)

            await ctx.send(message, delete_after=30)
        else:
            await ctx.message.add_reaction("\N{BLACK QUESTION MARK ORNAMENT}")

    @mark_as_handler(commands.DisabledCommand, commands.CheckFailure)
    async def on_command_disabled(self, ctx, error):
        await ctx.message.add_reaction("\N{NO ENTRY SIGN}")

    @mark_as_handler(commands.CommandOnCooldown)
    async def on_command_on_cooldown(self, ctx, error):
        reaction = "\N{SNOWFLAKE}\N{VARIATION SELECTOR-16}"
        asyncio.create_task(ctx.message.add_reaction(reaction))
        await asyncio.sleep(error.retry_after)
        try:
            await ctx.message.remove_reaction(reaction, ctx.bot.user)
        except discord.NotFound:
            pass

    @mark_as_handler(NotImplementedError)
    async def on_not_implemented_error(self, ctx, error):
        await ctx.message.add_reaction("\N{CONSTRUCTION SIGN}")

    @mark_as_handler(*MANAGED_EXCEPIONS)
    async def on_managed_exception(self, ctx, error):
        message = str(error).strip()
        if message:
            await ctx.send(message)

    @mark_as_handler(Exception)
    async def on_unhandled_exception(self, ctx, error):
        ref = uuid.uuid4()
        self.logger.exception("Unhandled exception! UUID: %s", ref, exc_info=error)
        await ctx.send(f"Uh oh, something unexpected went wrong! I've DM'ed this to my owner!\n\n> Ref: `{ref}`")
        await self.tell_me(error, ref)

    @cog.CogBase.listener()
    async def on_error(self, error):
        ref = uuid.uuid4()
        self.logger.exception("Unhandled exception! UUID: %s", ref, exc_info=error)
        await self.tell_me(error, ref)

    async def tell_me(self, error, uuid):
        with contextlib.suppress(BaseException):
            me = (await self.bot.application_info()).owner
            pag = commands.Paginator()
            pag.add_line(f"Exception report {uuid} at {datetime.datetime.utcnow()}")
            pag.add_line("")
            for line in "".join(traceback.format_exception(type(error), error, error.__traceback__)).split("\n"):
                pag.add_line(line)
            for page in pag.pages:
                await me.send(page)

def setup(bot):
    bot.add_cog(ErrorHandlerCog(bot))
