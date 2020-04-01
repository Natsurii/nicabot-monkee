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
Loggable class.
"""
import io
import logging  # Logging (duh!)
import typing

__all__ = ("Loggable", "force_verbosity")


class Loggable:
    """Adds functionality to a class to allow it to log information."""

    logger: logging.Logger

    def __init_subclass__(cls, **_):
        cls.logger: logging.Logger = logging.getLogger(cls.__name__)


def force_verbosity(verbosity: str):
    if isinstance(verbosity, str):
        verbosity = logging.getLevelName(verbosity)

    def decorator(type_t: typing.Type[Loggable]):
        type_t.logger.log(
            logging.getLevelName("CRITICAL"),
            f"Setting verbosity of {type_t.__qualname__} to be {logging.getLevelName(verbosity)}",
        )
        type_t.logger.setLevel(verbosity)
        return type_t

    return decorator


class RedirectableLoggerStream(io.TextIOBase):
    """
    Wraps a main stream permanently plus multiple other streams temporarily, and allows callers to hook into these
    with new delegate streams.

    The idea is we can add a stream and anything written out is also added to that stream. This lets commands listen
    in to their logs without disrupting existing loggers.
    """

    def __init__(self, delegate_to):
        self.delagate_to = delegate_to
        self.temp_delegates = set()

    def write(self, s: str) -> int:
        i = self.delagate_to.write(s)
        for delegate in self.temp_delegates:
            delegate.write(s)
        return i

    def add_delegate(self, stream):
        self.temp_delegates.add(stream)
        return RedirectionStreamContext(self, stream)


class RedirectionStreamContext:
    def __init__(self, redirector, delegate_to):
        self.redirector = redirector
        self.delegate_to = delegate_to

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.redirector.temp_delegates.remove(self.delegate_to)
