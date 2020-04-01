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
NOAA cog implementation.
"""
import io

import discord

import neko3.cog
from neko3 import neko_commands
from neko3 import pagination
from neko3 import theme
from . import utils


class NOAACog(neko3.cog.CogBase):
    @neko_commands.group(name="noaa", brief="Gets info from NOAA regarding US weather.")
    async def noaa_group(self, ctx):
        return await neko_commands.send_usage(ctx)

    async def _download(self, gif_url):
        async with self.acquire_http_session() as http:
            async with http.get(gif_url) as resp:
                resp.raise_for_status()
                data = await resp.read()
        data = io.BytesIO(data)
        return data

    @noaa_group.command(name="us", brief="Shows the US weather overview.")
    async def us_overview_command(self, ctx):
        async with ctx.typing():
            png = await self._download(utils.OVERVIEW_MAP_US)
        embed = theme.generic_embed(ctx, title=ctx.command.brief, description=utils.OVERVIEW_BASE)
        embed.set_image(url="attachment://image.png")
        await ctx.send(utils.OVERVIEW_BASE, file=discord.File(png, "image.png"))

    @noaa_group.command(name="alaska", aliases=["ak"], brief="Shows the Alaskan weather overview.")
    async def alaska_overview_command(self, ctx):
        async with ctx.typing():
            png = await self._download(utils.OVERVIEW_MAP_AK)
        embed = theme.generic_embed(ctx, title=ctx.command.brief, description=utils.OVERVIEW_BASE)
        embed.set_image(url="attachment://image.png")
        await ctx.send(utils.OVERVIEW_BASE, file=discord.File(png, "image.png"))

    @noaa_group.command(name="hawaii", aliases=["hi"], brief="Shows the Hawaiian weather overview.")
    async def hawaii_overview_command(self, ctx):
        async with ctx.typing():
            png = await self._download(utils.OVERVIEW_MAP_HI)
        embed = theme.generic_embed(ctx, title=ctx.command.brief, description=utils.OVERVIEW_BASE)
        embed.set_image(url="attachment://image.png")
        await ctx.send(utils.OVERVIEW_BASE, file=discord.File(png, "image.png"))

    @noaa_group.group(name="radar", brief="Country-wide radar view for the US.")
    async def radar_group(self, ctx, *, region=None):
        """
        Call with the highres argument to send a full image. Pass a region name to view
        that region instead.
        """
        if region is None:
            await self.radar_base(ctx)
        else:
            await self.radar_regional_search(ctx, region)

    async def radar_base(self, ctx):
        async with ctx.typing():
            gif = await self._download(utils.RADAR_US)

        embed = theme.generic_embed(
            ctx,
            title=ctx.command.brief,
            description=f"{utils.OVERVIEW_BASE}\n\nRun with the `highres` argument for higher resolution!",
        )
        embed.set_image(url="attachment://image.gif")
        await ctx.send(embed=embed, file=discord.File(gif, "image.gif"))

    async def radar_regional_search_command(self, ctx, site):
        async with ctx.typing():
            name, url = utils.get_wide_urls_radar_closest_match(site)
            gif = await self._download(url)

        await ctx.send(
            f"Closest match was {name} -- {utils.OVERVIEW_BASE}", file=discord.File(gif, "hawaii-overview.gif")
        )

    @radar_group.command(name="highres", aliases=["hires"], brief="Country-wide radar view for the US...BUT BIGGER")
    async def high_res_us_radar_command(self, ctx):
        async with ctx.typing():
            gif = await self._download(utils.RADAR_FULL_US)
        embed = theme.generic_embed(ctx, title=ctx.command.brief, description=utils.OVERVIEW_BASE)
        embed.set_image(url="attachment://image.gif")
        await ctx.send(embed=embed, file=discord.File(gif, "image.gif"))

    @radar_group.command(name="hawaii", aliases=["hi"], brief="Shows the Hawaiian radar.")
    async def hawaii_radar_command(self, ctx):
        async with ctx.typing():
            gif = await self._download(utils.get_wide_urls_radar_closest_match("hawaii")[1])
        embed = theme.generic_embed(ctx, title=ctx.command.brief, description=utils.OVERVIEW_BASE)
        embed.set_image(url="attachment://image.gif")
        await ctx.send(embed=embed, file=discord.File(gif, "image.gif"))

    @radar_group.command(name="alaska", aliases=["ak"], brief="Shows the Alaskan radar.")
    async def alaska_radar_command(self, ctx):
        async with ctx.typing():
            gif = await self._download(utils.get_wide_urls_radar_closest_match("alaska")[1])
        embed = theme.generic_embed(ctx, title=ctx.command.brief, description=utils.OVERVIEW_BASE)
        embed.set_image(url="attachment://image.gif")
        await ctx.send(embed=embed, file=discord.File(gif, "image.gif"))

    @noaa_group.command(name="RIDGE", aliases=["ridge", "local"], brief="Shows local radar layers.")
    async def local_command(self, ctx, *, area):
        """Search by a NEXRAD radar site, or the location of the radar."""
        async with self.acquire_http_session() as http:
            layers = await utils.generate_ridge_images_closest_match(http, area)

        author = f"Closest match: {layers.radar_site}"
        title = layers.radar_location

        def embed(**kwargs):
            if "image" in kwargs:
                image = kwargs.pop("image")
            else:
                image = None
            embed = theme.generic_embed(ctx, title=title, url=layers.web_page, **kwargs)
            embed.set_author(name=author)

            if image:
                embed.set_image(url=image)
            return embed

        @pagination.embed_generator(max_chars=2048, provides_numbering=False)
        def embed_generator(_, page, __):
            return embed(description=page)

        embeds = [
            embed(description="Base reflectivity (up to 248nmi)", image=layers.base_reflectivity_248nmi),
            embed(description="Base reflectivity (up to 124nm)", image=layers.base_reflectivity_124nm),
            embed(description="One hour precipitation", image=layers.one_hour_precipitation),
            embed(description="Composite reflectivity", image=layers.composite_reflectivity),
            embed(description="Storm relative motion", image=layers.storm_relative_motion),
            embed(description="Storm total precipitation", image=layers.storm_total_precipitation),
        ]

        p = pagination.EmbedNavigatorFactory(max_lines=20, factory=embed_generator)

        if layers.text_forecast:
            p.add_lines(*layers.text_forecast.split("\n"))
        else:
            p.add_line("No warnings are in place...")

        nav = p.build(ctx)

        for page in nav.pages:
            if embeds:
                page.set_image(url=embeds[0].image["url"])
                page.set_footer(text=embeds[0].description)
                embeds.pop(0)

        nav.pages = nav.pages + embeds

        nav.start()
