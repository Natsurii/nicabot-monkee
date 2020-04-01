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
Ported from Neko v1. Plots the ISS's location on a map.
"""
import datetime
import enum
import io

import discord

# noinspection PyPep8Naming
import PIL.Image as image

# noinspection PyPep8Naming
import PIL.ImageDraw as draw
from discord.ext import commands

import neko3.cog
from neko3 import files
from neko3 import neko_commands
from neko3 import theme


def _plot(latitude, longitude):
    mercator = MercatorProjection()

    x, y = mercator.swap_units(latitude, longitude, MapCoordinate.long_lat)

    x, y = int(x), int(y)

    pen = mercator.pen()

    """
    pixels = [
        (x - 1, y - 1), (x - 1, y + 1),
        (x, y),
        (x + 1, y - 1), (x + 1, y + 1),
    ]

    pen.point([(x % mercator.width, y) for x, y in pixels], (255, 0, 
    0))
    """
    pen.ellipse([(x - 4, y - 4), (x + 4, y + 4)], (255, 0, 0))

    return mercator.image


class MapCoordinate(enum.Enum):
    long_lat = enum.auto()
    xy = enum.auto()


class MercatorProjection:
    """
    Holds a PIL image and allows for manipulation using longitude-latitude
    locations.

    :param map_image: the image object to use for the projection.
    """

    def __init__(self, map_image: image.Image = None):
        """
        Creates a mercator projection from the given Image object.

        This assumes that 0E,0N is at the central pixel.

        If no image is given, the default mercator bitmap is used.
        """
        if map_image is None:
            map_image = image.open(files.in_here("mercator-small.png"))

        self.image = map_image
        self.ox, self.oy = map_image.width / 2, map_image.height / 2

        # Differential of X in pixels per degree
        self.dx = map_image.width / 360

        # Differential of Y in pixels per degree
        self.dy = map_image.height / 180

    @property
    def width(self):
        return self.image.width

    @property
    def height(self):
        return self.image.height

    def swap_units(self, vertical, horizontal, input_measurement):
        """
        Converts between X,Y and Lat,Long, depending on measurement.

        :return a tuple of (x,y) or (lat,long)
        """
        if input_measurement == MapCoordinate.long_lat:
            horizontal = (horizontal * self.dx) + self.ox
            vertical = self.oy - vertical * self.dy

            return horizontal, vertical
        elif input_measurement == MapCoordinate.xy:
            horizontal = (horizontal - self.ox) / self.dx
            vertical = (self.oy - vertical) / self.dy
            return vertical, horizontal
        else:
            raise TypeError("Unknown measurement")

    def duplicate(self):
        """Deep copy the projection."""
        return MercatorProjection(self.image.copy())

    def pen(self) -> draw.ImageDraw:
        """Gets an object capable of drawing over the projection."""
        return draw.ImageDraw(self.image)


class SpaceCog(neko3.cog.CogBase):
    async def plot(self, latitude, longitude, bytesio):
        """
        Plots a longitude and latitude on a given mercator projection.

        :param latitude: the latitude.
        :param longitude: the longitude.
        :param bytesio: the bytes IO to dump PNG data to.
        """

        img = await self.run_in_process_pool(_plot, [latitude, longitude])

        img.save(bytesio, "PNG")

        # Seek back to the start
        bytesio.seek(0)

    @neko_commands.command(name="iss", aliases=["internationalspacestation"], brief="Shows you where the ISS is.")
    @commands.cooldown(1, 30, commands.BucketType.guild)
    async def iss_command(self, ctx):
        """
        Calculates where above the Earth's surface the ISS is currently,
        and plots it on a small map.
        """

        with ctx.channel.typing():
            # Plot the first point
            with io.BytesIO() as b:
                async with self.acquire_http_session() as http:
                    res = await http.request("GET", "https://api.wheretheiss.at/v1/satellites/25544")

                    data = await res.json()
                    image_fut = self.plot(data["latitude"], data["longitude"], b)

                    assert isinstance(data, dict), "I...I don't understand..."

                    long = data["longitude"]
                    lat = data["latitude"]
                    time = datetime.datetime.fromtimestamp(data["timestamp"])
                    altitude = data["altitude"]
                    velocity = data["velocity"]

                    is_day = data["visibility"] == "daylight"

                    desc = "\n".join(
                        [
                            f"**Longitude**: {long:.3f}°E",
                            f'**Latitude**: {abs(lat):.3f}°{"N" if lat >= 0 else "S"}',
                            f"**Altitude**: {altitude:.3f} km",
                            f"**Velocity**: {velocity:.3f} km/h",
                            f"**Timestamp**: {time} UTC",
                        ]
                    )

                    embed = theme.generic_embed(
                        ctx=ctx,
                        title="International space station location",
                        description=desc,
                        url="http://www.esa.int/Our_Activities/Human_Spaceflight"
                        "/International_Space_Station"
                        "/Where_is_the_International_Space_Station ",
                    )

                    await image_fut

                    b.seek(0)
                    file = discord.File(b, "iss.png")

                    await ctx.send(file=file, embed=embed)


def setup(bot):
    bot.add_cog(SpaceCog(bot))
