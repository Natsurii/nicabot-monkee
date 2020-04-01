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
Basic utilities and stuff.
"""
import asyncio
import collections
import inspect
import platform
import subprocess
import time

import psutil
from discord.ext import commands

import neko3
from neko3 import cog
from neko3 import neko_commands
from neko3 import properties
from neko3 import string
from neko3 import theme


# noinspection PyBroadException,PyShadowingNames
class BasicCommandsCog(cog.CogBase):
    async def bot_check(self, ctx):
        """
        Prevents us, while not in debug mode, from responding to other
        bots what-so-ever.

        This is a useful thing to have in debugging mode for testing.
        """
        return self.bot.debug or not ctx.author.bot

    @properties.cached_property()
    def dependencies(self):
        self.logger.info("Calculating dependencies for Neko3. This will be cached for the next run.")
        python = f"{platform.python_implementation()} {platform.python_version()} {platform.python_revision()}\n"
        python += f"{platform.python_compiler()} {platform.python_build()} on {platform.platform()}\n"
        python += f"Hosted on {platform.node() or 'some machine somewhere, idk'}"
        pip = subprocess.check_output(["pip", "--version"], universal_newlines=True)
        dependencies = subprocess.check_output(["pip", "freeze"], universal_newlines=True)
        return f"{python}\n\n{pip}\n{dependencies}"

    @property
    def up_time(self) -> str:
        """Get the uptime of the bot as a string."""
        uptime = self.bot.up_time
        if uptime >= 60 * 60 * 24:
            uptime /= 60.0 * 60 * 24
            uptime = round(uptime, 1)
            uptime = f'{uptime} day{"s" if uptime != 1 else ""}'
        elif uptime >= 60 * 60:
            uptime /= 60.0 * 60
            uptime = round(uptime, 1)
            uptime = f'{uptime} hour{"s" if uptime != 1 else ""}'
        elif uptime >= 60:
            uptime /= 60.0
            uptime = round(uptime, 1)
            uptime = f'{uptime} minute{"s" if uptime != 1 else ""}'
        else:
            uptime = int(uptime)
            uptime = f'{uptime} second{"s" if uptime != 1 else ""}'

        return uptime

    async def get_commits(self):
        """
        Gets the most recent commit.
        """
        # Returns a tuple of how long ago, the body, and the number of commits.
        # %ar = how long ago
        # %b  = body
        # %h  = shortened hash
        # $(git log --oneline | wc -l) - commit count.

        f1 = asyncio.create_subprocess_exec(
            "git",
            "log",
            "--pretty=%ar",
            "--relative-date",
            "-n1",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            stdin=asyncio.subprocess.DEVNULL,
        )

        f2 = asyncio.create_subprocess_exec(
            "git",
            "log",
            "--pretty=%s%n%n%b",
            "-n1",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            stdin=asyncio.subprocess.DEVNULL,
        )

        f3 = asyncio.create_subprocess_shell(
            "git log --oneline | wc -l",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            stdin=asyncio.subprocess.DEVNULL,
        )

        f1_res, f2_res, f3_res = await asyncio.gather(f1, f2, f3)

        return (
            b"".join([await f1_res.stdout.read()]).decode("utf-8").strip(),
            b"".join([await f2_res.stdout.read()]).decode("utf-8").strip(),
            int(b"".join([await f3_res.stdout.read()]).decode("utf-8")),
        )

    @neko_commands.command(name="uptime", brief="Shows how long I have been alive " "for.")
    async def up_time_command(self, ctx):
        """Determines the time.perf_counter runtime of the bot."""
        await ctx.send(self.up_time)

    @neko_commands.command(
        name="version", aliases=["v", "ver", "about"], brief="Shows versioning info, and some other things."
    )
    async def version_command(self, ctx):
        """Shows versioning information and some other useful statistics."""
        licence = neko3.__license__
        repo = neko3.__repository__
        version = neko3.__version__
        uptime = self.up_time
        docstring = inspect.getdoc(neko3)
        if docstring:
            # Ensures the license is not included in the description, as that
            # is rather long.
            docstring = "".join(docstring.split("===", maxsplit=1)[0:1])

            docstring = [string.remove_single_lines(inspect.cleandoc(docstring))]
        else:
            docstring = []

        docstring.append(f"_Licensed under the **{licence}**_")

        embed = theme.generic_embed(ctx, description=f"v{version}\n" + f"\n".join(docstring), url=repo)

        # Most recent changes
        # Must do in multiple stages to allow the cached property to do
        # magic first.
        when, update, count = await self.get_commits()

        embed.add_field(name=f"Update #{count} ({when})", value=string.trunc(update, 1024), inline=False)
        embed.add_field(name="Dependencies", value=f"Run `{ctx.prefix}dependencies` to see what makes Nekozilla tick!")

        embed.set_image(url=ctx.bot.user.avatar_url)

        embed.set_footer(text=f"Uptime: {uptime}")

        embed.set_thumbnail(url=ctx.bot.user.avatar_url)
        await ctx.send(embed=embed)

    @neko_commands.command(name="canirun", brief="Determines if you can run the command here.")
    async def can_i_run_command(self, ctx, command):
        command = ctx.bot.get_command(command)
        if command is None:
            return await ctx.send("That command does not exist...", delete_after=5)

        try:
            can_run = await command.can_run(ctx)
        except Exception as ex:
            await ctx.send("You cannot run the command here, because: " f"`{type(ex).__name__}: {ex!s}`")
        else:
            await ctx.send(f'You {can_run and "can" or "cannot"} run this ' "command here.")

    @commands.cooldown(1, 30, commands.BucketType.guild)
    @neko_commands.command(
        name="stats",
        brief="Shows a summary of what this bot can see, the bot's overall health and status, and software "
        "versioning information",
    )
    async def stats_command(self, ctx):
        import threading
        from datetime import timedelta
        import platform

        # Calculates the ping, and will store our message response a little
        # later
        ack_time = 0

        def callback(*_, **__):
            nonlocal ack_time
            ack_time = time.perf_counter()

        start_ack = time.perf_counter()
        future = ctx.bot.loop.create_task(ctx.send("Getting ping!"))
        future.add_done_callback(callback)

        message = await future

        event_loop_latency = time.perf_counter() - start_ack
        ack_time -= start_ack
        event_loop_latency -= ack_time

        users = max(len(ctx.bot.users), len(list(ctx.bot.get_all_members())))
        tasks = len(asyncio.Task.all_tasks(loop=asyncio.get_event_loop()))
        procs = 1 + len(psutil.Process().children(recursive=True))

        tasks_threads_procs = f"{tasks}/{threading.active_count()}/{procs}"

        stats = collections.OrderedDict(
            {
                "Commands invoked": f"{ctx.bot.command_invoke_count}",
                "Users": f"{users:,}",
                "Guilds/channels": f"{len(ctx.bot.guilds):,}/" f"{len(list(ctx.bot.get_all_channels())):,}",
                "Commands/aliases": f"{len(frozenset(ctx.bot.walk_commands())):,}" f"/{len(ctx.bot.all_commands):,}",
                "Futures/Threads/Processes": tasks_threads_procs,
                "Cogs/extensions": f"{len(ctx.bot.cogs):,}/{len(ctx.bot.extensions):,}",
                "Bot uptime": str(timedelta(seconds=ctx.bot.up_time)),
                "System uptime": str(timedelta(seconds=time.perf_counter())),
                "Heartbeat latency": f"∼{ctx.bot.latency * 1000:,.2f}ms",
                "`ACK` latency": f"∼{ack_time * 1000:,.2f}ms",
                "Event loop latency": f"{event_loop_latency * 1e6:,.2f}µs",
                "Architecture": f"{platform.machine()} " f'{" ".join(platform.architecture())}',
                "Python": f"{platform.python_implementation()} "
                f"{platform.python_version()}\n"
                f'{" ".join(platform.python_build()).title()}\n'
                f"{platform.python_compiler()}",
            }
        )

        if ctx.bot.shard_count and ctx.bot_shard_count > 1:
            stats["Shards"] = f"{ctx.bot.shard_count}"

        embed = theme.generic_embed(ctx)

        # embed.set_thumbnail(url=ctx.bot.user.avatar_url)

        embed.set_footer(text=platform.platform())

        for name, value in stats.items():
            embed.add_field(name=name, value=value, inline=len(str(value)) < 100)

        await message.edit(content="", embed=embed)

        em = "\N{REGIONAL INDICATOR SYMBOL LETTER X}"

        async def later():
            try:
                await message.add_reaction(em)
                await ctx.bot.wait_for(
                    "reaction_add",
                    timeout=300,
                    check=lambda r, u: r.emoji == em
                    and not u.bot
                    and r.message.id == message.id
                    and u.id == ctx.message.author.id,
                )
            except asyncio.TimeoutError:
                try:
                    await message.clear_reactions()
                finally:
                    return
            else:
                try:
                    await neko_commands.try_delete(message)
                    await neko_commands.try_delete(ctx)
                finally:
                    return

        # noinspection PyAsyncCall
        asyncio.create_task(later())

    @neko_commands.command(name="dependencies", aliases=["deps"], brief="See what makes Nekozilla tick!")
    async def dependencies_command(self, ctx):
        async with ctx.typing():
            self.logger.info("Inspecting dependencies")
            p = commands.Paginator()
            dependency_string = self.dependencies
            for line in dependency_string.split("\n"):
                p.add_line(line)
            for page in p.pages:
                asyncio.create_task(ctx.send(page))

    @neko_commands.command(name="invite", brief="Sends an invite to let you add the bot to your server.")
    async def invite_command(self, ctx):
        await ctx.send(f"{ctx.author.mention}: {ctx.bot.invite}")


def setup(bot):
    bot.add_cog(BasicCommandsCog(bot))
