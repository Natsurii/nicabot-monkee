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
Converts to-and-from ASCII to unsigned big-endian binary.
"""
import math

from neko3 import neko_commands

aliases = {
    "bin": 2,
    "binary": 2,
    "2s": 2,
    "twos": 2,
    "tri": 3,
    "oct": 8,
    "octal": 8,
    "eight": 8,
    "denary": 10,
    "dec": 10,
    "decimal": 10,
    "ten": 10,
    "hex": 16,
    "hexadecimal": 16,
    "sixteen": 16,
}


def to_base_str(n, base):
    """Converts a number n into base `base`."""
    convert_string = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    if n < base:
        return convert_string[n]
    else:
        return to_base_str(n // base, base) + convert_string[n % base]


class ASCIIConversionCog(neko_commands.Cog):
    @neko_commands.command(name="base", brief="Converts between bases.", usage="<from base> <to base> <value>")
    async def base_group(self, ctx, *, query):
        """
        Expects the input base as the first argument, the output base as the second
        argument, and the value to convert as the third. Only supports upto base 36.
        """
        values = query.replace(",", "").replace(" to", "").split(" ")

        if len(values) < 3 or len(values) > 3:
            return await ctx.send("Expected exactly three arguments.", delete_after=10)

        from_base, to_base, value = values[0], values[1], values[2]

        try:
            if not from_base.isdigit():
                from_base = aliases[from_base.lower()]
            else:
                from_base = int(from_base)

            if not to_base.isdigit():
                to_base = aliases[to_base.lower()]
            else:
                to_base = int(to_base)

            if not all(0 < x <= 36 for x in (from_base, to_base)):
                return await ctx.send("Bases must be greater than zero and less or equal to 36.")
        except KeyError as ex:
            nb = " "
            # Prevent @everyone exploits.
            return await ctx.send(f"I didn't recognise the base {str(ex).replace('@', '@' + nb)!r}" f"...")

        try:
            value = abs(int(value, from_base))
        except ValueError as ex:
            return await ctx.send(f"Error: {ex}.")

        await ctx.send(to_base_str(value, to_base) or "0")

    @neko_commands.command(name="ascii2bin", brief="Converts the ASCII string to binary.", aliases=["a2b"])
    async def convert_ascii_to_binary_command(self, ctx, *, string):
        """
        Any UTF-8 characters are removed.
        """
        if string == "^":
            prev = await self._get_previous_message(ctx)
            if not prev:
                return
            else:
                string = prev.content

        return await self.ascii_to_binary(ctx, string=string)

    @neko_commands.command(name="bin2ascii", brief="Converts the binary string to ASCII.", aliases=["b2a"])
    async def convert_binary_to_ascii_command(self, ctx, *, string):
        if string == "^":
            prev = await self._get_previous_message(ctx)
            if not prev:
                return
            else:
                string = prev.content

        return await self.binary_to_ascii(ctx, string=string)

    @staticmethod
    async def ascii_to_binary(ctx, *, string):
        string = "".join(c for c in string if 0 <= ord(c) < 0xFFFF)

        if not string:
            return await ctx.send("No valid ASCII characters given.", delete_after=10)

        binaries = [bin(ord(c))[2:11].rjust(8, "0") for c in string]

        await ctx.send(" ".join(binaries).replace("@", "@" + chr(0xFFF0)))

    @staticmethod
    async def binary_to_ascii(ctx, *, string):
        string = "".join(c for c in string if c not in " \t\r\n")
        if not all(c in "01" for c in string):
            print(string)
            return await ctx.send("Not binary input...", delete_after=10)

        zeros = math.ceil(len(string) / 8)
        string = string.rjust(zeros, "0")

        chars = []
        for i in range(0, len(string), 8):
            chars.append(chr(int(string[i : i + 8], 2)))

        text = "".join(chars)
        await ctx.send(text)

    @staticmethod
    async def _get_previous_message(ctx):
        # Get the previous message.
        history = await ctx.channel.history(limit=3).flatten()

        try:
            # Sometimes discord bugs out and sends the message we just sent; other times it wont...
            for i, m in enumerate(list(history)):
                if m.id == ctx.message.id:
                    del history[i]

        except ValueError:
            pass

        if len(history) < 2 or not history[-1].content:
            await ctx.send("I can't seem to find a message...", delete_after=10)
            return None
        else:
            return history[0]


def setup(bot):
    bot.add_cog(ASCIIConversionCog())
