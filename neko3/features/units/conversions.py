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
Hard coded model definitions. These are singletons, and are evil... if you
alter
them. They should not be altered however, so there should never be a problem.
"""
from decimal import Decimal
from typing import Iterator
from typing import Optional

from neko3 import algorithms
from .models import *

__all__ = ("get_category", "get_compatible_models", "find_unit_by_str")


def kelvin_to_celcius(kelvin):
    if kelvin < Decimal(0):
        raise ValueError("Cannot be less than 0K")
    else:
        return kelvin - Decimal("273.15")


def kelvin_to_fahrenheit(kelvin):
    if kelvin < Decimal(0):
        raise ValueError("Cannot be less than 0K")
    else:
        return (kelvin * (Decimal("9") / Decimal("5"))) - Decimal("459.67")


def celcius_to_kelvin(celcius):
    if celcius < Decimal("-273.15"):
        raise ValueError("Cannot be less than 273.15C")
    else:
        return celcius + Decimal("273.15")


def fahrenheit_to_kelvin(fahrenheit):
    if fahrenheit < Decimal("-459.67"):
        raise ValueError("Cannot be less than -459.67F")
    else:
        return Decimal("5") * (fahrenheit + Decimal("459.67")) / Decimal("9")


# Last name should be abbreviation. First should be singular and second should
# be plural.
_models = {
    UnitCollectionModel(
        UnitCategoryModel.DISTANCE,
        UnitModel.new_si("meter", "meters", "metre", "metres", "m"),
        UnitModel.new_cv("0.3048", "foot", "feet", "ft"),
        UnitModel.new_cv("1000", "kilometer", "kilometers", "kilometre", "kilometres", "km"),
        UnitModel.new_cv("1609.34", "mile", "miles", "mi"),
        UnitModel.new_cv("0.9144", "yard", "yards", "yd"),
        UnitModel.new_cv("0.0254", "inch", "inches", "inchs", "in"),
        UnitModel.new_cv(
            "1852",
            "nautical mile",
            "nautical miles",
            "nautical-mile",
            "nautical-miles",
            "nmi",
            exclude_from_conversions=True,
        ),
        UnitModel.new_cv("0.01", "centimeter", "centimeters", "centimetre", "centimetres", "cm"),
        UnitModel.new_cv("0.001", "millimeter", "millimeters", "millimetre", "millimetres", "mm"),
        UnitModel.new_cv(
            "1.496e+11", "AU", "AU", "astronomical unit", "astronomical units", "AU", exclude_from_conversions=True
        ),
        UnitModel.new_cv("9.461e+15", "light-year", "light-years", "light year", "light years", "ly"),
        UnitModel.new_cv("3.086e+16", "parsec", "parsecs", "pc", exclude_from_conversions=True),
    ),
    UnitCollectionModel(
        UnitCategoryModel.TIME,
        UnitModel.new_si("second", "seconds", "s"),
        UnitModel.new_cv("60", "minute", "minutes"),
        UnitModel.new_cv("3600", "hour", "hours", "h"),
        UnitModel.new_cv("86400", "day", "days", "dy", "dys"),
        UnitModel.new_cv("604800", "week", "weeks", "wk", "wks"),
        UnitModel.new_cv("2592000", "month", "months", "mon", "mons"),
        UnitModel.new_cv("31536000", "year", "years", "yr", "yrs"),
        UnitModel.new_cv("3.336e-11", "jiffy", "jiffies", exclude_from_conversions=True),
        UnitModel.new_cv("5.391e-44", "plank time", "tP", exclude_from_conversions=True),
    ),
    UnitCollectionModel(
        UnitCategoryModel.SPEED,
        UnitModel.new_si(
            "meter per second", "meters per second", "metres per second", "metre per second", "ms^-1", "m/s"
        ),
        UnitModel.new_cv(
            "0.2777777777777777777777777778",
            "kilometer per hour",
            "kilometers per hour",
            "kilometres per hour",
            "kilometre per hour",
            "kmh",
            "kmph",
            "kmh^-1",
            "km/hr",
            "km/h",
        ),
        UnitModel.new_cv("0.4417167941608573546287944577", "mile per hour", "miles per hour", "mi/h", "mph"),
        UnitModel.new_cv(
            "0.3047999902464003121151900123",
            "foot per second",
            "feet per second",
            "fts^-1",
            "ftsec^-1",
            "ft/sec",
            "ft/s",
        ),
        UnitModel.new_cv("0.5144456333854638241830603342", "knot", "knots", "kts", "kt"),
    ),
    UnitCollectionModel(
        UnitCategoryModel.VOLUME,
        UnitModel.new_si("meter³", "meters³", "m^3", "m³"),
        UnitModel.new_cv("0.001", "liter", "litre", "liters", "litres", "l"),
        UnitModel.new_cv("1e-6", "milliliter", "milliliters", "millilitre", "millilitres", "ml"),
        UnitModel.new_cv("1e-5", "centiliter", "centiliters", "centilitre", "centilitres", "cl"),
        UnitModel.new_cv("1e-6", "centimeters³", "cm³", "cm^3", "cc"),
        UnitModel.new_cv("0.000568261", "pints", "pint", "UKpnt" "pnt"),
        UnitModel.new_cv("0.00454609", "gallons", "gallon", "UKgal", "gal"),
        UnitModel.new_cv("0.000473176", "US pints", "US pint", "USpnt"),
        UnitModel.new_cv("0.00378541", "US gal", "USgal"),
        UnitModel.new_cv("0.0283168", "feet³", "foot³", "feet^3", "foot^3", "ft^3"),
        UnitModel.new_cv("1.6387e-5", "inches³", "inch³", "inchs³", "in^3" "inches^3", "inch^3", "inchs^3", "in³"),
    ),
    # Includes mass for the benefit of the doubt.
    UnitCollectionModel(
        UnitCategoryModel.FORCE_MASS,
        UnitModel.new_si("newton", "newtons", "kgms^-2", "kg/ms^2", "N"),
        UnitModel.new_cv("0.101936799180", "kilogram", "kilograms", "kilogrammes", "kilo", "kilos", "kg"),
        UnitModel.new_cv("4.44822", "pound force", "lbf"),
        UnitModel.new_cv("0.04623775433027025", "pound", "pounds", "lb"),
        UnitModel.new_cv("0.6473285606237836", "stone", "stone", "stones", "st"),
        UnitModel.new_cv("101.93679918", "tonne", "T"),
    ),
    UnitCollectionModel(
        UnitCategoryModel.DATA,
        UnitModel.new_si("byte", "bytes", "B"),
        UnitModel.new_cv("1e3", "kilobyte", "kilobytes", "kB"),
        UnitModel.new_cv("1e6", "megabyte", "megabytes", "MB"),
        UnitModel.new_cv("1e9", "gigabyte", "gigabytes", "GB"),
        UnitModel.new_cv("1e12", "terabyte", "terabytes", "TB"),
        UnitModel.new_cv("1024", "kibibyte", "kibibytes", "kiB"),
        UnitModel.new_cv("1048576", "mebibyte", "mebibytes", "MiB"),
        UnitModel.new_cv("1073741824", "gibibyte", "gibibytes", "GiB"),
    ),
    UnitCollectionModel(
        UnitCategoryModel.TEMPERATURE,
        UnitModel.new_si("\ufff0K", "\ufff0K", "kelvin", "K"),
        UnitModel(celcius_to_kelvin, kelvin_to_celcius, "°C", "°C", "celsius", "centigrade", "oC", "C"),
        UnitModel(fahrenheit_to_kelvin, kelvin_to_fahrenheit, "°F", "°f", "fahrenheit", "oF", "F"),
    ),
}


def get_category(category: UnitCategoryModel) -> Optional[UnitCollectionModel]:
    """
    Gets the given collection of measurement quantities for the given
    dimensionality of measurement.
    """
    res = algorithms.find(lambda c: c.unit_type == category, _models)
    return res


def get_compatible_models(model: UnitModel, ignore_self: bool = False, ignore_si: bool = False) -> Iterator[UnitModel]:
    """Yields any compatible models with the given model, including itself."""
    if ignore_self or ignore_si:
        for pm in get_category(model.unit_type):
            if pm.exclude_from_conversions:
                continue
            if ignore_self and pm == model:
                continue
            elif ignore_si and model.is_si:
                continue
            else:
                yield pm

    else:
        yield from get_category(model.unit_type)


def find_unit_by_str(input_string: str) -> Optional[UnitModel]:
    """
    Attempts to find a match for the given input string. Returns None if
    nothing is resolved.
    """
    input_string = input_string.lower()

    for category in _models:
        for model in category:
            if input_string in (n.lower() for n in model.names):
                return model
