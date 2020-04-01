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
Various thread and process pool templates.
"""
import asyncio
import functools
import inspect
import logging
import os  # File system access.
import typing

import aiofiles
import aiohttp
from discord.ext import commands

from neko3 import logging_utils


def _magic_number(*, cpu_bound=False):
    """
    Returns the magic number for this machine. This is the number of
    concurrent execution media to spawn in a pool.
    :param cpu_bound: defaults to false. Determines if we are considering
        IO bound work (the default) or CPU bound.
    :return: 3 * the number of USABLE logical cores if we are IO bound. If we
        are CPU bound, we return 2 * the number of processor cores, as CPU
        bound work utilises the majority of it's allocated time to doing
        meaningful work, whereas IO is usually slow and consists of thread
        yielding. There is no point spamming the CPU with many more jobs than
        it can concurrently handle with CPU bound work, whereas it will provide
        a significant performance boost for IO bound work. We don't consider
        scheduler affinity for CPU bound as we expect that to use a process
        pool, which is modifiable by the kernel.
    """
    # OR with 1 to ensure at least 1 "node" is detected.
    if cpu_bound:
        return 4 * os.cpu_count() - 1 or 1
    else:
        return 6 * (len(os.sched_getaffinity(0)) or 1)


def _pickle_and_wrap(call, *args, **kwargs):
    args = args or ()
    kwargs = kwargs or {}

    logging.basicConfig(level=logging.root.level)
    name = inspect.getfile(call) + "." + call.__qualname__
    logging.root.name = f"{name} parent_pid={os.getppid()} child_pid={os.getpid()}"
    logging.debug(f"Firing up process")
    result = call(*args, **kwargs)
    logging.debug(f"Shutting down process.")
    return result


class CogBase(logging_utils.Loggable, commands.Cog):
    """Contains any shared resource traits we may want to acquire."""

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    @classmethod
    def acquire_http_session(cls):
        """
        Acquires a new HTTP client session. This must be closed after use to
        avoid leaving connections open.
        """
        return aiohttp.ClientSession()

    def async_open(self, file_name, *args, **kwargs):
        self.logger.info("Reading %s...", file_name)
        kwargs.setdefault("executor", self.bot.thread_pool)
        kwargs.setdefault("loop", self.bot.loop)
        return functools.partial(aiofiles.open, file_name, *args, **kwargs)()

    async def run_in_thread_pool(self, call: typing.Callable, args: typing.List = None, kwargs: typing.Dict = None):
        kwargs = kwargs or {}
        args = args or ()
        return await self._execute(self.bot.thread_pool, call, *args, **kwargs)

    async def run_in_process_pool(self, call: typing.Callable, args: typing.List = None, kwargs: typing.Dict = None):
        kwargs = kwargs or {}
        args = args or ()
        return await self._execute(self.bot.process_pool, _pickle_and_wrap, call, *args, **kwargs)

    async def _execute(self, executor, call, *args, **kwargs):
        self.logger.debug("Executing %s in %s", call, executor)

        partial = call if isinstance(call, functools.partial) else functools.partial(call, *args, **kwargs)

        loop = asyncio.get_running_loop()

        if not args:
            args = []
        if not kwargs:
            kwargs = {}

        return await loop.run_in_executor(executor, partial)

    @classmethod
    def create_setup(cls):
        def setup(bot):
            bot.add_cog(cls(bot))

        return setup
