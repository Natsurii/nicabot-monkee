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
Handles reading config files.
"""
import io  # Streams
import json
import os  # File operations
import typing  # Type checking

import aiofiles  # Async file IO
import yaml

from neko3 import files
from neko3 import logging_utils

CONFIG_DIRECTORY = os.getenv("NEKOZILLA_CONFIG_DIRECTORY", "./config")

# Functions to call to deserialize each type.
deserializers = {".json": json.load, ".yaml": yaml.safe_load, ".yml": yaml.safe_load}


class ConfigFile(logging_utils.Loggable):
    """
    Representation of a configuration file that allows for read-only
    access. This model assumes that the config file is not changeable at
    runtime; thus the data is cached after the first access.

    This also will attempt to guess the file extension if omitted, for example,
    if you attempt to load `foo`, but `foo` does not exist, the class will
    attempt to resolve `foo.json`, then `foo.yaml`, etc. If one of those is
    found, then that is loaded instead.

    Note. This is not thread-safe.

    The constructor will block for a very short period of time whilst it
    checks that the file is a valid file inode and that it exists. This is only
    really a problem if you are constantly making these objects in a coroutine
    and you have a very slow file system.

    :param path: the path of the file to read. If extension is omitted, we
        attempt to find it.
    :param should_guess: defaults to true. If true, we allow guessing of the
        extension if we fail to find it.
    """

    def __init__(self, path, *, should_guess=True):
        path, ext = self._get_extension(path, should_guess)

        if not path:
            raise ValueError("Not a valid path")
        elif not os.access(path, os.R_OK):
            raise PermissionError(f"I do not have read access to {path!r}.")
        else:
            self.path = path
            self._value = None
            try:
                self.deserializer = deserializers[ext]
            except KeyError:
                raise NotImplementedError(f"No deserialiser is defined for {ext}")

    @staticmethod
    def _get_extension(base: str, should_guess: bool = True) -> typing.Optional[typing.Tuple[str, str]]:
        """
        Assuming that base is not found as an actual file path, attempt
        to resolve the config file by guessing the extension. We return the
        first match for the file name, with the extension. This will also work
        if the extension already exists. If nothing can be found, then an
        exception is raised.
        """
        for ext in deserializers:
            if os.path.isfile(base) and base.endswith(ext):
                return base, ext
            elif os.path.isfile(base + ext) and should_guess:
                return base + ext, ext

        if not os.path.exists(base):
            raise FileNotFoundError(f"{base!r} does not exist.")
        elif not os.path.isfile(base):
            raise TypeError(f"{base!r} is not a valid file.")
        else:
            return None

    async def async_get(self):
        """Asynchronously reads the config from file."""
        if self._value is not None:
            return self._value
        else:
            self.logger.info(
                f"Asynchronously deserialising {self.path} using "
                f'{getattr(self.deserializer, "__module__")}.'
                f"{self.deserializer.__name__}"
            )
            async with aiofiles.open(self.path) as fp:
                with io.StringIO(await fp.read()) as str_io:
                    str_io.seek(0)

                    return self.deserializer(str_io)

    def sync_get(self):
        """Blocks while we read the config from the file."""
        if self._value is not None:
            return self._value
        else:
            self.logger.info(
                f"Deserialising {self.path} using "
                f'{getattr(self.deserializer, "__module__")}.'
                f"{self.deserializer.__name__}"
            )

            with open(self.path) as fp:
                return self.deserializer(fp)

    def invalidate(self):
        """
        Invalidates the cache. This causes the next read to cause a new file
        read operation.
        """
        old = self._value
        self._value = None
        return old

    @property
    def is_cached(self):
        return self._value is not None


def get_from_config_dir(file_name, *, load_now=True):
    """
    Constructs a ConfigFile from the default configuration directory, and
    caches the data.

    :param file_name: the file to open in the configuration directory.
    :param load_now: true if we should immediately cache. Defaults to False.
    :returns: a ConfigFile object.
    """
    path = os.path.join(CONFIG_DIRECTORY, file_name)
    cf = ConfigFile(path)

    if load_now:
        cf.sync_get()
    return cf


def get_from_here(file_name, *, nested_by=0, load_now=False):
    """
    Constructs a ConfigFile relative to the current directory the caller is
    defined in, and caches the data.

    :param file_name: the file name to open.
    :param nested_by: how many stack frames we are nested by. Only use this if
        you are implementing this routine as part of another routine.
    :param load_now: true if we should immediately cache. Defaults to False.
    :return: the config file object.
    """
    path = files.in_here(file_name, nested_by=1 + nested_by)
    cf = ConfigFile(path)

    if load_now:
        cf.sync_get()
    return cf


def get_config_data(file_name):
    """Quickly fetches the config data from the config directory."""
    return get_from_config_dir(file_name, load_now=False).sync_get()
