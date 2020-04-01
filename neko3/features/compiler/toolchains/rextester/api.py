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
Rextester API implementation.

Reverse engineered from: http://rextester.com/
"""
import asyncio
import base64
import collections
import enum
import json
from dataclasses import dataclass
from typing import List

import aiohttp

# Forces simple editor in any response. Not really relevant, but required
# nonetheless. Layout forces vertical layout. Again, doesn't have much
# relevance to what we are doing.
EDITOR = 3
LAYOUT = 1

# Code endpoint to post to
ENDPOINT = "https://rextester.com/rundotnet/Run"


# view-source:http://rextester.com/l/common_lisp_online_compiler:466
class Language(enum.IntEnum):
    """
    Language opcodes to specify which language to execute.
    """

    csharp = 1
    visual_basic = 2
    fsharp = 3
    java = 4
    python2 = 5
    gccc = 6
    gcccpp = 7
    php = 8
    pascal = 9
    objc = 10
    haskell = 11
    ruby = 12
    perl = 13
    lua = 14
    assembly = 15
    sqlserver = 16
    clientside_javascript = 17
    commonlisp = 18
    prolog = 19
    go = 20
    scala = 21
    scheme = 22
    nodejs = 23
    python3 = 24
    octave = 25
    clangc = 26
    clangcpp = 27
    visualcpp = 28
    visualc = 29
    d = 30
    r = 31
    tcl = 32
    mysql = 33
    postgresql = 34
    oracle = 35
    html = 36
    swift = 37
    bash = 38
    ada = 39
    erlang = 40
    elixir = 41
    ocaml = 42
    kotlin = 43
    brainfuck = 44
    fortran = 45

    sql = postgresql
    cpp = gcccpp
    c = gccc
    python = python3
    py = python
    js = nodejs
    javascript = nodejs
    clientside_js = clientside_javascript


@dataclass(repr=True)
class RextesterResponse:
    warnings: str
    errors: str
    files: List[bytes]
    stats: str
    result: str


COMPILER_ARGS = collections.defaultdict(
    lambda: "",
    {
        Language.haskell: "-o a.out source_file.hs",
        Language.gccc: "-o a.out source_file.c",
        Language.gcccpp: "-o a.out source_file.cpp",
        Language.clangc: "-o a.out source_file.c",
        Language.clangcpp: "-o a.out source_file.cpp",
        Language.visualc: "-o a.exe source_file.c",
        Language.visualcpp: "-o a.exe source_file.cpp",
        Language.go: "-o a.out source_file.go",
    },
)

SOURCE_TRANSFORMATIONS = collections.defaultdict(lambda: lambda source: source, {})


async def execute(lang: Language, source: str, compiler_args: str = None) -> RextesterResponse:
    """
    Executes the given source code as the given language under rextester
    :param sesh: the aiohttp session to use.
    :param lang: the language to compile as.
    :param source: the source to compile.
    :param compiler_args: optional compiler args. Only applicable for C/C++
    :return: the response.
    """
    transformer = SOURCE_TRANSFORMATIONS[lang.value]
    source = transformer(source)

    form_args = {
        "LanguageChoiceWrapper": lang.value,
        "EditorChoiceWrapper": EDITOR,
        "LayoutChoiceWrapper": LAYOUT,
        "Program": source,
        "Input": "",
        "ShowWarnings": True,
        "Privacy": "",
        "PrivacyUsers": "",
        "Title": "",
        "SavedOutput": "",
        "WholeError": "",
        "WholeWarning": "",
        "StatsToSave": "",
        "CodeGuid": "",
    }

    if compiler_args:
        form_args["CompilerArgs"] = compiler_args
    else:
        form_args["CompilerArgs"] = COMPILER_ARGS[lang]

    async with aiohttp.ClientSession() as session:
        async with session.post(ENDPOINT, data=form_args) as resp:
            resp.raise_for_status()
            data = await resp.text()
            try:
                data = json.loads(data)
            except Exception as ex:
                raise RuntimeError(
                    f"Failed to decode {lang}; response was "
                    f"{resp.status} {resp.reason}: {data} {ex}\n\nSource was: {source}"
                )

    return RextesterResponse(
        data["Errors"],
        data["Warnings"],
        list(map(base64.b64decode, (data["Files"] or {}).values())),
        data["Stats"],
        data["Result"],
    )


if __name__ == "__main__":
    loop = asyncio.get_event_loop()

    async def test():
        async with aiohttp.ClientSession() as cs:
            r = await execute(
                cs,
                Language.csharp,
                """
                using System;
                using System.Collections.Generic;
                using System.Linq;
                using System.Text.RegularExpressions;
                
                namespace Rextester
                {
                    public class Program
                    {
                        public static void Main(string[] args)
                        {
                            Console.WriteLine("Hello, world!");
                        }
                    }
                }
                """,
            )

            print(repr(r))

    loop.run_until_complete(test())
