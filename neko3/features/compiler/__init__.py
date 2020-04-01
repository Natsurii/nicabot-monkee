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
Various code-related compilation tools.

A huge-ass module that consists almost purely of API interfaces I created
from stuff I found online and reverse engineered.

Note that it is only respectful to stop using this module if usage gets too
high. It would be unfair to ruin the service for everyone else. However, for
tens or hundreds of requests per day, this should be fine.
"""
from . import code_style
from . import coliru
from . import r
from . import rextester
from . import tex


def setup(bot):
    types = [code_style.CodeStyleCog, coliru.ColiruCog, r.RCog, rextester.RextesterCog, tex.TeXCog]

    for class_ in types:
        bot.add_cog(class_(bot))
