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
Compiler/interpreter for CRAN-R.

Reverse engineered from the online https://rdrr.io CRAN-R interpreter.
"""
import asyncio
import base64
import json
from dataclasses import dataclass
from typing import List
from typing import Optional
from typing import Tuple

import aiohttp
import async_timeout

HOST = "https://rdrr.io"

INVOKE_EP = "/snippets/run"
INVOKE_REQ = "POST"

RETRIEVE_EP = "/snippets/get/"
RETRIEVE_REQ = "GET"


@dataclass()
class CranRResult:
    fail_reason: Optional[str]
    state: str
    result: str
    images: List[Tuple[bytes, str]]  # Bytes against string type.
    output: str


async def eval_r(source: str, timeout=60, polling_pause=1):
    """
    Evaluates the given R code asynchronously and returns a CranRResult if
    we complete the task within the given time frame.
    :param session: the client session for aiohttp to use.
    :param source: source to evaluate.
    :param timeout: timeout to die after (default is 1 minute)
    :param polling_pause: the rate to poll at in seconds. Defaults to 1.
    :return: CranRResult object.
    """
    async with aiohttp.ClientSession() as session:
        transmit = await session.request(
            INVOKE_REQ,
            f"{HOST}{INVOKE_EP}",
            data=json.dumps({"csrfmiddlewaretoken": None, "input": source}),  # Not sure what this is for.
        )

        # Raise errors if there are any.
        transmit.raise_for_status()

        # Tells us the end point to go collect our data from.
        first_response = await transmit.json()

        if any(f not in first_response for f in ("_id", "result")):
            raise RuntimeError(f"Unexpected response: {first_response}")

        identifier = first_response["_id"]

        result_url = f"{HOST}{RETRIEVE_EP}{identifier}"

        # The job will be running in the background. We should keep checking
        # for a given period of time before giving up.
        with async_timeout.timeout(timeout):
            while True:  # Breaks by asyncio.TimeoutError eventually.
                async with session.request(RETRIEVE_REQ, result_url) as resp:
                    resp.raise_for_status()
                    second_response = await resp.json()

                if second_response["state"] == "complete":
                    break
                elif second_response["result"] == "failure":
                    break
                else:
                    await asyncio.sleep(polling_pause)

    # Decipher images from base 64 into raw bytes. Yes, this is blocking,
    # but it should be a fairly fast operation to perform.
    images = []
    for image in second_response["images"]:
        b64 = image["$binary"]
        image_type = image["$type"]  # TODO: find out what this means.
        byte_data = base64.b64decode(b64)
        images.append((byte_data, image_type))

    return CranRResult(
        second_response["failReason"],
        second_response["state"],
        second_response["result"],
        images,
        second_response["output"],
    )


# Just like for Coliru. Unit testing time.
if __name__ == "__main__":
    source = "\n".join(
        (
            "library(ggplot2)",
            "",
            "# Use stdout as per normal...",
            'print("Hello, world!")',
            "",
            "# Use plots...",
            "plot(cars)",
            "",
            "# Even ggplot!",
            "qplot(wt, mpg, data=mtcars, colour=factor(cyl))",
            "",
            "",
        )
    )

    async def run():
        import aiohttp

        session = aiohttp.ClientSession()

        return await eval_r(session, source)

    print(asyncio.run(run(), debug=True))
