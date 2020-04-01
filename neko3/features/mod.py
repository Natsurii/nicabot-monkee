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
Ban/unban users.
"""
import functools
import re

from discord.ext import commands

from neko3 import permission_bits as permissions


class Mention(commands.MemberConverter):
    async def convert(self, ctx, arg):
        try:
            return await super().convert(ctx, arg)
        except Exception as ex:  # Todo
            for id in re.findall(r".*\d+.*", arg):
                try:
                    return await ctx.bot.fetch_user(id)
                except:
                    continue
            raise ex
            


def has_any_perms(member, perm1, *perms):
    actual_perms = permissions.Permissions(member.guild_permissions.value)
    return any(actual_perms & perm for perm in (perm1, *perms))


def both_have_any_perms(perm1, *perms):
    def decorator(command):
        @functools.wraps(command)
        async def wrapper(self, ctx, *args, **kwargs):
            if not has_any_perms(ctx.author, perm1, *perms):
                await ctx.send("You need one of " + ", ".join(perm.name for perm in (perm1, *perms)) + " to do this.")
            elif not has_any_perms(ctx.guild.me, perm1, *perms):
                await ctx.send("I need one of " + ", ".join(perm.name for perm in (perm1, *perms)) + " to do this.")
            else:
                await command(self, ctx, *args, **kwargs)
        return wrapper
    return decorator


class BanCog(commands.Cog):
    @commands.command()
    @commands.guild_only()
    @both_have_any_perms(permissions.Permissions.BAN_MEMBERS, permissions.Permissions.ADMINISTRATOR)
    async def ban(self, ctx, who: Mention, *, reason=None):
        await ctx.guild.ban(who, reason=reason)
        await ctx.send("\N{OK HAND SIGN}", delete_after=10)

    @commands.command()
    @commands.guild_only()
    @both_have_any_perms(permissions.Permissions.BAN_MEMBERS, permissions.Permissions.ADMINISTRATOR)
    async def unban(self, ctx, who: Mention, *, reason=None):
        await ctx.guild.unban(who, reason=reason)
        await ctx.send("\N{OK HAND SIGN}", delete_after=10)

    @commands.command()
    @commands.guild_only()
    @both_have_any_perms(permissions.Permissions.KICK_MEMBERS, permissions.Permissions.ADMINISTRATOR)
    async def kick(self, ctx, who: Mention, *, reason=None):
        await ctx.guild.kick(who, reason=reason)
        await ctx.send("\N{OK HAND SIGN}", delete_after=10)


def setup(bot):
    bot.add_cog(BanCog())
