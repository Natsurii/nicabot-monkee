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
Uses webhooks to substitute Discord-style binds such as `/shrug` into messages
sent from Android devices without the substitution available.
"""
import random
import re

import discord
from discord.ext import commands

import neko3.cog
from neko3 import neko_commands
from neko3 import pagination
from neko3 import string
from neko3 import theme


class BindsCog(neko3.cog.CogBase):
    """
    If the bot used can make webhooks, if a message containing /shrug
    is sent, or one of the other discord binds, then the bot will delete
    the message, produce a webhook that imitates the user, and then resend
    the message in the corrected state. This "kinda" allows users on mobile
    to use desktop binds.
    """

    webhook_avatar_res = 64

    # TODO: move to a config file
    raw_binds = {
        "shrug|meh": "¯ヽ_(ツ)\\_ノ¯",
        "tableflip|flip": ("(╯°□°）╯︵ ┻━┻", "(ノಠ益ಠ)ノ︵ ┻━┻", "ノ┬─┬ノ ︵ ( \\o°o)"),
        "unflip|putback": "┬──┬ ノ(° - °ノ)",
        "angry": ("(ᗒᗣᗕ)", "(งಠᗝಠ)ง", "୧༼ಠ益ಠ༽︻╦╤─"),
        "lenny": ("( ͡° ͜ʖ ͡°)", "( • ͜ʖ • )"),
        "simplelenny": "° ◡ ͡°",
        "heh": "ಠᴗಠ",
        "confused|wut|wtf": ("(⊙＿☉)", "(⊙.☉)7", "(⊙.⊙)", "ಠ▃ಠ"),
        "wizard|zap": "(∩ >-<)⊃━☆ﾟ.*･｡ﾟ",
        "happy": ("(　＾∇＾)", "( ^◡^)"),
        "dancing": ("(∼‾▿‾)∼", "(ノ^o^)ノ", "(ﾉ≧∀≦)ﾉ", "∼(‾▿‾)∼", "ヾ(-_- )ゞ"),
        "yay|excited": ("(ง^ᗜ^)ง", "\\(^~^)/", "(๑>ᴗ<๑)"),
        "ayy": "(☞⌐■\\_■)☞",
        "ahh": "(ʘᗝʘ)",
        "spy": ("┬┴┬┴┤ ͜ʖ ͡°) ├┬┴┬┴", " ┤¬ ͜ ¬) ├┬┴┬┴"),
        "cry|sad": ("(πᗣπ)", "o(╥﹏╥)o", ".·´¯`(>▂<)´¯`·.", "(╥_╥)", "ლ(╥﹏╥ლ)", "щ(ಥДಥщ)"),
        "shy": "（⌒▽⌒ゞ",
        "creep": "ԅ(≖‿≖ԅ)",
        "kiss": ("(づ￣ ³￣)づ", "( ˘ ³˘)♥"),
        "love": "꒰˘̩̩̩⌣˘̩̩̩๑꒱♡",
        "wtf": "ლ(ಠ_ಠლ)",
        "moustache": "( ˇ෴ˇ )",
        "cat": "(=ↀωↀ=)",
        "wave": "( ￣▽￣)/",
        "salute": "(￣^￣)ゞ",
        "strong": "ᕙ(⇀‸↼‶)ᕗ",
        "smart": "f(ಠ‿↼)z",
        "highfive": "( ⌒o⌒)人(⌒-⌒ )v",
        "takemymoney": "(╯°□°）╯$ $ $",
        "derp": "ヽ(。_°)ノ",
        "damnkids": "(•̀o•́)ง",
        "bat": "(/╰^._.^╯\\)",
        "squid": "くコ:彡",
        "running": "৫(”ړ৫)˒˒˒˒",
        "endure": "(҂◡_◡) ᕤ ",
        "whatreyoulookingat": "(づ ͠°‸ °)づ",
        "glassesoff": "( •_•)>⌐■-■",
        "wink": "( ͡~ ͜ʖ ͡°)",
    }

    binds = {
        re.compile(f"(?:^|(?<=[^A-Za-z/0-9]))/({k})(?:$|(?=[^A-Za-z/0-9]))", re.I): v
        for k, v in sorted(raw_binds.items(), key=str)
    }

    @staticmethod
    def scrub(content):
        return content.replace("\N{GRAVE ACCENT}" * 3, "\N{MODIFIER LETTER GRAVE ACCENT}" * 3)

    @commands.guild_only()
    @neko_commands.command(name="binds", brief="Shows available binds.")
    async def view_binds_command(self, ctx):
        if ctx.guild.me.guild_permissions.manage_webhooks:

            @pagination.embed_generator(max_chars=2048)
            def generator(_, page, __):
                return theme.generic_embed(ctx, description=page)

            binder = pagination.StringNavigatorFactory(
                max_lines=10, prefix="```", suffix="```", substitutions=[self.scrub]
            )

            for bind_command, value in self.raw_binds.items():
                bind_command = bind_command.replace("|", ", ")
                if isinstance(value, tuple):
                    value = ", ".join(value)

                binder.add_line(f"{bind_command}: {value}")
            binder.start(ctx)
        else:
            await ctx.send(
                "I don't seem to have the MANAGE_WEBHOOKS "
                "permission required for this to work. Please "
                "grant me that "
            )

    @classmethod
    async def delete_and_copy_handle_with_webhook(cls, message):
        async with cls.acquire_http_session() as http:

            channel: discord.TextChannel = message.channel
            author: discord.User = message.author

            # Use bit inception to get the avatar.
            avatar_url = author.avatar_url_as(format="png", size=cls.webhook_avatar_res)

            avatar_resp = await http.get(str(avatar_url))

            name = message.author.display_name
            if len(name) < 2:
                # Webhook length restriction.
                name = str(message.author)

            # noinspection PyUnresolvedReferences
            wh: discord.Webhook = await channel.create_webhook(name=name, avatar=await avatar_resp.read())

            try:
                await message.delete()
            except Exception:
                pass
            finally:
                await wh.send(content=message.content)
                await wh.delete()

    @neko_commands.Cog.listener()
    async def on_message(self, message):
        """
        On message, check for any binds. If we have a valid bind, first
        check to see whether we can make webhooks or not. If we can, we should
        generate a webhook that impersonates the user context.
        """
        author = message.author
        ctx = await self.bot.get_context(message)

        # Cases where we should refuse to run.
        if message.guild is None:
            return

        if re.match(r"/nick\b", message.content):
            try:
                await message.delete()
                nick = message.content[5:].lstrip() or None
                await author.edit(nick=nick)
                return await message.channel.send("\N{OK HAND SIGN}", delete_after=5)
            except Exception as ex:
                return await message.channel.send(str(ex), delete_after=5)

        if not message.guild.me.guild_permissions.manage_webhooks or author.bot:
            return

        has_matched = False

        for matched_bind, replacements in self.binds.items():
            # If we matched a bind, remove it.

            if matched_bind.search(message.content):
                has_matched = True
                if isinstance(replacements, tuple):
                    replacement = random.choice(replacements)
                else:
                    replacement = replacements
                message.content = matched_bind.sub(replacement, message.content)

        if has_matched:
            message.content = string.trunc(message.content)
            message.content = await commands.clean_content().convert(ctx, message.content)
            await self.delete_and_copy_handle_with_webhook(message)


def setup(bot):
    bot.add_cog(BindsCog(bot))
