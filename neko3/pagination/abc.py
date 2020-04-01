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
Abstract base classes for the pagination module.
"""

__all__ = ("PagABC",)

import weakref
from abc import ABC
from abc import abstractmethod


class PagABC(ABC):
    """
    Keeps track of the references. Useful for memory usage debugging:
    a serious downside to the pagination system in Neko2.

    The weak references are dealt with automatically internally, so you
    never even have to acknowledge it's existence.
    """

    _instances = weakref.WeakSet()

    def __init__(self):
        self._instances.add(self)

    @classmethod
    @abstractmethod
    def memory_usage(cls) -> int:
        """Estimates the memory usage used by the internal content."""
        ...
