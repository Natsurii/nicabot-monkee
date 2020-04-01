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
Implementations of errors.
"""

__all__ = ("HttpError", "NotFound")


class HttpError(RuntimeError):
    def __init__(self, response):
        self.response = response

    @property
    def reason(self) -> str:
        return self.response.reason

    @property
    def status(self) -> int:
        return self.response.status

    def __str__(self):
        return f"{self.status}: {self.reason}"


class NotFound(RuntimeError):
    def __init__(self, message=None):
        self.message = message if message else "No valid result was found"

    def __str__(self):
        return self.message


class CommandExecutionError(RuntimeError):
    """
    Should be raised if something goes wrong in a command. Deriving from
    this ensures the correct type of error message is shown to the user.

    This should send the raw message to the user in any error handler
    implementation.
    """

    def __init__(self, message: str):
        self.message = message

    def __str__(self):
        return self.message
