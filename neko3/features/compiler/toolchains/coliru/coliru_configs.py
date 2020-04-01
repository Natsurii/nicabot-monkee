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
Callable asynchronous compilers provided by Coliru.

Reverse engineered from: http://coliru.stacked-crooked.com/

https://docs.google.com/document/d/18md3rLdgD9f5Wro3i7YYopJBFb_6MPCO8-0ihtxHoyM
"""
import aiofiles
import aiohttp

import neko3.cog
from neko3 import files
from neko3 import logging_utils
from neko3 import singleton
from .api import *

# Thank asottile for this!
_asottile_base = "https://raw.githubusercontent.com/asottile"
_ffstring_url = _asottile_base + "/future-fstrings/master/future_fstrings.py"
_trt_url = _asottile_base + "/tokenize-rt/master/tokenize_rt.py"
_replify_path = files.in_here("replify.py")


class GlobalResourceManager(logging_utils.Loggable, metaclass=singleton.SingletonMeta):
    def __init__(self):
        self._ffstrings = None
        self._trt = None
        self._replify = None

    async def obtain_ffstrings(self):
        if self._ffstrings is None:
            async with aiohttp.ClientSession() as session:
                async with session.get(_ffstring_url) as resp:
                    self.logger.info("Fetching %s", _ffstring_url)
                    resp.raise_for_status()
                    self._ffstrings = await resp.text()
        return self._ffstrings

    async def obtain_trt(self):
        if self._trt is None:
            async with aiohttp.ClientSession() as session:
                async with session.get(_trt_url) as resp:
                    self.logger.info("Fetching %s", _trt_url)
                    resp.raise_for_status()
                    self._trt = await resp.text()
        return self._trt

    async def obtain_replify(self):
        if self._replify is None:
            async with aiofiles.open(_replify_path) as fp:
                self._replify = await fp.read()
        return self._replify


# Maps human readable languages to their syntax highlighting strings.
languages = {}
# Maps a language or syntax highlighting option to the docstring.
docs = {}
# Maps a language or syntax highlighting option
targets = {}


def register(*names, language):
    import inspect

    def decorator(coro):
        languages[language.lower()] = [coro.__name__]

        unclean = inspect.getdoc(coro)

        if not unclean:
            unclean = "No detailed info exists for this right now."
        clean = inspect.cleandoc(unclean)

        docs[language] = clean

        for n in {coro.__name__, *names}:
            targets[n] = coro
            docs[n] = clean
            languages[language.lower()].append(n)

        return coro

    return decorator


@register(language="C")
async def c(source):
    """LLVM Clang C compiler

    Note that this will compile with the `-Wall`, `-Wextra`, `-Wpedantic`,
    `-std=c11`, and `-O0` flags.

    Example:
    ```c
    #include <stdio.h>

    int main(void) { printf("Hello, World!\n"); }
    ```

    Pragmas:
    
    Neko supports a few pragmas to enable some flags and features.
    Each have the syntax `#pragma neko [flag]`
    
    - `32` - force 32 bit binary output (default is 64 bit).
    - `asm` - dump assembly output.
    - `gcc` - compile under `gcc`. The default is to use `clang`.
    - `math` - compile with `-lm`.
    - `pthread` - compile with `-lpthread`.
    """
    script = "-Wall -Wextra -Wno-unknown-pragmas -pedantic -g -O0 -std=c11 -o a.out app.c "

    lines = source.split("\n")

    if "#pragma neko math" in lines:
        script += "-lm "

    if "#pragma neko pthread" in lines:
        script += "-lpthread "

    if "#pragma neko 32" in lines:
        script += "-m32 "

    if "#pragma neko gcc" not in lines:
        if not source.endswith("\n"):
            source += "\n"
        compiler = "clang "
    else:
        compiler = "gcc "

    if "#pragma neko asm" in lines:
        script += " -S -Wa,-ashl"
        execute = "cat -n ./a.out"
    else:
        execute = "./a.out"

    compiler_invocation = compiler + script

    main = SourceFile("app.c", source)
    make = SourceFile("Makefile", f"all:\n    {compiler_invocation}\n    {execute}\n")

    cc = Coliru("make -f Makefile", make, main)

    async with aiohttp.ClientSession() as cs:
        return await cc.execute(cs)


@register("c++", "cc", language="C++")
async def cpp(source):
    """GNU C++ compiler

    Note that this will compile with the `-Wall`, `-Wextra`, `-Wpedantic`,
    `-O0`, and `-std=c++2a`.

    Example:
    ```cpp
    #include <iostream>

    int main() { std::cout << "Hello, World!" << std::endl; }
    ```
    
    Pragmas:
    
    Neko supports a few pragmas to enable some flags and features.
    Each have the syntax `#pragma neko3 [flag]`
    
    - `32` - force 32 bit binary output (default is 64 bit).
    - `asm` - dump assembly output.
    - `fs` - compile with the `-lstdc++fs` flag.
    - `math` - compile with `-lm`.
    - `pthread` - compile with `-lpthread`.
    """
    script = "-Wall -Wextra -Wno-unknown-pragmas -pedantic -g -O0 -std=c++2a -o a.out app.cpp "

    lines = source.split("\n")

    if "#pragma neko3 fs" in lines:
        script += "-lstdc++fs "

    if "#pragma neko3 math" in lines:
        script += "-lm "

    if "#pragma neko3 pthread" in lines:
        script += "-lpthread "

    if "#pragma neko3 32" in lines:
        script += "-m32 "

    script += "-std=c++2a "
    compiler = "g++ "

    if "#pragma neko asm" in lines:
        script += " -S -Wa,-ashl"
        execute = "cat -n ./a.out"
    else:
        execute = "./a.out"

    compiler_invocation = compiler + script

    main = SourceFile("app.cpp", source)
    make = SourceFile("Makefile", f"all:\n    {compiler_invocation}\n    {execute}\n")

    cc = Coliru("make -f Makefile", make, main)
    async with aiohttp.ClientSession() as session:
        return await cc.execute(session)


@register("python2.7", "py2", "py2.7", language="Python2")
async def python2(source):
    """Python2.7 Interpreter

    Example:
    ```python
    print 'Hello, World'
    ```
    """
    script = 'python main.py; echo "Returned $?"'
    cc = Coliru(script, SourceFile("main.py", source))
    async with aiohttp.ClientSession() as cs:
        return await cc.execute(cs)


@register("python3", "python3.5", "py", "py3", "py3.5", language="Python")
async def python(source):
    """Python3.5 Interpreter (complete with f-string backport support!)

    Example:
    ```python
    print('Hello, World')
    ```
    
    Add the `# repl` comment as the first line to enable interactive
    interpreter behaviour (I am still working on this, so 

    See <https://github.com/asottile/future-fstrings> and
    <https://github.com/asottile/tokenize-rt> for more details on
    how the f-string support is backported and implemented.
    """
    async with aiohttp.ClientSession() as cs:

        manager = GlobalResourceManager()

        source_files = [
            SourceFile("main.py", source),
            SourceFile("tokenize_rt.py", await manager.obtain_trt()),
            SourceFile("future_fstrings.py", await manager.obtain_ffstrings()),
        ]

        if any(source.strip().startswith(x) for x in ("#repl\n", "# repl\n", "#repr\n", "# repr\n")):
            source_files.append(SourceFile("replify.py", await manager.obtain_replify()))
            script = (
                'echo "Trying experimental REPL support!"; '
                "python3.5 future_fstrings.py main.py | python3.5 replify.py; "
                'echo "Returned $?"'
            )
        else:
            script = "python3.5 future_fstrings.py main.py | python3.5; " 'echo "Returned $?"'

        cc = Coliru(script, *source_files)

        return await cc.execute(cs)


@register("pl", language="PERL 5")
async def perl(source):
    """PERL interpreter (PERL5)

    Example:
    ```perl
    use warnings;
    use strict;

    my @a = (1..10);
    my $sum = 0;

    $sum += $_ for @a;
    print $sum;
    print "\n";
    ```
    """
    async with aiohttp.ClientSession() as cs:
        script = "perl main.pl"
        cc = Coliru(script, SourceFile("main.pl", source))
        return await cc.execute(cs)


@register("irb", language="Ruby")
async def ruby(source):
    """Ruby interpreter.

    Example
    ```ruby
    def translate str
      alpha = ('a'..'z').to_a
      vowels = %w[a e i o u]
      consonants = alpha - vowels

      if vowels.include?(str[0])
        str + 'ay'
      elsif consonants.include?(str[0]) && consonants.include?(str[1])
        str[2..-1] + str[0..1] + 'ay'
      elsif consonants.include?(str[0])
        str[1..-1] + str[0] + 'ay'
      else
        str # return unchanged
      end
    end

    puts translate 'apple' # => "appleay"
    puts translate 'cherry' # => "errychay"
    puts translate 'dog' # => "ogday"
    ```
    """
    script = "ruby main.rb"
    cc = Coliru(script, SourceFile("main.rb", source))
    async with aiohttp.ClientSession() as cs:
        return await cc.execute(cs)


@register("shell", language="Shell")
async def sh(source):
    """Shell interpreter.

    Example
    ```sh
    yes but bash is still better imo
    ```
    """
    script = 'sh main.sh; echo "Returned $?"'
    cc = Coliru(script, SourceFile("main.sh", source))
    async with aiohttp.ClientSession() as cs:
        return await cc.execute(cs)


@register(language="Bash")
async def bash(source):
    """Bash interpreter

    Example
    ```bash
    yes i like bash ok
    ```
    """
    script = 'bash main.sh; echo "Returned $?"'
    cc = Coliru(script, SourceFile("main.sh", source))
    async with aiohttp.ClientSession() as cs:
        return await cc.execute(cs)


# Fortran libs are missing... go figure.

# @register('gfortran', 'f08', language='Fortran 2008')
async def fortran(source):
    """GNU Fortran Compiler (most recent standard)

    This compiles the given code to Fortran using the 2008 standard.

    For support for F95 and F90, see the help for `Fortran 1990` and
    `Fortran 1995`.

    Example:
    ```fortran
    PROGRAM    Fibonacci
        IMPLICIT   NONE
        INTEGER :: FIRST, SECOND, TEMP, IX
        FIRST = 0
        SECOND = 1
        WRITE (*,*) FIRST
        WRITE (*,*) SECOND
        DO IX = 1, 45, 1
            TEMP = FIRST + SECOND
            FIRST = SECOND
            SECOND = TEMP
            WRITE (*,*) TEMP
        END DO
    END PROGRAM Fibonacci
    ```
    """
    script = 'gfortran main.f08 && ./a.out; echo "Returned $?"'
    cc = Coliru(script, SourceFile("main.f08", source))
    async with aiohttp.ClientSession() as cs:
        return await cc.execute(cs)


# @register('gfortran90', 'f90', language='Fortran 1990')
async def fortran90(source):
    """GNU Fortran Compiler (1990 Standard)

    Example:
    ```fortran
    PROGRAM    Fibonacci
        IMPLICIT   NONE
        INTEGER :: FIRST, SECOND, TEMP, IX
        FIRST = 0
        SECOND = 1
        WRITE (*,*) FIRST
        WRITE (*,*) SECOND
        DO IX = 1, 45, 1
            TEMP = FIRST + SECOND
            FIRST = SECOND
            SECOND = TEMP
            WRITE (*,*) TEMP
        END DO
    END PROGRAM Fibonacci
    ```
    """
    script = 'gfortran main.f90 && ./a.out; echo "Returned $?"'
    cc = Coliru(script, SourceFile("main.f90", source))
    async with aiohttp.ClientSession() as cs:
        return await cc.execute(cs)


# @register('gfortran95', 'f95', language='Fortran 1995')
async def fortran95(source):
    """GNU Fortran Compiler (1995 Standard)

    Example:
    ```fortran
    PROGRAM    Fibonacci
        IMPLICIT   NONE
        INTEGER :: FIRST, SECOND, TEMP, IX
        FIRST = 0
        SECOND = 1
        WRITE (*,*) FIRST
        WRITE (*,*) SECOND
        DO IX = 1, 45, 1
            TEMP = FIRST + SECOND
            FIRST = SECOND
            SECOND = TEMP
            WRITE (*,*) TEMP
        END DO
    END PROGRAM Fibonacci
    ```
    """
    script = 'gfortran main.f95 && ./a.out; echo "Returned $?"'
    cc = Coliru(script, SourceFile("main.f95", source))
    async with aiohttp.ClientSession() as cs:
        return await cc.execute(cs)


@register("gawk", language="GNU Awk")
async def awk(source):
    """GNU AWK interpreter.

    Example:
    ```awk
    function factorial(n, i, f) {
        f = n
        while (--n > 1)
            f *= n
        return f
    }

    BEGIN { for (i=1; i<20; i++) print i, factorial(i) }
    ```
    """
    script = 'awk -f main.awk; echo "Returned $?"'
    cc = Coliru(script, SourceFile("main.awk", source))
    async with aiohttp.ClientSession() as cs:
        return await cc.execute(cs)


@register(language="Lua")
async def lua(source):
    """Lua interpreter.

    Example:
    ```lua
    function factorial(n)
        if (n == 0) then
            return 1
        else
            return n * factorial(n - 1)
        end
    end

    for n = 0, 16 do
        io.write(n, "! = ", factorial(n), "\n")
    end
    ```
    """
    script = 'lua main.lua; echo "Returned $?"'
    cc = Coliru(script, SourceFile("main.lua", source))
    async with aiohttp.ClientSession() as cs:
        return await cc.execute(cs)


@register("makefile", language="GNU Make")
async def make(source):
    """GNU-make.

    Allows you to write a basic Makefile and execute it. Note that Makefiles
    require tab indentation to work. The workaround for this drawback is to
    use four-space indentation in your code. I will then convert it to tab
    indentation for you before running it.

    Example:
    ```makefile
    CC := clang
    CFLAGS := -Wall -Wextra -pedantic -Werror -std=c11 -ggdb -gdwarf-2 -O0
    OUT := foo.out
    INFILES := main.c foo.c bar.c baz.c
    OBJFILES := $(subst .c,.o,$(INFILES))

    all: $(OBJFILES)
        $(CC) $(CFLAGS) -o $(OUT) $(OBJFILES)

    %.o: %.c %.h
        $(CC) $(CFLAGS) -o $@ -c $<

    clean:
        $(RM) *.o *.out -Rvf

    rebuild: clean all

    .PHONY: all clean rebuild
    ```
    """
    script = 'make -f Makefile; echo "Returned $?"'
    cc = Coliru(script, SourceFile("Makefile", source))
    async with aiohttp.ClientSession() as cs:
        return await cc.execute(cs)
