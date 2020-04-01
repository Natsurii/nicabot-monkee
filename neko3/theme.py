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
Global theme stuff.
"""
import inspect
import random

import discord

from neko3 import __author__
from neko3 import __repository__
from neko3 import embeds

# DEPRECATED, but I can't be bothered to sit and work out where it comes from right
# now, so it stays here.
COLOUR = 0x363940


def random_colour():
    return random.choice((
        0x373b3e,
        0xbec8d1,
        0x86cecb,
        0x137a7f,
        0xe12885,
    ))


def generic_embed(ctx, *args, colour=random_colour, avatar_injected=False, **kwargs):
    if inspect.isfunction(colour):
        colour = colour()

    e = embeds.Embed(*args, colour=colour, **kwargs)
    author = __author__
    owner_user = discord.utils.get(ctx.bot.users, id=ctx.bot.owner_id)
    if owner_user:
        owner = f"(@{owner_user})"
        author_str = f"N³, by {author} {owner}"
        author_icon = str(owner_user.avatar_url)
        author_url = __repository__
        e.set_author(name=author_str, url=author_url, icon_url=author_icon)

    if avatar_injected:
        e.set_thumbnail(url=ctx.bot.user.avatar_url_as(static_format="png"))
    return e
