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
Provides autorole functionality for hard-coded guilds if we are in them.
"""
import asyncio
import collections
import logging

import discord
from discord.ext import commands


# `Predicate` is a bipredicate consuming a role and a member object.
AutoRole = collections.namedtuple("AutoRole", "role_id predicate")


GUILDS_TO_ROLES = {
    # `hikari'
    574921006817476608: [
        # `Members' role to non-bots who join.
        AutoRole(645576224906805250, lambda r, m: not m.bot)
    ]
}


class AutoRoleCog(commands.Cog):
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    @commands.Cog.listener()
    async def on_member_join(self, member_obj):
        if member_obj.guild.id in GUILDS_TO_ROLES:
            self.ensure_roles(member_obj)

    @commands.Cog.listener()
    async def on_guild_available(self, guild_obj):
        if guild_obj.id in GUILDS_TO_ROLES:
            self.logger.info("Checking members roles in %s", guild_obj)
            # https://github.com/Rapptz/discord.py/issues/2473
            # // async for member_obj in guild_obj.fetch_members(limit=None):
            for member_obj in guild_obj.members:
                self.ensure_roles(member_obj)
            self.logger.info("Finished looking up roles in %s", guild_obj)

    def ensure_roles(self, member_obj):
        guild_obj = member_obj.guild
        for role_id, predicate in GUILDS_TO_ROLES[guild_obj.id]:
            role_obj = guild_obj.get_role(role_id)

            if role_obj is not None and role_obj not in member_obj.roles and predicate(role_obj, member_obj):
                asyncio.create_task(self.add_role(member_obj, role_obj, guild_obj))

    async def add_role(self, member_obj, role_obj, guild_obj):
        try:
            await member_obj.add_roles(role_obj, reason=f"{__name__}: user did not have role")
        except (discord.Forbidden, discord.HTTPException) as ex:
            self.logger.exception("Failed to add role %s to member %s in guild %s", role_obj, member_obj, guild_obj)
        else:
            self.logger.info("Granted role %s to member %s in guild %s", role_obj, member_obj, guild_obj)


def setup(bot):
    bot.add_cog(AutoRoleCog())
