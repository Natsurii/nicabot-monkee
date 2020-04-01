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
Reverse-polish-notation parser.
"""
import base64
import hashlib
import math
import re
from decimal import Decimal
from typing import Any
from typing import Union

from neko3 import neko_commands

binary_operations = {
    "+": lambda a, b: a + b,
    "-": lambda a, b: a - b,
    "*": lambda a, b: a * b,
    "/": lambda a, b: a / b,
    "div": lambda a, b: a / b,
    "idiv": lambda a, b: a // b,
    "//": lambda a, b: a // b,
    "%": lambda a, b: a % b,
    "**": lambda a, b: a ** b,
    "|": lambda a, b: int(a) | int(b),
    "&": lambda a, b: int(a) & int(b),
    "^": lambda a, b: int(a) ^ int(b),
    "<<": lambda a, b: int(a) << int(b),
    "bsl": lambda a, b: int(a) << int(b),
    ">>": lambda a, b: int(a) >> int(b),
    "bsr": lambda a, b: int(a) >> int(b),
    "<": lambda a, b: 1 if a < b else 0,
    ">": lambda a, b: 1 if a > b else 0,
    "<=": lambda a, b: 1 if a <= b else 0,
    ">=": lambda a, b: 1 if a >= b else 0,
    "==": lambda a, b: 1 if a == b else 0,
    "!=": lambda a, b: 1 if a != b else 0,
    "<>": lambda a, b: 1 if a != b else 0,
    "&&": lambda a, b: 1 if a and b else 0,
    "and": lambda a, b: 1 if a and b else 0,
    "||": lambda a, b: 1 if a or b else 0,
    "or": lambda a, b: 1 if a or b else 0,
    "gcd": lambda a, b: math.gcd(int(a), int(b)),
    "hypot": lambda a, b: math.hypot(float(a), float(b)),
}

unary_operations = {
    "!": lambda x: 0 if int(x) else 1,
    "~": lambda x: ~int(x),
    "floor": math.floor,
    "ceil": math.ceil,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "sec": lambda x: 1.0 / math.cos(x),
    "cosec": lambda x: 1.0 / math.sin(x),
    "cot": lambda x: 1.0 / math.tan(x),
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "asec": lambda x: 1.0 / math.acos(x),
    "acosec": lambda x: 1.0 / math.asin(x),
    "acot": lambda x: 1.0 / math.atan(x),
    "exp": math.exp,
    "log": math.log,
    "ln": math.log1p,
    "log2": math.log2,
    "gamma": math.gamma,
    "lgamma": math.lgamma,
    "abs": abs,
    "sqrt": lambda n: n ** 1 / 2,
}


def format_unary_operator_example(op):
    return f"`{op}x`" if not op.isalnum() else f"`{op}(x)`"


specials = dict(
    pi=Decimal(math.acos(-1.0)),
    π=Decimal(math.acos(-1.0)),
    e=Decimal(1).exp(),
    tau=2 * Decimal(math.acos(-1.0)),  # 2 pi
    τ=2 * Decimal(math.acos(-1.0)),
    c=299_792_458,  # speed of light
    G=Decimal(6.67408e-11),  # Gravitational constant
    epsilon0=Decimal(8.854_187_817e-12),  # permitivity of free space
    ε0=Decimal(8.854_187_817e-12),
    g=Decimal(9.81),
    nice=69,
    lit=420,
)

bases = {
    "hex": hex,
    "fp-hex": lambda n: float(n).hex(),
    "dec": int,
    "oct": oct,
    "bin": bin,
    "bool": bool,
    "b32be": lambda n: base64.b32encode(int(n).to_bytes((n.bit_length() + 7) // 8, "big")).decode("utf-8"),
    "b64be": lambda n: base64.b64encode(int(n).to_bytes((n.bit_length() + 7) // 8, "big")).decode("utf-8"),
    "b32le": lambda n: base64.b32encode(int(n).to_bytes((n.bit_length() + 7) // 8, "little")).decode("utf-8"),
    "b64le": lambda n: base64.b64encode(int(n).to_bytes((n.bit_length() + 7) // 8, "little")).decode("utf-8"),
    "md5": lambda n: hashlib.md5(str(n).encode("utf-8")).hexdigest(),
}

binary_regex = re.compile(r"[+-]?0[bB]\d+")
octal_regex = re.compile(r"[+-]?0[oO]\d+")
hexadecimal_regex = re.compile(r"[+-]?0[xX]\d+")


def tokenize(*chunks) -> Union[str, Decimal, int]:
    """
    Returns an iterable of tokens to parse left-to-right from an
    iterable of string chunks. Each chunk is a token.
    """
    for token in chunks:
        try:
            if binary_regex.match(token):
                token = int(token, 2)
            elif octal_regex.match(token):
                token = int(token, 8)
            elif hexadecimal_regex.match(token):
                token = int(token, 16)

            yield Decimal(token)
        except Exception:
            yield token


def parse(tokens) -> Union[Union[str, float, int, Decimal, Decimal], Any]:
    """
    Attempts to parse the tokens. If successful, we return the result value.
    """
    if not tokens:
        raise ValueError("Please provide some input.")

    stack = []
    pos = 0
    token = None

    try:
        for pos, token in enumerate(tokens):
            if isinstance(token, (float, int, Decimal)):
                stack.append(token)
            else:
                try:
                    # Constant:
                    stack.append(specials[token])
                except KeyError:
                    # Operator:
                    try:

                        try:
                            op = binary_operations[token]

                            right, left = stack.pop(), stack.pop()
                            stack.append(Decimal(op(left, right)))
                        except KeyError:
                            op = unary_operations[token]
                            value = stack.pop()
                            stack.append(Decimal(op(value)))
                    except ZeroDivisionError:
                        stack.append(float("nan"))

        if len(stack) != 1:
            return "Too many values. Perhaps you missed an operator?"
        else:
            return stack.pop()

    except IndexError:
        return (
            "Pop from empty stack. Perhaps you have too many operators? "
            f"(At token {pos + 1} of {len(tokens)}: {token!r})"
        )
    except KeyError:
        return f"Operator was unrecognised. (At token {pos + 1} of " f"{len(tokens)}: {token!r})"
    except Exception:
        return "Error"


class ReversePolishCog(neko_commands.Cog):
    @neko_commands.command(name="rpn", aliases=["postfix"], brief="Parses the given reverse polish notation.")
    async def rpn_command(self, ctx, *expression):
        """
        Executes the given reverse polish (postfix) notation expression.

        Note that only binary operators are currently supported. Run
        with the `help` argument for the expression to view what is
        supported.

        For example:
            12 22 /
        will result in the infix expression:
            12 / 22

        5th May 2018: now evaluates expressions in the right order.
            Division and mod operations are no longer inverted.
            Division by zero errors are now handled.
        """
        if len(expression) == 0 or len(expression) == 1 and expression[0].lower() == "help":
            await ctx.send(
                "Supported Operators:\n"
                + ", ".join(sorted(f"`x {o} y`" for o in binary_operations))
                + ", "
                + ", ".join(sorted(map(format_unary_operator_example, unary_operations)))
                + "\n\n"
                + "Supported Constants:\n"
                + ", ".join(sorted(f"`{c}`" for c in specials))
                + "\n\n"
                + "You may place an optional cast as the leftmost operand. Supported conversions are:\n"
                + ", ".join(f"`{b}`" for b in bases)
            )
        else:
            tokens = list(tokenize(*expression))

            if len(tokens) > 1 and tokens[0] in bases:
                base = tokens.pop(0)
            else:
                base = None

            result = parse(tokens)

            if base is not None:
                result = int(result)

                result = bases[base](result)

            result = str(result)
            if len(result) > 2000:
                result = result[:1996] + "..."

            await ctx.send(result)


def setup(bot):
    bot.add_cog(ReversePolishCog())
