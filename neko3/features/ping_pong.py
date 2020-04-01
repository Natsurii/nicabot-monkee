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
Ping pong.
"""
import time

from discord.ext import commands

from neko3 import neko_commands
from neko3 import string
from neko3 import theme

PING_CPU_PASSES = 20


class PingPongCog(neko_commands.Cog):
    @commands.cooldown(1, 1, commands.BucketType.default)
    @neko_commands.command(name="ping", aliases=["pong"])
    async def ping_command(self, ctx):
        # Calculate the message-send time. This is the time taken to the response.
        message_send_time = time.perf_counter()

        pong_or_ping = "PING" if ctx.invoked_with == "pong" else "PONG"

        msg = await ctx.send(f"{pong_or_ping}...")
        message_send_time = time.perf_counter() - message_send_time

        heartbeat_latency = ctx.bot.latency

        # Calculate the event loop latency. This is a good representation of how
        # slow the loop is running. We spin the processor up first on the
        # current core to get an accurate measurement of speed when the CPU core
        # is under full load.

        # Time to do a round trip on the event loop, and time to callback.
        end_sync, end_async, end_fn = 0, 0, 0
        sync_latency, async_latency, function_latency = 0, 0, 0

        # Used to measure latency of a task.
        async def coro():
            """
            Empty coroutine that is used to determine the rough waiting time
            in the event loop.
            """
            pass

        # Measures time between the task starting and the callback being hit.
        def sync_callback(_):
            """
            Callback invoked once a coroutine has been ensured as a future.
            This measures the rough time needed to invoke a callback.
            """
            nonlocal end_sync
            end_sync = time.perf_counter()

        def fn_callback():
            """
            Makes a guesstimate on how long a function takes to invoke relatively.
            """
            nonlocal end_fn
            end_fn = time.perf_counter()

        for _ in range(0, 200):
            pass  # Dummy work to spin the CPU up

        for i in range(0, PING_CPU_PASSES):
            start = time.perf_counter()
            async_call = ctx.bot.loop.create_task(coro())
            async_call.add_done_callback(sync_callback)
            await async_call
            end_async = time.perf_counter()

            sync_latency += end_sync - start
            async_latency += end_async - start

            start = time.perf_counter()
            fn_callback()
            function_latency += end_fn - start

        function_latency /= PING_CPU_PASSES
        async_latency /= PING_CPU_PASSES
        sync_latency /= PING_CPU_PASSES

        # We match the latencies with respect to the total time taken out of all
        # of them
        total_ping = 1.05 * (message_send_time + heartbeat_latency)
        total_loop = 1.05 * (async_latency + sync_latency + function_latency)

        message_send_time_pct = message_send_time * 100 / total_ping
        heartbeat_latency_pct = heartbeat_latency * 100 / total_ping
        async_latency_pct = async_latency * 100 / total_loop
        sync_latency_pct = sync_latency * 100 / total_loop
        function_latency_pct = function_latency * 100 / total_loop

        joiner = lambda *a: "\n".join(a)

        pong = joiner(
            "```diff",
            f"+ GATEW: {self.make_progress_bar(heartbeat_latency_pct)} {heartbeat_latency * 1_000: .2f}ms",
            f"-  REST: {self.make_progress_bar(message_send_time_pct)} {message_send_time * 1_000: .2f}ms",
            f"+ STACK: {self.make_progress_bar(function_latency_pct)} {function_latency * 1_000_000: .2f}µs",
            f"- CALLB: {self.make_progress_bar(sync_latency_pct)} {sync_latency * 1_000_000: .2f}µs",
            f"+   AIO: {self.make_progress_bar(async_latency_pct)} {async_latency * 1_000_000: .2f}µs",
            "```",
        )

        embed = theme.generic_embed(ctx, avatar_injected=True, title=pong_or_ping, description=pong)
        embed.set_footer(text=f"{string.plur_simple(ctx.bot.command_invoke_count, 'command')} run since startup")

        await msg.edit(content="", embed=embed)

    @staticmethod
    def make_progress_bar(percent):
        full = "\N{FULL BLOCK}"
        empty = " "
        percent_per_block = 5

        return "".join(full if i < percent else empty for i in range(0, 100, percent_per_block))


def setup(bot):
    bot.add_cog(PingPongCog())
