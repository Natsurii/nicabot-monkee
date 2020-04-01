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
Steals an emoji.
"""
import asyncio
import io
import re
import typing

import aiohttp
import discord
from discord.ext import commands

import neko3.cog
from neko3 import neko_commands
from neko3 import pagination
from neko3 import string
from neko3 import theme

static_re = re.compile(r"<:([^:]+):(\d+)>")
animated_re = re.compile(r"<a:([^:]+):(\d+)>")


class EmojiCog(neko3.cog.CogBase):
    @staticmethod
    async def find_emojis(channel, limit):
        animated, static, message = [], [], None

        async for message in channel.history(limit=limit):
            animated.extend(animated_re.findall(message.content))
            static.extend(static_re.findall(message.content))

            if animated or static:
                break

        return animated, static, message

    @neko_commands.command(
        name="steal", brief="Steals emojis and sends to your inbox", aliases=["loot", "swag", "pinch", "nick"]
    )
    async def steal_emoji_command(self, ctx, *, message=None):
        """
        Takes a message ID for the current channel, or if not, a string message containing
        the emojis you want to steal. If you don't specify anything, I look through the
        past 200 messages. Using `^` will have the same effect, and mostly exists for legacy
        and/or muscle memory with other commands.
        
        I get all custom emojis in the message and send them to your inbox with links; this
        way, you can download them or add them to your stamp collection or whatever the hell
        you do for fun.
        
        Teach those Nitro users no more big government. Break their hearts out. FINISH THEM.
        VIVA LA REVOLUTION!
        """
        if not message or message == "^":
            animated, static, new_message = await self.find_emojis(ctx.channel, 1000)
        else:
            new_message = None

            try:
                new_message = await ctx.channel.fetch_message(int(message))
            except Exception:
                new_message = ctx.message
            finally:
                animated = animated_re.findall(new_message.content)
                static = static_re.findall(new_message.content)

        if not static and not animated or not new_message:
            return await ctx.send("No custom emojis could be found...", delete_after=10)

        paginator = pagination.Paginator(enable_truncation=False)

        paginator.add_line(f"Emoji loot from {new_message.jump_url}")
        paginator.add_line()

        for name, id in static:
            paginator.add_line(f" ⚝ {name}: https://cdn.discordapp.com/emojis/{id}.png")

        for name, id in animated:
            paginator.add_line(f" ⚝ {name}: https://cdn.discordapp.com/emojis/{id}.gif <animated>")

        async with ctx.typing():
            for page in paginator.pages:
                await ctx.author.send(page)

        tot = len(animated) + len(static)
        await ctx.send(f'Check your DMs. You looted {tot} emoji{"s" if tot - 1 else ""}!', delete_after=7.5)
        try:
            await ctx.message.delete()
        except Exception:
            pass

    @commands.guild_only()
    @neko_commands.command(
        name="bigemoji", brief="Sends the URL for an emoji so you can see it, copy it, or download it."
    )
    async def big_emoji_command(self, ctx, *, emoji: discord.Emoji):
        emoji_url = str(emoji.url)
        async with ctx.typing():
            async with aiohttp.ClientSession() as session:
                async with session.get(emoji_url) as resp:
                    resp.raise_for_status()
                    data = await resp.read()

            self.logger.debug("Fetching %s emoji", emoji_url)
            data = io.BytesIO(data)
            data.seek(0)

            await ctx.send(emoji.name, file=discord.File(data, f"{emoji.name}.{emoji_url}"))

    @staticmethod
    def transform_mute(emojis):
        return [str(emoji) + " " for emoji in emojis]

    @staticmethod
    def transform_verbose(emojis):
        return [f"{emoji} = {emoji.name}\n" for emoji in sorted(emojis, key=lambda e: e.name.lower())]

    @neko_commands.command(name="emojilibrary", aliases=["emojis", "emotes", "emotelibrary"])
    async def emoji_library_command(self, ctx, arg=None):
        """Shows all emojis I can see ever. Pass the --verbose/-v flag to see names."""
        if arg:
            transform = self.transform_verbose
        else:
            transform = self.transform_mute

        emojis = transform(ctx.bot.emojis)

        p = pagination.StringNavigatorFactory()
        for emoji in emojis:
            p += emoji

        p.start(ctx)

    @neko_commands.command(name="searchemoji", aliases=["search", "emote", "emoji"])
    async def search_emoji_command(self, ctx, emoji: discord.Emoji):
        """Gets an emoji I can see from any guild I am in..."""
        embed = theme.generic_embed(ctx, title=emoji.name, description=str(emoji), url=emoji.url)
        embed.set_footer(text=str(emoji.guild))
        embed.set_image(url=emoji.url)
        await ctx.send(embed=embed)

    @staticmethod
    def sanitise_emoji_name(emoji_obj):
        if not isinstance(emoji_obj, str):
            emoji_obj = emoji_obj.name

        return f'`:{emoji_obj.replace("`", "ˋ")}:`'

    @commands.guild_only()
    @commands.bot_has_permissions(manage_guild=True)
    @commands.has_permissions(manage_guild=True)
    @neko_commands.group(name="addemoji", brief="Uploads an emoji to the server, if you have permission.")
    async def add_emoji_command(self, ctx, name, *, url: typing.Union[discord.Emoji, str]=None):
        """
        If an attachment is given, then I will upload that. If you instead give a URL to an image,
        then I will use that.
        """
        try:
            async with ctx.typing():
                if ctx.message.attachments and url is None:
                    file_url = ctx.message.attachments[0].url
                elif isinstance(url, discord.Emoji):
                    id = url.id
                    ext = "gif" if url.animated else "png"
                    file_url = f"http://cdn.discordapp.com/emojis/{id}.{ext}"
                elif isinstance(url, str):
                    file_url = url
                else:
                    return await ctx.send("Please upload an image first, specify a URL, or give an existing custom emoji.")

                async with self.acquire_http_session() as http:
                    async with http.request("get", file_url) as resp:
                        resp.raise_for_status()
                        content = await resp.read()

                emoji = await ctx.guild.create_custom_emoji(
                    name=name, image=content, reason=f"{ctx.author} added a new emoji using me"
                )

            await ctx.send(f"{self.sanitise_emoji_name(emoji)} ➜ {emoji}")

        except Exception:
            self.logger.exception("Failed to add emoji")
            # todo: remove (debug only)
            raise

    @commands.guild_only()
    @commands.bot_has_permissions(manage_guild=True)
    @commands.has_permissions(manage_guild=True)
    @neko_commands.group(name="removeemoji", brief="Removes emojis from this server, if you have permission.")
    async def remove_emoji_command(self, ctx, emoji: discord.Emoji, *emojis: discord.Emoji):
        """
        Takes one or more emojis to purge.
        """
        successes = 0
        try:
            reason = f"{ctx.author} removed this emoji using me"

            async with ctx.typing():
                for next_emoji in (emoji, *emojis):
                    try:
                        await next_emoji.delete(reason=reason)
                        successes += 1
                        asyncio.create_task(ctx.send(f"{self.sanitise_emoji_name(next_emoji)} ➜ 🗑️"))
                    except:
                        asyncio.create_task(ctx.send(f"Failed to delete {self.sanitise_emoji_name(next_emoji)}..."))
        finally:
            await ctx.send(f'Deleted {string.plur_simple(successes, "emoji")}')

    @commands.guild_only()
    @commands.bot_has_permissions(manage_guild=True)
    @commands.has_permissions(manage_guild=True)
    @neko_commands.group(name="renameemoji", brief="Renames an emoji, if you have permission.")
    async def rename_emoji_command(self, ctx, emoji: discord.Emoji, new_name):
        try:
            reason = f"{ctx.author} renamed this emoji from {emoji} to {new_name} using me"
            await emoji.edit(name=new_name, reason=reason)
            await ctx.send(f"{self.sanitise_emoji_name(emoji)} ➜ {self.sanitise_emoji_name(new_name)}")
        except Exception as ex:
            self.logger.exception("Failed to rename emoji")
            await ctx.send(f"I couldn't do it... {ex}")


def setup(bot):
    bot.add_cog(EmojiCog(bot))
