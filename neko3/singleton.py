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
Singleton pattern implementation for creating unique one-instance objects
from classes on demand.

Note:
    ``class Foo(Singleton)`` is analogus to ``class Foo(metaclass=SingletonMeta)``.

Example usage:

    >>> class Foo(Singleton):
    >>>     def __init__(self):
    >>>         print('Initialising new Foo')

    >>> a = Foo()
    Initialising new Foo
    >>> b = Foo()
    >>>
    >>> a is b
    >>> True

Author:
    Nekokatt

"""

__all__ = ("SingletonMeta", "Singleton")


def _singleton_repr(t: type):
    return f"<{t.__name__} Singleton>"


class SingletonMeta(type):
    """
    Metaclass that enforces the Singleton pattern. Useful for specialising
    sentinel objects, et cetera.
    """

    __singletons = {}

    def __call__(cls):
        if cls in cls.__singletons:
            return cls.__singletons[cls]
        else:
            singleton = super(SingletonMeta, cls).__call__()
            cls.__singletons[cls] = singleton
            return singleton

    def __repr__(cls):
        return _singleton_repr(cls)

    def __eq__(cls, other):
        if isinstance(type(other), cls):
            return True
        elif other is cls:
            return True
        else:
            return False

    def __hash__(cls):
        return super().__hash__()

    __str__ = __repr__


class Singleton(metaclass=SingletonMeta):
    """Less verbose way of implementing a singleton class."""

    __slots__ = ()

    def __repr__(self):
        return _singleton_repr(type(self))

    __str__ = __repr__

    def __eq__(self, other):
        if isinstance(other, type(self)):
            return True
        elif other is self:
            return True
        else:
            return False
