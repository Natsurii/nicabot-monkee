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
Cog providing the LaTeX commands.
"""
import io

import discord

import neko3.cog
from neko3 import neko_commands
from neko3.features.compiler import utils

# URL endpoint to use.
end_point = "http://latex.codecogs.com/"

# Rendering engines
engines = {"png", "gif", "pdf", "swf", "emf", "svg"}

# Additional arguments to alter font size.
sizes = {5: "\\tiny ", 9: "\\small ", 10: "", 12: "\\large ", 18: "\\LARGE ", 20: "\\huge "}

# Fonts available.
fonts = {
    "Latin Modern": "",
    "Verdana": "\\fn_jvn ",
    "Comic Sans": "\\fn_cs ",
    "Computer Modern": "\\fn_cm ",
    "Helvetica": "\\fn_phv ",
}

# Background colours.
backgrounds = {
    "transparent": "",
    "black": "\\bg_black ",
    "white": "\\bg_white ",
    "red": "\\bg_red ",
    "green": "\\bg_green ",
    "blue": "\\bg_blue ",
}


class TeXCog(neko3.cog.CogBase):
    @neko_commands.command(
        name="tex",
        aliases=["latex", "texd", "latexd"],
        brief="Attempts to parse a given LaTeX string and display a preview.",
    )
    async def tex_command(self, ctx, *, content: str):
        """
        Add the `d` prefix to the command to delete your message before the
        response is shown.
        """
        delete = ctx.invoked_with.endswith("d")

        content_matcher = utils.code_block_re.match(content)
        if content_matcher:
            content = content_matcher.group(2)

        if delete:
            await neko_commands.try_delete(ctx)

        async with ctx.typing():
            msg = await self.get_send_image(ctx, content)

        if not delete:
            await neko_commands.wait_for_edit(ctx=ctx, msg=msg, timeout=1800)

    @staticmethod
    def generate_url(
        content,
        *,
        engine: str = "png",
        size: int = 12,
        font: str = "Latin Modern",
        bg_colour: str = "transparent",
        fg_colour: str = "white",
        dpi: int = 200,
    ) -> str:
        """
        Generates the URL containing the LaTeX preview for the given content.
        :param content: content to render.
        :param engine: the rendering engine to use. Must be in the
        ``engines`` set.
        :param size: default size. Must be in the ``sizes`` dict.
        :param font: default font. Must be in the ``fonts`` dict.
        :param bg_colour: default background colour. Must be in the
        ``backgrounds``
            dict.
        :param fg_colour: default text colour name. Refer to
            https://en.wikibooks.org/wiki/LaTeX/Colors
            #The_68_standard_colors_known_to_dvips
            for acceptable values. This is case sensitive, for at least some
            of the
            time.
        :param dpi: default dots per inch. Must be a non-zero positive integer.
        :returns: a formatted URL pointing to the image resource.
        """
        if engine not in engines:
            raise ValueError(f"Invalid engine {engine}. Valid engines are " f'{", ".join(engines)}')
        elif size not in sizes:
            raise ValueError(f"Invalid size {size}. Valid sizes are {list(sizes.keys())}")
        elif font not in fonts:
            raise ValueError(f"Invalid font {font}. Valid fonts are " f'{", ".join(list(fonts))}')
        elif bg_colour not in backgrounds:
            raise ValueError(f"Invalid background {bg_colour}. Valid colours are " f'{", ".join(list(backgrounds))}')
        elif dpi <= 0:
            raise ValueError("DPI must be positive.")
        else:

            def sanitise(string):
                string = string.replace(" ", "&space;")
                string = string.replace("\n", "&space;")
                return string

            raw_str = ""
            raw_str += sanitise(f"\\dpi{{{dpi}}}")
            raw_str += sanitise(f"{backgrounds[bg_colour]}")
            raw_str += sanitise(f"{fonts[font]}")
            raw_str += sanitise(f"{sizes[size]}")
            raw_str += sanitise(f"\\color{{{fg_colour}}} {content}")

            return f"{end_point}{engine}.latex?{raw_str}"

    async def pad_convert_image(self, in_img: io.BytesIO, bg_colour: tuple):
        """
        Takes input image bytes and constructs the image in memory in a
        CPU worker. We then add a padded border around the edge of the image
        and stream it back into the given output bytes IO object. We do this
        as the default rendered LaTeX has no border, and on a contrasting
        background this can look awkward and is harder to read.

        This assumes both the input and output are to be PNG format.

        EDIT: this has to be done on a Thread, not a Process. We cannot pickle
        BytesIO objects.
        """

        return await self.run_in_process_pool(utils.latex_image_render, [in_img, bg_colour])

    async def get_send_image(self, ctx, content: str) -> discord.Message:
        # Append a tex newline to the start to force the content to
        # left-align.
        url = self.generate_url(f"\\\\{content}", size=10)

        async with self.acquire_http_session() as conn:
            async with conn.get(url) as resp:
                resp.raise_for_status()
                data = await resp.read()

        with io.BytesIO(data) as in_data:
            in_data.seek(0)
            out_data = io.BytesIO(await self.pad_convert_image(in_data, (0x36, 0x39, 0x3E)))
            out_data.seek(0)
            file = discord.File(out_data, "latex.png")

            msg = await ctx.send(content=f"{ctx.author}:", file=file)

            return msg
