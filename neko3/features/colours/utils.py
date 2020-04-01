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
Colour codes:

Dulux colours: http://www.dulux.co.nz/media/341246/duluxrgb.pdf
"""

import io
import json
import logging
import math
import string
import typing

import PIL.Image as pil_image
import PIL.ImageDraw as pil_pen
import PIL.ImageFont as pil_font

from neko3 import files

_pheight = 25
_pwidth = 25

# Palette options.
_pal_colours_per_row = 7
_pal_width_per_colour = 200
_pal_height_per_colour = 100
_pal_backing_colour = (0, 0, 0, 0)
# Relative text location in the palette.
_pal_rel_text_location = (10, 10)

_rgb = typing.Tuple[int, int, int]
_rgba = typing.Tuple[int, int, int, int]
_cmyk = typing.Tuple[float, float, float, float]
_hsl = typing.Tuple[float, float, float]
_hsv = typing.Tuple[float, float, float]
_unsan_v = typing.Union[str, int, float]

font = None

for poss_font in ("arial.ttf", "Lato-Bold.ttf", "DejaVuSerif.ttf"):
    try:
        font = pil_font.truetype(poss_font, 25)
    except OSError:
        continue
    else:
        break

if font is None:
    # Default font if we can't find any other fonts.
    font = pil_font.load_default()


def generate_preview(red: int, green: int, blue: int, alpha: int):
    """Generates a 25x25 pixel colour preview as a PNG."""
    if not all(0 <= rgba <= 255 for rgba in (red, green, blue, alpha)):
        raise ValueError(f"Invalid colour channel in ({red},{green},{blue},{alpha}).")

    img = pil_image.new("RGBA", color=(red, green, blue, alpha), size=(_pwidth, _pheight))

    bytes_io = io.BytesIO()
    bytes_io.seek(0)
    img.save(bytes_io, "PNG")
    bytes_io.seek(0)
    return bytes_io.getvalue()


def invert(r: int, g: int, b: int, a: int) -> _rgba:
    """Inverts the given colour."""
    return 0xFF - r, 0xFF - g, 0xFF - b, a


# The ensure_x methods will perform valid conversions, and may throw
# ValueError and TypeError exceptions.


def ensure_deg_360(val: _unsan_v) -> float:
    # Ensures the value is an angle in degrees 0->360

    # Remove any arbitrary units at the end.
    for x in "oO'°":
        val = val.replace(x, "")

    try:
        val = float(val)
    except ValueError:
        raise TypeError("Expected floating point angle (degrees).") from None
    else:
        if not 0 <= val <= 360:
            raise ValueError("Expected angle to be between 0 and 360°")
    return val


def ensure_percentage(val: _unsan_v) -> float:
    # Ensures the value is a valid percentage between 0 and 100, floating.
    try:
        if val.endswith("%"):
            val = val[:-1]
        val = float(val)
    except ValueError:
        raise TypeError("Expected percentage.") from None
    else:
        if not 0 <= val <= 100:
            raise ValueError("Expected percentage between 0 and 100%.")

    return val / 100


def ensure_float_in_01(val: _unsan_v) -> float:
    # Some useful validation for arbitrary colour spaces.
    try:
        val = float(val)
    except ValueError:
        raise TypeError("Expected float value between 0 and 1.") from None
    else:
        if not 0 <= val <= 1:
            raise ValueError("Must be between 0 and 1.")
    return val


def ensure_int_in_0_255(val: _unsan_v) -> int:
    # Validation!
    try:
        val = int(val)
    except ValueError:
        raise TypeError("Expected int value between 0 and 255.") from None
    else:
        if not 0 <= val <= 255:
            raise ValueError("Must be between 0 and 255.")
    return val


def is_web_safe(r: int, g: int, b: int, a: int):
    """
    True if the rgba value is websafe.

    Cite: https://www.rapidtables.com/web/color/Web_Safe.html
    """
    if a != 255:
        return False
    else:
        return all(x in (0, 0x33, 0x66, 0x99, 0xCC, 0xFF) for x in (r, g, b))


def to_float(r: int, g: int, b: int, a: int = None):
    """Converts RGBA or RGB to float."""
    had_a = a is not None
    if not had_a:
        a = 255
    r, g, b, a = (ensure_int_in_0_255(x) for x in (r, g, b, a))

    r = round(r / 255.0, 2)
    g = round(g / 255.0, 2)
    b = round(b / 255.0, 2)
    a = round(a / 255.0, 2)
    return (r, g, b, a)


def from_float(r: float, g: float, b: float, a: int = None):
    """Parses from float to int values."""
    # Validates and parses the inputs to the correct type.
    had_a = a is not None
    if not had_a:
        a = 1.0

    r, g, b, a = (ensure_float_in_01(x) for x in (r, g, b, a))

    r = int(r * 255)
    g = int(g * 255)
    b = int(b * 255)
    a = int(a * 255)

    return (r, g, b, a)


def to_hex(r: int, g: int, b: int, _a: int = None, *, prefix="#"):
    """
    Takes RGBA colour values from 0 to 255, and generates a hex
    representation. Note the alpha channel is ignored, and is optional.
    :param r: red channel
    :param g: green channel
    :param b: blue channel
    :param _a: the alpha channel. Optional, and isn't used.
    :param prefix: what to prefix to the start. Defaults to '#'
    :return: the string generated.
    """
    r = hex(r)[2:4]
    g = hex(g)[2:4]
    b = hex(b)[2:4]

    if len(r) == 1:
        r = f"0{r}"
    if len(g) == 1:
        g = f"0{g}"
    if len(b) == 1:
        b = f"0{b}"

    return "".join((prefix, r, g, b))


def to_short_hex(r: int, g: int, b: int, _a: int = None, *, prefix="#"):
    """
    Attempts to return a 3-digit hex code. If it can not, it returns None.
    """
    r = hex(r)[2:4]
    g = hex(g)[2:4]
    b = hex(b)[2:4]

    if len(r) == 1:
        r = f"0{r}"
    if len(g) == 1:
        g = f"0{g}"
    if len(b) == 1:
        b = f"0{b}"

    if not all(chan[0] == chan[1] for chan in (r, g, b)):
        return None
    else:
        return "".join((prefix, r[0], g[0], b[0]))


def from_hex(cc: str) -> _rgba:
    """
    Takes a three or six digit hexadecimal RGB value and returns the value as
    a tuple of red, green and blue byte-sized ints. Each can range between 0
    and 255 inclusive.

    If a 0x or a # is on the start of the string, we ignore it, so you do not
    need to sanitise input for those.

    :param cc: the input
    :return: tuple of red, green and blue.
    """
    cc = cc.upper()
    for x in ("0x", "0X", "#"):
        cc = cc.replace(x, "")

    if len(cc) not in (3, 6) or not all(d in "0123456789ABCDEF" for d in cc):
        raise ValueError("Expected either 3 or 6 hexadecimal digits only.")
    elif len(cc) == 3:
        # FAB -> FFAABB
        cc = "".join(2 * d for d in cc)

    # noinspection PyTypeChecker
    return tuple(int(d, 16) for d in (cc[0:2], cc[2:4], cc[4:6], "FF"))


def to_cmyk(r: int, g: int, b: int) -> _cmyk:
    """
    Takes RGB values 0->255 and returns their values
    in the CMYK namespace.

    https://www.rapidtables.com/convert/color/rgb-to-cmyk.html
    """
    r, g, b, _ = to_float(r, g, b)

    k = 1 - max(r, g, b)
    if k == 1:
        c, y, m = 0, 0, 0
    else:
        c = (1 - r - k) / (1 - k)
        m = (1 - g - k) / (1 - k)
        y = (1 - b - k) / (1 - k)

    return (c, m, y, k)


def from_cmyk(c: float, m: float, y: float, k: float) -> _rgba:
    """
    Converts CMYK values 0->1 and returns the equivalent RGB values
    0->255

    https://www.rapidtables.com/convert/color/cmyk-to-rgb.html
    """
    c, m, y, k = (ensure_float_in_01(x) for x in (c, m, y, k))

    r = int(255 * (1 - c) * (1 - k))
    g = int(255 * (1 - m) * (1 - k))
    b = int(255 * (1 - y) * (1 - k))

    return (r, g, b, 255)


def to_hsl(r: int, g: int, b: int) -> _hsl:
    """
    Converts r, g, b to HSL.

    https://www.rapidtables.com/convert/color/rgb-to-hsl.html
    """
    r, g, b, _ = to_float(r, g, b)
    c_max = max(r, g, b)
    c_min = min(r, g, b)
    delta = c_max - c_min

    light = (c_max + c_min) / 2

    if delta == 0:
        h = 0.0
    elif c_max == r:
        h = 60 * (((g - b) / delta) % 6)
    elif c_max == g:
        h = 60 * (((b - r) / delta) + 2)
    else:
        assert c_max == b, "Your code is screwed up, laddie."
        h = 60 * (((r - g) / delta) + 4)

    if delta == 0:
        s = 0
    else:
        s = delta / (1 - abs(2 * light - 1))

    s *= 100
    light *= 100

    return (h, s, light)


def from_hsl(h: float, s: float, light: float) -> _rgba:
    """
    Converts hsl to rgb.
    """
    h = ensure_deg_360(h)
    s, light = ensure_percentage(s), ensure_percentage(light)

    c = (1 - abs(2 * light - 1)) * s
    x = c * (1 - (abs((h / 60) % 2 - 1)))
    m = light - c / 2
    if 0 <= h < 60:
        r, g, b = (c, x, 0)
    elif 60 <= h < 120:
        r, g, b = (x, c, 0)
    elif 120 <= h < 180:
        r, g, b = (0, c, x)
    elif 180 <= h < 240:
        r, g, b = (0, x, c)
    elif 240 <= h < 300:
        r, g, b = (x, 0, c)
    else:
        assert 300 <= h < 360, "English, MoFo! Do you speak it?"
        r, g, b = (c, 0, x)

    r = int((r + m) * 255)
    g = int((g + m) * 255)
    b = int((b + m) * 255)

    return (r, g, b, 255)


def to_hsv(r: int, g: int, b: int, a: int = None) -> _hsv:
    """
    Converts RGB to HSV.
    """
    r, g, b, a = to_float(r, g, b, a)

    c_max = max(r, g, b)
    c_min = min(r, g, b)

    delta = c_max - c_min

    if delta == 0:
        h = 0.0
    elif c_max == r:
        h = 60 * (((g - b) / delta) % 6)
    elif c_max == g:
        h = 60 * (((b - r) / delta) + 2)
    else:
        assert c_max == b, "You done broke it."
        h = 60 * (((r - g) / delta) + 4)

    s = 0 if c_max == 0 else delta / c_max

    v = c_max

    s *= 100
    v *= 100

    return (h, s, v)


def from_hsv(h: float, s: float, v: float) -> _rgba:
    """
    Converts HSV to RGB.
    """
    h = ensure_deg_360(h)
    s, v = ensure_percentage(s), ensure_percentage(v)

    c = v * s
    x = c * (1 - abs(((h / 60) % 2) - 1))
    m = v - c

    if 0 <= h < 60:
        r, g, b = (c, x, 0)
    elif 60 <= h < 120:
        r, g, b = (x, c, 0)
    elif 120 <= h < 180:
        r, g, b = (0, c, x)
    elif 180 <= h < 240:
        r, g, b = (0, x, c)
    elif 240 <= h < 300:
        r, g, b = (x, 0, c)
    else:
        assert 300 <= h < 360, "Enough is enough."
        r, g, b = (c, 0, x)

    r = int((r + m) * 255)
    g = int((g + m) * 255)
    b = int((b + m) * 255)

    return r, g, b, 255


class ColourNames(typing.Mapping[str, typing.Tuple[int, int, int]]):
    """
    Looks at a large collection of common colour names. These include basic names
    and HTML standard names, as well as a massive Dulux colour list I found.
    """

    # noinspection PyMissingConstructor
    def __init__(self):
        self.log = logging.getLogger(__name__)

        path = files.in_here("commoncolours.json")
        self.log.info("Reading common HTML colours from %s", path)
        with open(path) as fp:
            obj = json.load(fp)
            obj = {n.lower(): v.lower() for n, v in obj.items()}
        assert isinstance(obj, dict)

        # Read the dulux colours in, but don't overwrite the HTML ones.
        path = files.in_here("duluxcolours.txt")
        self.log.info("Reading the DULUX colour guide from %s", path)
        with open(path) as fp:
            for line in fp.readlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                shade, _, rest = line.partition(" ")
                rest, _, lrv = rest.rpartition(" ")
                rest, _, b = rest.rpartition(" ")
                rest, _, g = rest.rpartition(" ")
                name, _, r = rest.rpartition(" ")
                alt_name = name.translate({c: "" for c in string.punctuation})

                hex_str = to_hex(int(r), int(g), int(b), prefix="")

                shade = shade.lower()
                hex_str = hex_str.lower()
                name = name.lower()

                if shade not in obj:
                    obj[shade] = hex_str

                if name not in obj:
                    obj[name] = hex_str

                if alt_name not in obj:
                    obj[alt_name] = hex_str

        # Do this to remove case sensitivity.
        self.__data = {n: from_hex(c) for n, c in obj.items()}

        # Reverse the list for reverse lookups.
        self.__reversed = {v: k for k, v in self.items()}

        self.log.info("Loaded %s colours!", len(self.__data))

    def __iter__(self):
        return iter(self.__data)

    def __len__(self) -> int:
        return len(self.__data)

    def __getitem__(self, item) -> _rgb:
        return self.__data[item.lower()]

    def __contains__(self, item) -> bool:
        return item.lower() in self.__data

    def get(self, name) -> _rgb:
        return self[name]

    def items(self) -> typing.ItemsView[str, typing.Tuple[int, int, int]]:
        return self.__data.items()

    def keys(self) -> typing.Iterable[str]:
        return self.__data.keys()

    def values(self) -> typing.Iterable[_rgb]:
        return self.__data.values()

    def from_value(self, value: (int, int, int), default=None):
        """Reverse lookup."""
        return self.__reversed.get(value, default)


# Suppresses incorrect inspections.
ColourNames = ColourNames()


def make_palette(*strings):
    """
    Generates a palette of the given hex string colours
    """
    if len(strings) == 0:
        raise ValueError("No input...")

    # Dict mapping hex to rgb tuples.
    colours = []

    for colour in strings:
        try:
            if colour.startswith("#") or all(c in string.hexdigits for c in colour):
                colours.append((colour, from_hex(colour)))
            else:
                display = colour[:12]
                if display != colour:
                    colour += "..."

                actual = ColourNames.get(colour)
                colours.append((display, actual))
        except KeyError:
            raise ValueError("Expected colour name, hex or RGB/RGBA bytes.")

    rows = math.ceil(len(colours) / _pal_colours_per_row)
    cols = min(_pal_colours_per_row, len(colours))

    im_width = cols * _pal_width_per_colour
    im_height = (rows - 1) * _pal_height_per_colour + _pal_height_per_colour

    image = pil_image.new("RGBA", (im_width, im_height), _pal_backing_colour)

    pen = pil_pen.Draw(image)

    for i, (name, raw) in enumerate(colours):
        if len(raw) == 4:
            r, g, b, a = raw
        else:
            r, g, b = raw
            a = 255

        col = i % cols
        row = int(i / cols)

        # Get the start coordinates
        xs, ys = col * _pal_width_per_colour, row * _pal_height_per_colour

        pen.rectangle((xs, ys, xs + _pal_width_per_colour, ys + _pal_height_per_colour), (r, g, b, a))

        text_xs, text_ys = _pal_rel_text_location
        text_xs += xs
        text_ys += ys

        # Adds text in two colours.
        inverted = invert(r, g, b, 0xFF)

        # Actual text
        pen.text((text_xs, text_ys), name, fill=inverted, font=font)

    bytes_io = io.BytesIO()
    image.save(bytes_io, "PNG")
    bytes_io.seek(0)
    return bytes_io.getvalue()
