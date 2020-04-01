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
Various useful operations to use in guilds.
"""
import urllib.parse
from datetime import datetime  # Timestamp stuff
from typing import TYPE_CHECKING

import discord
from discord.ext.commands import errors
from discord.ext.commands.converter import *

# Random colours; Permission help; Logging; String helpers; HTTPS
from neko3 import aggregates
from neko3 import algorithms
from neko3 import cog
from neko3 import embeds
from neko3 import logging_utils
from neko3 import neko_commands
from neko3 import pagination
from neko3 import string
from neko3.converters import *
from neko3.permission_bits import Permissions

if TYPE_CHECKING:

    class PermissionConverter(Permissions):
        pass


else:

    class PermissionConverter(Converter):
        async def convert(self, ctx, argument):
            try:
                argument = argument.upper().replace(" ", "_").replace("SERVER", "GUILD")
                permission = Permissions.__members__[argument]
            except KeyError:
                raise errors.BadArgument(f"{argument} is not a valid permission name")
            else:
                return permission


class InspectionsCog(cog.CogBase, logging_utils.Loggable):
    # noinspection PyMethodMayBeStatic
    async def cog_check(self, ctx):
        """Only allows these to be called in Guilds."""
        return ctx.guild

    @neko_commands.group(
        name="inspect",
        brief="Inspects a given element.",
        examples=["@User#1234", "#channel", "@Role Name"],
        invoke_without_command=True,
        aliases=["in"],
    )
    async def inspect_group(self, ctx, *, obj: MentionOrSnowflakeConverter = None):
        """
        Inspects something by passing a mention. This will not support
        emojis, or anything that is not a valid mention. See the help page
        for all inspection sub-commands if you require parsing a specific
        entity type to be recognised, or cannot mention the entity.
        """
        if obj is None:
            ctx.message.content = f"{ctx.prefix}help {ctx.command}"
            ctx = await ctx.bot.get_context(ctx.message)
            return await ctx.bot.invoke(ctx)

        if isinstance(obj, (int, str)):
            await self.inspect_snowflake_command.callback(self, ctx, snowflakes=str(obj))
        elif isinstance(obj, discord.Member):
            await self.inspect_member_command.callback(self, ctx, member=obj)
        elif isinstance(obj, discord.Role):
            await self.inspect_role_command.callback(self, ctx, role=obj)
        elif isinstance(obj, discord.Emoji):
            await self.inspect_emoji_command.callback(self, ctx, emoji=obj)
        elif isinstance(obj, discord.PartialEmoji):
            await ctx.send(f"You should use `{ctx.prefix}char` for Unicode " "emojis.")
        else:
            try:
                channel = GuildChannelConverter()
                channel = await channel.convert(ctx, ctx.args[0])
                await self.inspect_channel_command.callback(self, ctx, channel=channel)
            except Exception:
                raise errors.BadArgument(
                    "Could not infer argument type." " See `n.help in` for explicit invocation info"
                )

    @staticmethod
    async def is_banned_here(ctx, user_id):
        if not ctx.guild:
            return False

        try:
            bans = [ban.user for ban in await ctx.guild.bans()]
        except discord.Forbidden:
            return False
        else:
            return discord.utils.get(bans, id=user_id)

    @inspect_group.command(name="allperms", brief="Shows a list of all permission names usable " "with this bot.")
    async def inspect_all_permissions_command(self, ctx):
        await ctx.send(
            "**Permissions that this bot understands:**\n\n"
            + ", ".join(f"`{p}`" for p in sorted(Permissions.__members__))
        )

    # noinspection PyUnresolvedReferences
    @inspect_group.group(
        name="avatar",
        brief="Shows the user's avatar.",
        examples=["@user"],
        aliases=["a", "av"],
        invoke_without_command=True,
    )
    async def inspect_avatar_group(self, ctx, *, user: InsensitiveMemberConverter = None):
        """
        If no avatar is specified, then the guild avatar is captured
        instead!
        """
        if user is None:
            user = ctx.author

        # Update the cache.
        colour = getattr(user, "colour", None)
        user = await ctx.bot.fetch_user(user.id)
        avatar_url = str(user.avatar_url)
        url_obj = [*urllib.parse.urlparse(avatar_url)]
        url_obj[2] = url_obj[2][:-5] + ".png" if url_obj[2].endswith(".webp") else url_obj[2]
        avatar_url = f"{url_obj[0]}://{url_obj[1]}{url_obj[2]}?size=2048"
        embed = embeds.Embed(title=f"`@{user}`'s avatar", url=avatar_url)

        if colour is not None:
            embed.colour = colour

        # 11th June 2018 - gifs break everything. Surprise, surprise.
        # Turns out it is the proxy_url that screws stuff up. From fiddling
        # with embed objects in an eval command for this bot, it seems you can
        # specify a custom proxy URL and discord will use it, which is good
        # because by setting the proxy url to the same url as the original,
        # we can usually overcome this issue!
        # noinspection PyProtectedMember
        embed._image = {"url": avatar_url, "proxy_url": avatar_url, "height": 0}

        await ctx.send(f"Member avatar inspection\n<{avatar_url}>", embed=embed)

    @inspect_avatar_group.command(name="guild", aliases=["g"], brief="Gets the guild avatar.")
    async def inspect_guild_avatar(self, ctx):
        embed = embeds.Embed(colour=algorithms.rand_colour())
        embed.set_image(url=str(ctx.guild.icon_url))
        await ctx.send("Guild avatar inspection", embed=embed)

    @inspect_group.command(name="emoji", brief="Inspects an emoji.", aliases=["e"])
    async def inspect_emoji_command(self, ctx, *, emoji: discord.Emoji = None):
        """
        Note that this will only work for custom emojis.
        If no emoji name is provided, we list all emojis available in this
        guild.
        """
        if emoji:

            desc = f'Created on {emoji.created_at.strftime("%c")}\n\n'

            if emoji.animated:
                desc += "Animated emoji\n"
            if emoji.require_colons:
                desc += "Must be wrapped in colons\n"
            if emoji.managed:
                desc += "Managed as part of a Twitch integration\n"
            if not emoji.roles:
                desc += "Emoji is usable by everyone here\n"

            rc = emoji.require_colons

            embed = embeds.Embed(
                title=rc and f"`:{emoji.name}:`" or f"`{emoji}`",
                description=desc,
                url=emoji.url,
                colour=0xAB19CF or emoji.animated and 0xD1851B,
            )

            if emoji.roles:
                embed.add_field(name="Usable by", value=string.trunc(", ".join(map(str, emoji.roles)), 1024))

            embed.set_thumbnail(url=emoji.url)

            embed.set_author(name=f'Emoji in "{emoji.guild}"', icon_url=emoji.url)
            embed.set_footer(text=str(emoji.id), icon_url=emoji.url)
            await ctx.send(embed=embed)
        elif len(ctx.guild.emojis) == 0:
            await ctx.send("This server has no emojis yet...", delete_after=10)
        else:
            binder = pagination.EmbedNavigatorFactory(max_lines=10)

            def key(e_):
                return e_.name

            for i, e in enumerate(sorted(ctx.guild.emojis, key=key)):
                binder.add_line(f"`{i + 1:03}`\t{e} \t `{e}`")

            binder.start(ctx)

    @inspect_group.command(
        name="perms", brief="Shows which roles and which channels explicitly grant a permission", aliases=["p"]
    )
    async def inspect_perms_commamd(self, ctx, *, permission: PermissionConverter):
        results = 0
        nav = pagination.StringNavigatorFactory(prefix="```diff", suffix="```", max_lines=15)

        nav.add_line(f"% Looking for roles and channels that allow {permission.name}")

        nav.add_line(f"+ {ctx.guild.owner} owns the guild so will inherit this permission anyway")

        for role in ctx.guild.roles:
            if permission & role.permissions.value:
                nav.add_line(f'+ Role "{role.name} grants this"')
                results += 1
            if Permissions.ADMINISTRATOR & role.permissions.value and not permission & Permissions.ADMINISTRATOR:
                nav.add_line(f'+ Role "{role.name}" grants ADMINISTRATOR which inherits this')

        if results:
            nav.add_line()

        for channel in ctx.guild.channels:
            for what, overwrite in channel.overwrites.items():
                allow, deny = overwrite.pair()

                target = isinstance(channel, discord.CategoryChannel) and "Category" or "Channel"
                subject = isinstance(what, discord.Role) and "role" or "member"

                if allow.value & permission:
                    nav.add_line(f'+ {target} "{channel.name}" explicitly for {subject} "{what}"')
                    results += 1
                if deny.value & permission:
                    nav.add_line(f'- {target} "{channel.name}" explicitly for {subject} "{what}"')
                    results += 1

        if not results:
            nav.add_line("- No results. Nothing has this permission.")

        nav.start(ctx)

    @inspect_group.command(name="channel", brief="Inspects a given channel.", aliases=["ch", "c"])
    async def inspect_channel_command(self, ctx, *, channel: GuildChannelConverter = None):
        """
        Inspects a channel in this guild. If no channel is given, we check
        the current channel.
        """
        channel = channel or ctx.channel

        category = channel.category
        category = category and category.name.upper() or None

        if isinstance(channel, discord.TextChannel):
            channel: discord.TextChannel

            try:
                wh_count = len(await channel.webhooks())
            except discord.Forbidden:
                wh_count = "I need `MANAGE_WEBHOOKS` first!"

            pin_count = len(await channel.pins())

            try:
                invite_count = len(await channel.invites())
            except discord.Forbidden:
                invite_count = "I need `MANAGE_CHANNELS` first!"

            embed = embeds.Embed(
                title=f"`#{channel.name}`",
                colour=algorithms.rand_colour(),
                description="\n".join(
                    [
                        f"**Type**: {channel.type.name.title()}",
                        f'**Created on**: {channel.created_at.strftime("%c")}',
                        f"**Category**: `{category}`",
                        f"**NSFW**: {string.yn(channel.is_nsfw()).lower()}",
                        f"**Pin count**: {pin_count}",
                        f"**Mention**: {channel.mention}",
                        f"**Webhook count**: {wh_count}",
                        f"**Invitations here**: {invite_count}",
                    ]
                ),
            )

            if channel.topic:
                embed.add_field(name="Topic", value=string.trunc(channel.topic, 1024), inline=False)

            if len(channel.members) == len(ctx.guild.members):
                embed.add_field(name="Accessible by", value="All " + string.plur_simple(len(channel.members), "member"))
            elif len(channel.members) > 10:
                embed.add_field(name="Accessible by", value=f"{len(channel.members)} members")
            elif channel.members:
                embed.add_field(name="Accessible by", value=", ".join(sorted(map(str, channel.members))))
            else:
                embed.add_field(name="Accessible by", value="No one has this role yet!")

            if channel.changed_roles:
                embed.add_field(
                    name="Roles with custom permissions",
                    value=", ".join(str(c) for c in sorted(channel.changed_roles, key=str)),
                )

        else:
            embed = embeds.Embed(
                title=f"`#{channel.name}`",
                colour=algorithms.rand_colour(),
                description="\n".join(
                    [
                        f"**Type**: Voice",
                        f'**Created on**: {channel.created_at.strftime("%c")}',
                        f"**Category**: `{category}`",
                        f"**Mention**: {channel.mention}",
                        f"**Bitrate**: {channel.bitrate / 1000:,.2f}kbps",
                        f"**User limit**: {channel.user_limit or None}",
                    ]
                ),
            )

            if len(channel.members) == len(ctx.guild.members):
                embed.add_field(
                    name="Members in this VC", value="All " + string.plur_simple(len(channel.members), "member")
                )
            elif len(channel.members) > 10:
                embed.add_field(name="Members in this VC", value=f"{len(channel.members)} members")
            elif channel.members:
                embed.add_field(name="Members in this VC", value=", ".join(sorted(map(str, channel.members))))
            else:
                embed.add_field(name="Members in this VC", value="No one is in this VC yet!")

        embed.set_author(name=f"Channel #{channel.position + 1}")
        embed.set_footer(text=str(channel.id))
        await ctx.send("Channel inspection", embed=embed)

    @inspect_group.group(name="guild", brief="Inspects this guild.", aliases=["server", "g", "s"])
    async def inspect_guild_group(self, ctx):
        """
        Gives details regarding the current guild.
        """
        guild = ctx.guild
        bot_members = len([*filter(lambda m: m.bot, guild.members)])
        human_members = len(guild.members) - bot_members
        categories = len(guild.categories)
        txt_channels = len([*filter(lambda c: isinstance(c, discord.TextChannel), guild.channels)])
        nsfw = sum(True for c in guild.text_channels if c.nsfw)
        vcs = len(guild.channels) - categories - txt_channels

        if guild.afk_timeout:
            afk_timeout = divmod(guild.afk_timeout // 60, 60)
            afk_timeout = f"{afk_timeout[0]} hours, {afk_timeout[1]} minutes"
        else:
            afk_timeout = "none"

        cock_block = ctx.guild.explicit_content_filter

        embed = embeds.Embed(
            title=guild.name,
            colour=algorithms.rand_colour(),
            description="\n".join(
                [
                    f"**Members**: {len(guild.members)} ({bot_members} bots, " f"{human_members} humans)",
                    f'**Created on**: {guild.created_at.strftime("%c")}',
                    f"**Roles**: {len(guild.roles)}",
                    f"**Emojis**: {len(guild.emojis)}",
                    f"**Owner**: {guild.owner}",
                    f'**Region**: {str(guild.region).replace("_", " ").title()}',
                    f"**Channels**: {len(guild.channels)}",
                    f"    {txt_channels} text channels (of which {nsfw} are NSFW)",
                    f"    {vcs} voice channels",
                    f"    {categories} categories",
                    f"**AFK channel**: {guild.afk_channel or 'none'} (timeout: {afk_timeout})",
                    f'**System channel**: {guild.system_channel or "none"}',
                    f'**Is chunked**: {guild.chunked and "yes" or "no"}',
                    f"**Content filter**: {cock_block}",
                    f'**Verification level**: {str(guild.verification_level).replace("_", " ").title()}',
                    f'**Enforces MFA**: {guild.mfa_level and "yes" or "no"}',
                    f'**Is large**: {guild.large and "yes" or "no"}',
                ]
            ),
        )

        if guild.features:
            embed.add_field(name="Special features", value=", ".join(map(str.title, map(str, guild.features))))

        if guild.shard_id is not None:
            embed.add_field(name="Shard ID", value=str(guild.shard_id))

        embed.set_thumbnail(url=guild.icon_url)

        embed.set_footer(text=str(guild.id))

        await ctx.send(embed=embed)

    @inspect_guild_group.command(name="roles", brief="Inspects this guild's roles.", aliases=["r"])
    async def inspect_guild_roles(self, ctx):
        """
        Shows a list of roles in this guild.
        """
        @pagination.embed_generator(max_chars=1000)
        def embed_generator(_, page, __):
            e = embeds.Embed(
                title=ctx.guild.name,
                description = page,
            )

            e.set_thumbnail(url=ctx.guild.icon_url)
            e.set_footer(text=str(ctx.guild.id))
            return e

        pages = pagination.EmbedNavigatorFactory(factory=embed_generator)
        for i, role in enumerate(ctx.guild.roles, start=1):
            pages.add_line(f"{i}. {role} ({role.id})")
        
        pages.start(ctx)

    @inspect_group.command(name="category", brief="Inspects a given category.", aliases=["ca", "cat"])
    async def inspect_category_command(self, ctx, *, category: LowercaseCategoryConverter = None):
        """
        If no category is provided, and we are in a valid category, we will
        inspect that, otherwise, you need to provide me with a valid category
        snowflake or name.
        """
        if category is None:
            if ctx.channel.category is None:
                raise commands.MissingRequiredArgument("category")
            else:
                category = ctx.channel.category

        embed = embeds.Embed(
            title=f"`{category.name.upper()}`",
            colour=algorithms.rand_colour(),
            description="\n".join(
                [
                    f'**Created on**: {category.created_at.strftime("%c")}',
                    f"**NSFW**: {string.yn(category.is_nsfw()).lower()}",
                ]
            ),
        )

        if category.changed_roles:
            embed.add_field(
                name="Roles with custom permissions",
                value=", ".join(str(c) for c in sorted(category.changed_roles, key=str)),
            )

        channels = sorted(map(lambda c: c.name, category.channels))

        if channels:
            c_string = ""
            for channel in channels:
                if c_string:
                    next_substring = f", `{channel}`"
                else:
                    next_substring = f"`{channel}`"

                if len(c_string + next_substring) < 1020:
                    c_string += next_substring
                else:
                    c_string += "..."

            embed.add_field(name="Channels", value=c_string)
        else:
            embed.add_field(name="Channels", value="No channels yet!")

        embed.set_author(name=f"Category #{category.position + 1}")
        embed.set_footer(text=str(category.id))
        await ctx.send("Category inspection", embed=embed)

    @staticmethod
    def _status(s):
        return {
            discord.Status.online: "Online",
            discord.Status.idle: "Away",
            discord.Status.dnd: "Busy",
            discord.Status.invisible: "Hiding",
            discord.Status.offline: "Offline",
        }.get(s, "On Mars")

    @inspect_group.command(name="member", brief="Inspects a given member or user.", aliases=["user", "u", "m"])
    async def inspect_member_command(self, ctx, *, member: InsensitiveMemberConverter = None):
        """
        If no member is specified, then I will show your profile instead.

        This will also show limited information about other members that exist on Discord.
        """
        if member is None:
            member = ctx.author

        embed = embeds.Embed(title=f"`@{member}`", colour=discord.Color.greyple())

        desc = "\n".join(
            [
                f'**Joined Discord on:** {member.created_at.strftime("%c")}',
                f"**Mention:** {member.mention}",
                f'**Account type**: {member.bot and "Bot" or "Human"}',
            ]
        )

        if isinstance(member, discord.Member):
            embed.title += " (member)"

            top_role = member.top_role

            desc += "\n" + "\n".join(
                [
                    f"**Display name:** {member.display_name}",
                    f"**Nickname:** {member.nick}",
                    f'**Joined here on:** {member.joined_at.strftime("%c")}',
                    f"**Top role:** {top_role.mention if top_role.id != ctx.guild.id else top_role}",
                    f"**Colour:** `#{hex(member.colour.value)[2:].zfill(6)}`",
                    f"**Status:** {self._status(member.status)}",
                    f"  Web: {self._status(member.web_status)}",
                    f"  PC: {self._status(member.desktop_status)}",
                    f"  Mobile: {self._status(member.mobile_status)}",
                ]
            )

            embed.colour = member.colour if member.colour != 0 else discord.Colour.greyple()

            if member.roles:
                embed.add_field(
                    name="Roles",
                    value=string.trunc(
                        ", ".join(r.mention if r.id != ctx.guild.id else r.name for r in reversed(member.roles)), 1020
                    ),
                )

            role_perms = Permissions.from_discord_type(member.guild_permissions)
            role_perms = {*role_perms.unmask()}

            chn_perms = member.permissions_in(ctx.channel)
            chn_perms = {*Permissions.from_discord_type(chn_perms).unmask()}

            # Calculate any extra perms granted for this channel only.
            chn_perms.difference_update(role_perms)

            if role_perms:
                role_perms = ", ".join(f"`{p}`" for p in sorted(role_perms, key=str))
            else:
                role_perms = "No role permissions granted (somehow)"

            embed.add_field(name="Role-granted permissions", value=role_perms)

            if member.activity:
                # This design is...not the best imho, but it is confusingly
                # defined in the API:
                # This attr can be a Game, Streaming or Activity, but Activity
                # itself can have a `playing` type which denotes a game, so...
                # how do we know which one to expect? Game is not a subtype
                # of activity nor vice versa!
                if isinstance(member.activity, discord.Activity):
                    a = member.activity

                    attrs = []
                    # Less verbose.
                    z = attrs.append

                    if a.start:
                        z(f'Since: {a.start.strftime("%c")}')
                    if a.end:
                        z(f'Until: {a.end.strftime("%c")}')

                    if a.details:
                        z(f"Details: {a.details}")

                    if a.small_image_text:
                        z(f"Small tooltip: {a.small_image_text}")
                    if a.large_image_text:
                        z(f"Large tooltip: {a.large_image_text}")

                    if not attrs:
                        z(a.name)
                    else:
                        attrs.insert(0, f"Name: {a.name}")

                    t = a.type
                    try:
                        t = "Activity" if t == discord.ActivityType.unknown else t.name.title()
                    except AttributeError:
                        # occurs for custom statuses on old dpy versions
                        t = "Custom activity"

                    embed.add_field(name=t, value="\n".join(attrs))
                elif isinstance(member.activity, discord.Game):
                    embed.add_field(name="Playing", value=member.activity.name)

                elif isinstance(member.activity, discord.Streaming):
                    a = member.activity
                    embed.add_field(
                        name="Streaming", value=f"[{a.twitch_name or a.name}]({a.url})\n" f'{a.details or ""}'
                    )

            if chn_perms:
                chn_perms = ", ".join(f"`{p}`" for p in sorted(chn_perms, key=str))
                embed.add_field(name="Additional permissions in this channel", value=chn_perms)

        else:
            embed.title += " (not a member)"

            if algorithms.find(lambda u: u.id == member.id, ctx.bot.users):
                desc += f"\n**Mutuality**: member in other servers I am in"

            is_banned = await self.is_banned_here(ctx, member.id)
            if is_banned:
                embed.add_field(
                    name="WARNING",
                    value="\N{WARNING SIGN}\N{VARIATION SELECTOR-16} USER IS BANNED HERE \N{WARNING SIGN}\N{VARIATION SELECTOR-16}",
                )

        embed.description = desc
        embed.set_thumbnail(url=str(member.avatar_url))
        embed.set_footer(text=str(member.id), icon_url=str(member.default_avatar_url))

        await ctx.send("Member inspection", embed=embed)

    @inspect_group.command(name="role", brief="Inspects a given role.", examples=["@Role Name"], aliases=["r"])
    async def inspect_role_command(self, ctx, *, role: discord.Role):
        permissions = Permissions.from_discord_type(role.permissions)
        permissions = (f"`{name}`" for name in permissions.unmask())

        desc = f'{role.mention}\n\n{", ".join(sorted(permissions))}'

        embed = embeds.Embed(title=role.name, description=desc, colour=role.colour)

        embed.set_footer(text=str(role.id))

        embed.add_field(name="Can be mentioned by users?", value=string.yn(role.mentionable))
        embed.add_field(name="Will hoist?", value=string.yn(role.hoist))
        embed.add_field(name="Externally managed?", value=string.yn(role.managed))
        embed.add_field(name="Created on", value=role.created_at.strftime("%c"))
        embed.add_field(name="Colour", value=f"`#{hex(role.colour.value)[2:].zfill(6)}`")

        if len(role.members) == len(ctx.guild.members):
            embed.add_field(
                name="Members with this role", value="All " + string.plur_simple(len(role.members), "member")
            )
        elif len(role.members) > 10:
            embed.add_field(name="Members with this role", value=f"{len(role.members)} members")
        elif role.members:
            embed.add_field(name="Members with this role", value=", ".join(sorted(map(str, role.members))))
        else:
            embed.add_field(name="Members with this role", value="No one has this role yet!")

        embed.add_field(
            name="Location in the hierarchy",
            value=f'{string.plur_simple(role.position, "role")} from the '
            f"bottom; {len(ctx.guild.roles) - role.position} from "
            "the top.",
        )

        await ctx.send("Role inspection", embed=embed)

    @inspect_group.command(
        name="snowflake", brief="Deciphers a snowflake.", examples=["439802699144232960"], aliases=["sf"]
    )
    async def inspect_snowflake_command(self, ctx, *, snowflakes: str):
        """You can pass up to 10 snowflakes at once."""
        if not snowflakes:
            return
        snowflake_re = re.compile(r"[^\d]*(\d+)[^\d]*")
        snowflakes = [int(snowflake) for snowflake in snowflake_re.findall(snowflakes)]

        if not snowflakes:
            return await ctx.send("No snowflakes found in that query. Sorry...")

        # Filters out duplicates.
        snowflakes = aggregates.FrozenOrderedSet(snowflakes)

        embed = embeds.Embed(colour=algorithms.rand_colour())

        # Discord epoch from the Unix epoch in ms
        # Essentially the number of milliseconds since epoch
        # at 1st January 2015
        # epoch = 1_420_070_400_000
        for i, snowflake in enumerate(sorted(snowflakes[:10])):
            timestamp = (((snowflake >> 22) & 0x3FFFFFFFFFF) + 1_420_070_400_000) / 1000
            try:
                creation_time = datetime.utcfromtimestamp(timestamp)
            except OverflowError:
                return await ctx.send("Hey, that ain't a valid snowflake buddy.")

            worker_id = (snowflake & 0x3E0000) >> 17
            process_id = (snowflake & 0x1F000) >> 12
            increment = snowflake & 0xFFF

            desc = "\n".join(
                (
                    f"`{creation_time} UTC`",
                    f"**Worker ID**: `{worker_id}`",
                    f"**Process ID**: `{process_id}`",
                    f"**Increment**: `{increment}`",
                )
            )

            # Attempt to resolve the snowflake in all caches where possible
            # and non-intrusive to do so.

            if snowflake == getattr(ctx.bot, "client_id", None):
                desc += "\n- My client ID"

            member = algorithms.find(lambda u: u.id == snowflake, ctx.guild.members)

            if snowflake == ctx.bot.owner_id:
                desc += "\n- My owner's ID"
                member = ctx.bot.get_user(ctx.bot.owner_id)

            if snowflake == ctx.bot.user.id:
                desc += "\n- My user ID"
                member = ctx.bot.user
            elif member:
                desc += f"\n- Member in this guild ({member})"
            else:
                try:
                    if algorithms.find(lambda u: u.id == snowflake, ctx.bot.users):
                        desc += f"\n- A member in another server I am in"
                    else:
                        desc += f"\n- A user I don't share a server with"

                    member = await ctx.bot.fetch_user(snowflake)

                    if hasattr(member, "nick"):
                        desc += f"\n- named {member}, nicked {member.nick}"
                    else:
                        desc += f"\n- named {member}"

                    if await self.is_banned_here(ctx, snowflake):
                        desc += "\n- \N{WARNING SIGN}\N{VARIATION SELECTOR-16}**USER IS BANNED HERE!**\N{WARNING SIGN}\N{VARIATION SELECTOR-16}"
                except discord.NotFound:
                    desc += "\n- Doesn't point to anything valid, unfortunately"

            if not i and member:
                embed.set_thumbnail(url=member.avatar_url)

            emoji = algorithms.find(lambda e: e.id == snowflake, ctx.guild.emojis)

            if emoji:
                desc += f"\n- Emoji in this guild ({emoji})"
            elif algorithms.find(lambda e: e.id == snowflake, ctx.bot.emojis):
                desc += "\n- Emoji in another guild"

            if algorithms.find(lambda c: c.id == snowflake, ctx.guild.categories):
                desc += "\n- Category in this guild"

            if algorithms.find(lambda r: r.id == snowflake, ctx.guild.roles):
                desc += "\n- Role in this guild"

            channel = ctx.bot.get_channel(snowflake)

            if channel:
                if snowflake == ctx.channel.id:
                    desc += f"\n- ID for this channel ({channel})"
                elif algorithms.find(lambda c: c.id == snowflake, ctx.guild.text_channels):
                    desc += f"\n- Text channel in this guild ({channel})"
                elif algorithms.find(lambda c: c.id == snowflake, ctx.guild.voice_channels):
                    desc += f"\n- Voice channel in this guild ({channel})"
                elif algorithms.find(lambda c: c.id == snowflake, ctx.bot.get_all_channels()):
                    desc += "\n- Text or voice channel in another guild"

            if snowflake == ctx.guild.id:
                desc += "\n- ID for this guild"
            elif algorithms.find(lambda g: g.id == snowflake, ctx.bot.guilds):
                desc += "\n- ID for another guild I am in"

            embed.add_field(name=snowflake, value=desc)

        await ctx.send("Snowflake inspection", embed=embed)


def setup(bot):
    bot.add_cog(InspectionsCog(bot))
