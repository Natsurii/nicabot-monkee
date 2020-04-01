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
Parser logic.
"""
import typing

from neko3.features.units.conversions import find_unit_by_str
from neko3.features.units.models import PotentialValueModel
from neko3.features.units.models import ValueModel


def _parse(input_model: PotentialValueModel) -> typing.Optional[ValueModel]:
    """Parses a single value.s"""
    unit_type = find_unit_by_str(input_model.unit)
    if unit_type is not None:
        return ValueModel(input_model.value, unit_type)


def parse(input_model: PotentialValueModel, *input_models: PotentialValueModel) -> typing.Iterator[ValueModel]:
    """
    Takes one or more input models that may be a measurement, and attempts
    to parse them, returning an iterator across all parsed results,
    and ignoring
    any that turn out to be invalid.
    """
    # Parse the potential models.
    for pm in (input_model, *input_models):
        parsed = _parse(pm)
        if parsed is not None:
            yield parsed
