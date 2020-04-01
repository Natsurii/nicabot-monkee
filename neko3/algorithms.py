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
Algorithm stuff, and general bits and pieces that don't belong elsewhere, or
that generally operate on a wide variety of data.
"""
import contextlib
import time  # Basic timestamps


def find(predicate, iterable, default=None):
    """
    Attempts to find the first match for the given predicate in the iterable.

    If the element is not found, then ``None`` is returned.
    """
    for el in iterable:
        if predicate(el):
            return el

    return default


class TimeIt(contextlib.AbstractContextManager):
    def __init__(self):
        self.start = float("nan")
        self.end = float("nan")

    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end = time.perf_counter()

    @property
    def time_taken(self):
        return self.end - self.start


def rand_colour() -> int:
    """Gets a random colour."""
    from random import randint

    return randint(0, 0xFFFFFF)
