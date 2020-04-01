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
String manipulation utilities.
"""
import re
import urllib.parse

__all__ = ("remove_single_lines", "trunc", "plur_simple", "plur_diff", "yn", "cap", "pascal2title", "is_url")


def remove_single_lines(string: str) -> str:
    """
    Attempts to remove single line breaks. This should take into account
    lists correctly this time! This will treat line breaks proceeded by
    anything that is not an alpha as a normal line break to keep. Thus, you
    must ensure each line of a continuing paragraph starts with an alpha
    character if you want it parsed correctly.

    The purpose of this is to fix textual paragraphs obtained from docstrings.

    Todo: implement something to prevent altering code blocks?
    """
    lines = []

    def previous_line():
        if lines:
            return lines[-1]
        else:
            return ""

    for line in string.splitlines():
        line = line.rstrip()

        # Empty line
        if not line:
            lines.append("")

        # Continuation
        elif line[0].isalpha():

            # Doing it this way prevents random leading whitespace.
            current_line = [line]
            if previous_line():
                current_line.insert(0, previous_line())
            current_line = " ".join(current_line)

            if previous_line():
                lines[-1] = current_line
            else:
                lines.append(current_line)

        # Treat normally: do not alter.
        else:
            lines.append(line)

    return "\n".join(lines)


def trunc(text, max_length: int = 2000):
    """Truncates output if it is too long."""
    if len(text) <= max_length:
        return text
    else:
        return text[0 : max_length - 3] + "..."


def plur_simple(cardinality: int, word: str, suffix="s"):
    """Pluralises words that just have a suffix if pluralised."""
    if cardinality - 1:
        word += suffix
    return f"{cardinality} {word}"


def plur_diff(cardinality: int, singular: str, plural: str):
    """Pluralises words that change spelling when pluralised."""
    return f"{cardinality} {plural if cardinality - 1 else singular}"


def yn(boolean: bool) -> str:
    """Converts 'True' or 'False' to 'Yes' or 'No'"""
    return "Yes" if boolean else "No"


def cap(string: str):
    """Capitalises the first letter of stuff.."""
    return string[0:1].upper() + string[1:]


def pascal2title(string: str) -> str:
    """Splits on whitespace between capital and lowercase letters."""
    # https://stackoverflow.com/a/29922050
    return " ".join(re.findall(r"[A-Z](?:[a-z]+|[A-Z]*(?=[A-Z]|$))", string))


def is_url(url):
    """Return true if the string is a valid URL. False otherwise."""
    # noinspection PyBroadException
    try:
        urllib.parse.urlparse(url)
        return True
    except Exception:
        return False
