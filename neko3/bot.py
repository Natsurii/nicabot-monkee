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
Holds the bot implementation.
"""
import asyncio
import contextlib
import inspect
import os
import time
import traceback
import typing
from concurrent.futures import process
from concurrent.futures import thread

import async_timeout
import discord
from discord.ext import commands
from discord.utils import oauth_url

from neko3 import logging_utils
from neko3 import pagination
from neko3 import permission_bits
from neko3 import properties

__all__ = ("BotInterrupt", "Bot")

# Sue me.
BotInterrupt = KeyboardInterrupt

DM_ON_ERROR = True

MAX_MESSAGES = 300


###############################################################################
# Bot class definition.                                                       #
###############################################################################
class Bot(commands.Bot, logging_utils.Loggable):
    """
    My implementation of the Discord.py bot. This implements a few extra things
    on top of the existing Discord.py and discord.ext.commands implementations.

    Attributes
    ----------
    - ``permbits`` - optional. An integer bitfield
        representing the default permissions to invite the bot with when
        generating OAuth2 URLs.

    Properties
    ----------
    - ``invite`` - generates an invite URL.

    Events
    ------
    These are called before the task they represent is executed.
    - on_start()
    - on_logout()

    These are executed after the task they represent has been executed.
    - on_add_command(command)
    - on_remove_command(command)
    - on_add_cog(cog)
    - on_remove_cog(cog)
    - on_load_extension(extension)
    - on_unload_extension(name)

    :param _unused_loop: the event loop to run on.
    :param bot_config:
        This accepts a dict with two sub-dictionaries:
        - ``auth`` - this must contain a ``token`` and a ``client_id`` member.
        - ``bot`` - this contains a group of kwargs to pass to the Discord.py
            Bot constructor.
    """

    def __init__(self, _unused_loop, bot_config: dict):
        """
        Initialise the bot using the given configuration.
        """
        commands.Bot.__init__(self, **bot_config.pop("bot", {}), max_messages=MAX_MESSAGES)

        auth = bot_config["auth"]
        self.token = auth["token"]
        self.client_id = auth.get("client_id", None)
        self.debug = bot_config.pop("debug", False)
        if self.debug:
            self.loop.set_debug(True)

        # Used to prevent recursively calling logout.
        self.logged_in = False
        self.shutting_down = False

        # Load version and help commands
        self.logger.info(f"Using command prefix: {self.command_prefix}")

        self._on_exit_funcs = []
        self._on_exit_coros = []

        self.command_invoke_count = 0

        self.activity_semaphore = asyncio.Semaphore()

        self.thread_pool: typing.Optional[thread.ThreadPoolExecutor] = None
        self.process_pool: typing.Optional[process.ProcessPoolExecutor] = None

    def __enter__(self):
        threads = 4 * os.cpu_count() - 1 or 4
        processes = len(os.sched_getaffinity(0)) or 4
        self.logger.info(
            "Acquiring up to %s thread workers and up to %s process workers for asyncio executors", threads, processes
        )
        self.thread_pool = thread.ThreadPoolExecutor(max_workers=threads)
        self.process_pool = process.ProcessPoolExecutor(max_workers=processes)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logger.info("Shutting down all thread workers")
        self.thread_pool.shutdown(wait=True)
        self.logger.info("Shutting down all process workers")
        self.process_pool.shutdown(wait=True)

    def on_exit(self, func):
        """
        Registers a function or coroutine to be called when we exit, before
        the event loop is shut down.
        :param func: the function or coroutine to call.
        """
        if inspect.iscoroutinefunction(func):
            self._on_exit_coros.append(func)
        else:
            self._on_exit_funcs.append(func)
        return func

    @properties.cached_property()
    def invite(self):
        perm_bits = getattr(self, "permbits", 0)

        permissions = permission_bits.Permissions.to_discord_type(perm_bits)

        return oauth_url(self.client_id, permissions=permissions)

    @property
    def up_time(self) -> float:
        """Returns how many seconds the bot has been up for."""
        curr = time.time()
        return curr - getattr(self, "start_time", curr)

    async def get_owner(self) -> discord.User:
        """
        Attempts to read the bot owner object from the cache.
        If that cannot be found, then we have to query Discord for the
        information. If that fails, the owner_id is probably invalid. A
        discord.NotFound error is raised in this case.
        """
        user = self.get_user(self.owner_id)
        if not user:
            # noinspection PyUnresolvedReferences
            user = await self.fetch_user(self.owner_id)

        return user

    async def run(self, token):
        """Starts the bot with the given token."""
        self.logger.info(f"Invite me to your server at {self.invite}")
        self.logged_in = True
        self.dispatch("start")
        setattr(self, "start_time", time.time())

        await self.start(token)

    # noinspection PyBroadException
    async def logout(self):
        """
        Overrides the default behaviour by attempting to unload modules
        safely first.
        """
        self.shutting_down = False
        self.logger.warning(
            "Requested logout, first disabling all commands and cleaning up any navigators that are running"
        )

        # Disable all commands for the rest of the duration of the app
        for command in self.all_commands.values():
            command.enabled = False

        await self.change_presence(status=discord.Status.dnd, activity=discord.Game("shutting down"))

        # Shut down all paginators
        close_action = (
            pagination.CancelAction.REMOVE_NON_ROOT_MESSAGES
            | pagination.CancelAction.REMOVE_REACTS
            | pagination.CancelAction.ADD_BOT_SHUTDOWN_REACT
        )

        tasks = []

        for active_navigator in pagination.BaseNavigator.active_navigators:
            tasks.append(active_navigator.kill(close_action))

        # TypeError raises if state is bad
        with contextlib.suppress(asyncio.TimeoutError, TypeError):
            async with async_timeout.timeout(10):
                self.logger.info("Waiting up to 10s for %s pagination tasks to terminate cleanly", len(tasks))
                await asyncio.gather(*tasks, return_exceptions=True)
                self.logger.info("Pagination tasks finished")

        if not self.logged_in:
            return
        else:
            self.dispatch("logout")

        self.logger.info("Unloading modules, then logging out")

        # We cannot iterate across the current dict object holding extensions
        # while removing items from it as Python will not allow continued
        # iteration over a non-constant state iterator... so we make a shallow
        # copy of it first and iterate across that.
        cached_extensions = dict(**self.extensions)
        for extension in cached_extensions:
            # Sometimes have an issue with None extensions existing for some
            # strange reason.
            if not extension:
                continue

            try:
                self.unload_extension(extension)
            except BaseException:
                self.logger.exception("Could not unload extension")

        # Cannot resize dict as we iterate across it.
        cached_cogs = dict(**self.cogs)
        for cog in cached_cogs:
            try:
                self.remove_cog(cog)
            except BaseException:
                traceback.print_exc()

        await super().logout()

        self.logged_in = False

        # Call on_exit handlers
        for handler in self._on_exit_funcs:
            handler()
        for handler in self._on_exit_coros:
            await handler()

    # OCD.
    stop = logout

    # noinspection PyBroadException
    def add_cog(self, cog):
        """
        The default implementation does not attempt to tidy up if a cog does
        not load properly. This attempts to fix this.
        """
        try:
            self.logger.debug(f"Loading cog {type(cog).__name__!r}")

            super().add_cog(cog)
            self.dispatch("add_cog", cog)
        except BaseException as ex:
            try:
                self.remove_cog(cog)
            finally:
                raise ImportError(ex)

    def remove_cog(self, name):
        """Logs and removes a cog."""
        self.logger.debug(f"Removing cog {name!r}")
        # Find the cog.
        cog = self.get_cog(name)
        super().remove_cog(name)
        self.dispatch("remove_cog", cog)

    def _recursively_log_command(self, command, message):
        if command is not None:
            self.logger.debug(message, self.command_prefix, command.qualified_name)
            if hasattr(command, "commands") and command.commands is not None:
                for sub in command.commands:
                    self._recursively_log_command(sub, message)

    def add_command(self, command):
        """Logs and adds a command."""
        self._recursively_log_command(command, 'Adding command "%s%s"')
        super().add_command(command)
        self.dispatch("add_command", command)

    def remove_command(self, name):
        """Logs and removes an existing command."""
        # Find the command
        command = self.get_command(name)
        self._recursively_log_command(command, "Removing command %s%r")
        super().remove_command(name)
        self.dispatch("remove_command", command)

    def load_extension(self, name):
        """
        Overrides the default behaviour by logging info about the extension
        that is being loaded. This also returns the extension object we
        have loaded.
        :param name: the extension to load.
        :return: the extension that has been loaded.
        """
        self.logger.debug(f"Loading extension {name!r}")
        super().load_extension(name)
        extension = self.extensions[name]
        self.dispatch("load_extension", extension)
        return extension

    def unload_extension(self, name):
        """Logs and unloads the given extension."""
        self.logger.debug(f"Unloading extension {name!r}")
        self.dispatch("unload_extension", name)
        super().unload_extension(name)

    async def on_connect(self):
        await self._show_initializing()

    async def on_ready(self):
        await self.change_presence(status=discord.Status.online)

    async def on_reconnect(self):
        await self._show_initializing()

    async def _show_initializing(self):
        await self.change_presence(status=discord.Status.idle, activity=discord.Game("initializing"))

    async def on_command(self, ctx):
        self.command_invoke_count += 1
        if ctx.guild:
            self.logger.debug(
                "A user invoked %s in %s#%s (%s#%s) (message ID: %s)",
                ctx.message.content.replace("@", "@-"),
                ctx.guild,
                ctx.channel,
                ctx.guild.id,
                ctx.channel.id,
                ctx.message.id,
            )
        else:
            self.logger.debug(
                "A user invoked %s in private messages (message ID: %s)",
                ctx.message.content.replace("@", "@-"),
                ctx.message.id,
            )
