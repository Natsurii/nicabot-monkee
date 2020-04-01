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
Repeats whatever you say but in a condescending tone. It should work well with
SQL so that the main code is edited, but comments and strings are not.
"""

import random
import re

from neko3 import neko_commands

regex = re.compile(r"```[a-zA-Z0-9]+\s([\s\S(^\\`{3})]*?)\s*```")


class MockSqlCog(neko_commands.Cog):
    @neko_commands.command(name="mocksql", brief="iTS pRonOunCeD sEquEl")
    async def mock_sql_command(self, ctx, *, markup):
        markup_scrub = regex.match(markup)
        if markup_scrub:
            markup = markup_scrub.group(1)

        single_quote = False
        double_quote = False
        single_comment = False
        multiline_comment = False

        output = ""
        index = 0

        while index < len(markup):
            if any((single_quote, double_quote, single_comment, multiline_comment)):
                output += markup[index]
                if single_comment and markup[index] == "\n":
                    single_comment = False
                    index += 1
                elif single_quote and markup[index] == "'":
                    single_quote = False
                    index += 1
                elif double_quote and markup[index] == '"':
                    double_quote = False
                    index += 1
                elif multiline_comment and markup[index:].startswith("*/"):
                    multiline_comment = False
                    output += "/"
                    index += 2
                else:
                    index += 1
            else:
                if random.choice((True, False)):
                    output += markup[index].upper()
                else:
                    output += markup[index].lower()

                if markup[index:].startswith("--"):
                    single_comment = True
                    output += "-"
                    index += 2
                elif markup[index:].startswith("/*"):
                    multiline_comment = True
                    output += "*"
                    index += 2
                elif markup[index] == '"':
                    double_quote = True
                    index += 1
                elif markup[index] == "'":
                    single_quote = True
                    index += 1
                else:
                    index += 1

        nb = " "
        # Prevent @everyone exploits
        await ctx.send(f"```sql\n{output}\n```\n".replace("@", "@" + nb))


def setup(bot):
    bot.add_cog(MockSqlCog())
