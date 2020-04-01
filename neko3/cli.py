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
Application entry point. This loads any modules, DMing the owner if there is
any error, and then starts the bot.

If a path is provided as the first argument, we look in this path directory
for any configuration files, otherwise, we assume ../neko2config.
"""
import asyncio
import logging
import os
import sys
import warnings

from neko3 import bot as client
from neko3 import configuration_files
from neko3 import logging_utils
from neko3 import module_detection

LOGGERS_TO_SUPPRESS = ["discord.http"]

SUPPRESS_TO_LEVEL = "FATAL"


def cli():
    NEKO3_TOKEN = os.environ["NEKO3_TOKEN"]
    NEKO3_CLIENT_ID = os.environ["NEKO3_CLIENT_ID"]
    NEKO3_OWNER_ID = os.environ["NEKO3_OWNER_ID"]
    NEKO3_PREFIX = os.getenv("NEKO3_PREFIX", "n.")
    
    config = dict(
        bot=dict(
            command_prefix=NEKO3_PREFIX,
            owner_id=int(NEKO3_OWNER_ID),
        ),
        auth=dict(
            client_id=NEKO3_CLIENT_ID,
            token=NEKO3_TOKEN,
        ),
        debug=False,
    )
    
    logging_kwargs = {
        "level": os.getenv("LOGGER_LEVEL", "INFO"),
        "format": "%(asctime)s.%(msecs)03d L:%(levelname)s M:%(module)s F:%(funcName)s: %(message)s",
        "datefmt": "%Y-%m-%d %H:%M:%S",
    }

    logging.basicConfig(**logging_kwargs)
    logger = logging.getLogger("neko3")

    for other_logger in LOGGERS_TO_SUPPRESS:
        other_logger = logging.getLogger(other_logger)
        other_logger.setLevel(SUPPRESS_TO_LEVEL)
    
    try:
        import uvloop
        uvloop.install()
        logging.info("Using uvloop for asyncio event loop")
    except:
        logging.info("Using default asyncio event loop")
        
    # Shuts up BeautifulSoup about every first world problem
    warnings.filterwarnings(action="ignore", category=UserWarning)

    loop = asyncio.get_event_loop()

    try:
        with client.Bot(loop, config) as bot:
            module_detection.ModuleDetectionService().auto_load_modules(bot)
            try:
                loop.run_until_complete(bot.run(bot.token))
            except client.BotInterrupt as ex:
                logger.critical(f"Received interrupt {ex}")
            except Exception as ex:
                logger.exception("An unrecoverable error occurred.", exc_info=ex)
            else:
                logger.info("The bot stopped executing as expected")

            try:
                if bot.logged_in:
                    loop.run_until_complete(bot.logout())
            except client.BotInterrupt:
                bot.logger.critical("Asked to shut down AGAIN, guess I will die")
            except Exception as ex:
                bot.logger.exception("Giving up all hope of a safe exit", exc_info=ex)
    finally:
        bot.logger.critical("Process is terminating NOW.")
