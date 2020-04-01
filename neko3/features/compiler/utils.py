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
Other utility bits and pieces.
"""
import asyncio
import io
import re

from PIL import Image

from neko3 import neko_commands
from neko3 import pagination

__inline_block = r"`([^\s`][^`]*?)`"

# Matches the file name and source in a block formatted like so.
#
# `foobar.py`
# ```python
# def foobar():
#     return baz
# ```
#
# ... language is ignored
__fnab = r"`((?:[^.\s\\/`][^`\\/]*){1}?)`" r"\s*```(?:[a-zA-Z0-9]+)?\s([\s\S(^\\`{3})]*?)\s*```"
__highlighted_block = r"```([a-zA-Z0-9]+)\s([\s\S(^\\`{3})]*?)\s*```"

__one_two_highlighted_block = r"(?:```([a-zA-Z0-9]+)\s([\s\S(^\\`{3})]*?)\s*```){1,2}"

# TODO: rename to python_block
__largest_maybe_highlighted_block = r"```([\s\S(^\\`{3})]*)\s*```"

# Used to detect code blocks.
code_block_re = re.compile(__highlighted_block)

# Used for QuickLatex
one_two_code_block_re = re.compile(__one_two_highlighted_block)

largest_block_re = re.compile(__largest_maybe_highlighted_block)

# A general inline block
inline_block_re = re.compile(__inline_block)

# Detects a backticked filename
file_name_and_block_re = re.compile(__fnab)

# Used to detect four-space indentation in Makefiles so that they can be
# replaced with tab control characters.
four_space_re = re.compile(r"^ {4}")


def fix_makefile(input_code: str) -> str:
    """
    Fixes makefiles so they actually compile. This converts any leading
    quadruple spaces on a line to a horizontal tab character.
    :param input_code: the input string.
    :return: the makefile-friendly string.
    """
    strings = []
    for line in input_code.splitlines():
        while four_space_re.match(line):
            line = four_space_re.sub("\t", line)
        strings.append(line)
    return "\n".join(strings)


async def start_and_listen_to_edit(ctx, booklet: pagination.BaseNavigator = None, *additional_messages):
    # Lets the book start up first, otherwise we get an error. If
    # we cant send, then just give up.
    booklet.start()

    for _ in range(0, 60):
        try:
            await asyncio.sleep(1)

            async def custom_delete():
                try:
                    booklet.kill(action=pagination.CancelAction.REMOVE_ALL_SENT_MESSAGES)
                except Exception:
                    pass

                for m in additional_messages:
                    ctx.bot.loop.create_task(m.delete())

            await neko_commands.wait_for_edit(
                ctx=ctx, msg=booklet.root_message, timeout=1800, custom_delete=custom_delete
            )
        except IndexError:
            # The booklet has not initialised yet!
            continue
        else:
            break


def padding_pct_width(width):
    if width > 800:
        return width + 100
    else:
        return width + max(width * 0.15, padding_min_width)


def padding_pct_height(height):
    if height > 800:
        return height + 100
    else:
        return height + max(height * 0.15, padding_min_width)


padding_min_width = 50  # pixels


def latex_image_render(in_img, bg_colour=(0xFF, 0xFF, 0xFF, 0xFF)):
    if isinstance(in_img, bytes):
        in_img = io.BytesIO(in_img)
        in_img.seek(0)

    old_img: Image.Image = Image.open(in_img)
    new_w = int(padding_pct_width(old_img.width))
    new_w = max(new_w, padding_min_width)
    new_h = int(padding_pct_height(old_img.height))
    new_x = int((new_w - old_img.width) / 2)
    new_y = int((new_h - old_img.height) / 2)
    out_img = io.BytesIO()
    new_img = Image.new("RGBA", (new_w, new_h), (0x0, 0x0, 0x0, 0x0))
    new_img.paste(old_img, (new_x, new_y))
    non_transparent = Image.new("RGBA", (new_w, new_h), bg_colour)
    new_img = Image.alpha_composite(non_transparent, new_img)
    new_img.save(out_img, "PNG")
    out_img.seek(0)
    return out_img.getvalue()
