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
import fnmatch
import io
import random
import re
import time
import traceback

from discord.ext import commands

from neko3 import algorithms
from neko3 import cli
from neko3 import cog
from neko3 import converters
from neko3 import neko_commands
from neko3 import pagination


class OwnerCog(cog.CogBase):
    # @staticmethod
    # async def cog_check(ctx):
    #     return await ctx.bot.is_owner(ctx.author)
    @commands.is_owner()
    @neko_commands.command(name="shutdown", aliases=["kys", "die"], hidden=True)
    async def restart_command(self, ctx):
        """
        Kills the bot. If it is running as a systemd service, this should
        cause the bot to restart.
        """
        self.logger.critical("%s RAN COMMAND IN %s @ #%s TO FORCE BOT TO LOGOUT", ctx.author, ctx.guild, ctx.channel)
        await ctx.send("\N{OK HAND SIGN}")
        await ctx.bot.logout()

    @commands.is_owner()
    @neko_commands.command(name="error", hidden=True)
    async def error_command(self, ctx, discord_only: bool = False):
        """Tests error handling."""
        if discord_only:
            from discord.ext.commands import errors

            error_type = random.choice(
                (
                    errors.TooManyArguments,
                    errors.CommandOnCooldown,
                    errors.DisabledCommand,
                    errors.CommandNotFound,
                    errors.NoPrivateMessage,
                    errors.MissingPermissions,
                    errors.NotOwner,
                    errors.BadArgument,
                    errors.MissingRequiredArgument,
                    errors.CheckFailure,
                    errors.CommandError,
                    errors.DiscordException,
                    errors.CommandInvokeError,
                )
            )
        else:
            error_type = random.choice(
                (
                    Exception,
                    RuntimeError,
                    IOError,
                    BlockingIOError,
                    UnboundLocalError,
                    UnicodeDecodeError,
                    SyntaxError,
                    SystemError,
                    NotImplementedError,
                    FileExistsError,
                    FileNotFoundError,
                    InterruptedError,
                    EOFError,
                    NameError,
                    AttributeError,
                    ValueError,
                    KeyError,
                    FutureWarning,
                    DeprecationWarning,
                    PendingDeprecationWarning,
                )
            )

        await ctx.send(f"Raising {error_type.__qualname__}")
        raise error_type

    @staticmethod
    async def listen_to_edit(ctx, booklet=None, *additional_messages):
        # Lets the book start up first, otherwise we get an error. If
        # we cant send, then just give up.
        for _ in range(0, 60):
            await asyncio.sleep(1)

            async def custom_delete():
                for message in additional_messages:
                    await message.delete()
                await (await booklet.root_resp).delete()

            await neko_commands.wait_for_edit(ctx=ctx, msg=booklet.root_resp, timeout=180, custom_delete=custom_delete)

    @commands.is_owner()
    @neko_commands.command(name="setavatar", brief="Changes the avatar to the given URL.", hidden=True)
    async def set_avatar_command(self, ctx, *, url=None):
        async with self.acquire_http_session() as conn:
            if url is None:
                try:
                    url = ctx.message.attachments[0].url
                except (IndexError, AttributeError):
                    raise commands.MissingRequiredArgument("url or an attachment")

            self.logger.info("Changing avatar to %s", url)

            try:
                async with conn.request("get", url) as r, ctx.typing():
                    await ctx.bot.user.edit(avatar=await r.read())
            except Exception as ex:
                self.logger.exception("Failed to set avatar")
                await ctx.send(f"{type(ex).__name__}: {ex}")
            else:
                self.logger.info("Set avatar successfully.")
                neko_commands.acknowledge(ctx)

    @commands.is_owner()
    @neko_commands.command(name="eventloop", brief="Shows event loop information.", hidden=True)
    async def event_loop_command(self, ctx):
        all_tasks = asyncio.Task.all_tasks(loop=ctx.bot.loop)

        booklet = pagination.StringNavigatorFactory(prefix="```", suffix="```", max_lines=None)
        summary = []

        for task in all_tasks:
            with io.StringIO() as fp:
                task.print_stack(file=fp)
                booklet.add_line(fp.getvalue())
                # noinspection PyProtectedMember
                # Repr, shorten it as it is obscenely long
                tup = getattr(task, "_repr_info", lambda: ["", "None"])()[1]
                summary.append(tup)
            booklet.add_page_break()

        booklet.add_page_break(to_back=False)
        summary = "\n".join(summary)
        booklet.add(summary, to_back=False)
        booklet.add_line(f"{len(all_tasks)} coroutines in the loop.", to_back=False)
        booklet.start(ctx)

    @commands.is_owner()
    @neko_commands.command(name="reset", brief="Reset the cooldown on a command", hidden=True)
    async def reset_command(self, ctx, command: converters.CommandConverter = None):
        # noinspection PyProtectedMember
        def reset_command(command):
            if command._buckets and command._buckets._cache:
                cache = command._buckets._cache
                self.logger.warning(f"Clearing %s cached cooldowns for %s", len(cache), command.qualified_name)
                cache.clear()

        if command is None:
            all_commands = {*ctx.bot.walk_commands()}
            for command in all_commands:
                reset_command(command)
            await ctx.send(f"Reset cooldowns for {len(all_commands)} commands", delete_after=5)
            neko_commands.acknowledge(ctx, timeout=5)
        else:
            reset_command(command)
            neko_commands.acknowledge(ctx, timeout=5)

    @commands.is_owner()
    @neko_commands.command(name="debug", brief="Times the execution of another command.", hidden=True, disabled=True)
    async def debug_command(self, ctx, *, content):
        message = ctx.message
        command_start = message.content.index(ctx.invoked_with) + len(ctx.invoked_with)
        message.content = message.content[command_start:].lstrip()

        if message.content.startswith(("!!", "debug")):
            await ctx.send("That would loop recursively, so I am not going to invoke it.")
            return

        message.content = ctx.prefix + message.content

        stream = io.StringIO()
        reraise = None

        start = time.perf_counter()
        with contextlib.redirect_stderr(stream), contextlib.redirect_stdout(stream), cli.STREAM.add_delegate(stream):
            try:
                cli.LOGGER_STREAM = stream
                new_ctx = await ctx.bot.get_context(message)
                await new_ctx.command.invoke(new_ctx)
            except BaseException as ex:
                self.logger.exception("An error occurred executing %s:", new_ctx.message.content, exc_info=ex)
                reraise = ex
            finally:
                elapsed = time.perf_counter() - start

        stream.seek(0)
        logs = stream.getvalue()

        if logs:
            nav = pagination.StringNavigatorFactory(prefix="```", suffix="```")
            for line in stream.getvalue().split("\n"):
                nav.add_line(line)

            nav.start(new_ctx)

        await ctx.send(f"> Execution finished in {elapsed * 1_000:.2f}ms")

        if reraise is not None:
            raise reraise

    @neko_commands.command(name="load", disabled=True)
    async def load_command(self, ctx, *, package):
        try:
            self.logger.info("%s requested loading of %s", ctx.author, package)

            with algorithms.TimeIt() as timer:
                ctx.bot.load_extension(package)

            await ctx.send(f"Loaded {package} in approx {timer.time_taken * 1_000:.0f}ms.")
        except Exception as ex:
            self.logger.exception("Failed to load %s", package, exc_info=ex)
            p = pagination.StringNavigatorFactory(prefix="```", suffix="```", max_lines=10)
            for line in traceback.format_exception(type(ex), ex, ex.__traceback__):
                p.add_line(line.rstrip())

            p.start(ctx)

    @neko_commands.command(name="unload", disabled=True)
    async def unload_command(self, ctx, *, package):
        extensions = fnmatch.filter(ctx.bot.extensions, package)
        count = len(extensions)
        p = pagination.StringNavigatorFactory(prefix="```", suffix="```", max_lines=10)
        p.add_line(f"Requesting unload of extensions matching pattern {package}")
        p.add_line(f"Matched {count} extension{'s' if count - 1 else ''}")

        for extension in extensions:
            try:
                with algorithms.TimeIt() as timer:
                    ctx.bot.unload_extension(extension)
                p.add_line(f"Unloaded {extension} in approx {timer.time_taken * 1_000:.0f}ms.")
            except Exception as ex:
                self.logger.exception("Could not unload %s", extension, exc_info=ex)
                p.add_line(f"Could not unload {extension} because {type(ex).__name__}: {ex}")

        p.start(ctx)

    @neko_commands.command(name="reload", disabled=True)
    async def reload_command(self, ctx, *, package="*"):
        extensions = fnmatch.filter(ctx.bot.extensions, package)
        count = len(extensions)
        p = pagination.StringNavigatorFactory(prefix="```", suffix="```", max_lines=10)
        p.add_line(f"Requesting reload of extensions matching pattern {package}")
        p.add_line(f"Matched {count} extension{'s' if count - 1 else ''}")

        successes = 0
        failures = 0

        with algorithms.TimeIt() as outer_timer:
            for extension in extensions:
                did_unload = False
                try:
                    with algorithms.TimeIt() as timer:
                        ctx.bot.unload_extension(extension)
                        did_unload = True
                        ctx.bot.load_extension(extension)
                    p.add_line(f"Reloaded {extension} in approx {timer.time_taken * 1_000:.0f}ms.")
                    successes += 1
                except Exception as ex:
                    prefix = "" if did_unload else "un"
                    self.logger.exception("Could not %sload %s", prefix, extension, exc_info=ex)
                    p.add_line(f"Could not {prefix}load {extension} " f"because {type(ex).__name__}: {ex}")
                    failures += 1

        p.add_line(f"Reloaded {successes}/{successes + failures} in " f"approx {outer_timer.time_taken * 1_000:.0f}ms.")

        p.start(ctx)

    @neko_commands.command(name="speedtest", hidden=True, brief="Runs a speedtest on my connection for diagnostics")
    @commands.is_owner()
    async def speed_test_command(self, ctx):
        cmd = (
            "curl -s "
            "https://raw.githubusercontent.com/sivel"
            "/speedtest-cli/master/speedtest.py | "
            "python -W ignore -"
        )

        p = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)

        async with ctx.typing():
            content, _ = await p.communicate()

        content = re.sub(r"(\d{1,3}\.){3}\d{1,3}", "xxx.xxx.xxx.xxx", content.decode())
        content = re.sub(r"Hosted by.*", "", content, re.I)

        await ctx.send(f"```fix\n{content}\n```\n")


def setup(bot):
    bot.add_cog(OwnerCog(bot))
