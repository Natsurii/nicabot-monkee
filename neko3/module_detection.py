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
Modules to load internally.
"""
import importlib
import inspect
import pkgutil
import typing

from neko3 import algorithms
from neko3 import logging_utils
from neko3 import properties
from neko3 import singleton

DEFAULT_START = "neko3.features"


class ModuleDetectionService(logging_utils.Loggable, metaclass=singleton.SingletonMeta):
    @properties.cached_property()
    def extension_candidates(self) -> typing.List[str]:
        queue = [importlib.import_module(DEFAULT_START)]
        successful_candidates = []

        while queue:
            module = queue.pop(0)

            if inspect.isfunction(getattr(module, "setup", None)):
                successful_candidates.append(module.__name__)
                self.logger.debug("%s is a valid extension", module.__name__)
            else:
                self.logger.debug("%s is not a valid extension", module.__name__)

            if hasattr(module, "__path__"):
                for _, fqn, is_package in pkgutil.walk_packages(module.__path__, prefix=f"{module.__name__}."):
                    try:
                        queue.append(importlib.import_module(fqn))
                    except Exception as ex:
                        self.logger.exception("Failed to import %s", fqn, exc_info=ex)

        return successful_candidates

    def auto_load_modules(self, bot) -> typing.List[typing.Tuple[BaseException, str]]:
        """
        Auto-loads any modules into the given bot.

        If any extensions fail to load, then we do not halt. A traceback is printed
        and we continue. Any errors are returned in a collection of 2-tuples paired
        with the name of the corresponding extension that caused the error.
        """
        errors = []
        modules = self.extension_candidates

        if not modules:
            self.logger.warning("No modules were discovered.")
        else:
            with algorithms.TimeIt() as overall_timer:
                for module in modules:
                    try:
                        with algorithms.TimeIt() as timer:
                            bot.load_extension(module)
                    except KeyboardInterrupt as ex:
                        raise ex from None
                    except Exception as ex:
                        self.logger.exception(f"Failed to load extension {module}", exc_info=ex)
                        errors.append((ex, module))
                    else:
                        self.logger.info(f"Loaded module {module} in {timer.time_taken * 1000:,.2f}ms")
            self.logger.info(
                f"Loaded {len(modules) - len(errors)}/{len(modules)} "
                f"modules successfully in {overall_timer.time_taken * 1000:,.2f}ms. Bot now has {len(bot.extensions)} "
                f"extensions loaded, with a total of {len(bot.cogs)} cogs and {len(bot.all_commands)} commands! "
                f"Will now start bot."
            )
        return errors
