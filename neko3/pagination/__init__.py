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
Utilities for paginating arbitrary content such as strings, in order to fit
inside a message in Discord.

This also has utilities to enable the creation of a navigation-like object in
a Discord chat. This is a state machine that contains a certain page from a 
paginator, and provides Discord reactions (known as "buttons") that have
actions associated with them. When an authorised user (fully customisable) 
interacts with said reaction, the bot will remove the reaction and perform the
given task. This enables navigation through paginator output while only
displaying one message at a time. Buttons are easily created and can do anything
you desire within the constraints of Discord.py.
"""

from .abc import *
from .factory.basefactory import *
from .factory.embedfactory import *
from .factory.stringfactory import *
from .navigator import *
from .optionpicker import *
from .paginator import *
from .reactionbuttons import *
