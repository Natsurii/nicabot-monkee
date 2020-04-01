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
A combination of a ``pagination.Paginator`` and a ``pagination.StringNavigator``.
"""

__all__ = ("StringNavigatorFactory",)

from typing import Sequence
from typing import Union

from discord.ext import commands

from ..navigator import FakeContext
from ..navigator import StringNavigator
from ..paginator import Paginator
from ..reactionbuttons import Button
from ..reactionbuttons import default_buttons


class StringNavigatorFactory(Paginator):
    """
    A paginator implementation that will build the desired StringNavigator.

    Example usage::

       snf = StringNavigatorFactory()

       for i in range(500):
           snf.add_line(f'{i}')

       snf.start(ctx)

    """

    def build(
        self,
        ctx: Union[commands.Context, FakeContext, tuple],
        buttons: Sequence[Button] = None,
        *,
        timeout: float = 300,
        initial_page: int = 0,
        **kwargs,
    ) -> StringNavigator:
        """
        Args:
            ctx: invocation context or fake context.
            buttons: buttons to show. If unspecified, this defaults to the defaultset of buttons.
            timeout: optional response timeout (defaults to 300 seconds)
            initial_page: the initial page index to start on (defaults to 0).

        Kwargs:
             attrs to assign the navigator.

        """
        if isinstance(ctx, tuple):
            ctx = FakeContext(*ctx)
        if buttons is None:
            buttons = default_buttons()

        n = StringNavigator(ctx, self.pages, buttons=buttons, timeout=timeout, initial_page=initial_page)
        for k, v in kwargs:
            setattr(n, k, v)
        return n

    def start(
        self,
        ctx: Union[commands.Context, FakeContext],
        buttons: Sequence[Button] = None,
        *,
        timeout: float = 300,
        initial_page: int = 0,
        **kwargs,
    ):
        """
        Same as performing ``.build(...).start()``
        """
        return self.build(ctx, buttons, timeout=timeout, initial_page=initial_page, **kwargs).start()
