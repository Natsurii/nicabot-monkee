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
Bits and bobs helpful when making Discord bots I guess.
"""

from discord import utils

from neko3 import neko_commands
from neko3 import permission_bits


class BotUtils(neko_commands.Cog):
    @neko_commands.command(
        name="makeinvite",
        brief="Generates an OAuth invite URL from a given snowflake client ID",
        help="Valid options: ```" + ", ".join(permission_bits.Permissions.__members__.keys()) + "```",
        aliases=["devinvite", "mkinvite"],
    )
    async def generate_invite_command(self, ctx, client_id: str, *permissions: str):
        perm_bits = 0

        for permission in permissions:
            if permission.upper() not in permission_bits.Permissions.__members__.keys():
                return await ctx.send(f"{permission} is not recognised.")
            else:
                perm_bits |= permission_bits.Permissions[permission.upper()]

        try:
            int(client_id)

            await ctx.send(
                utils.oauth_url(
                    client_id, permissions=perm_bits if hasattr(perm_bits, "value") else None, guild=ctx.guild
                )
            )
        except Exception:
            await ctx.send("Please provide a valid client ID")


def setup(bot):
    bot.add_cog(BotUtils())
