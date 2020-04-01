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
RNG utils.
"""
import random

import neko3.converters
from neko3 import neko_commands

MAX_ROLLS_PER_COMMAND = 200
MAX_SIDES_PER_DIE = (1 << 16) - 1


class RandomCog(neko_commands.Cog):
    @staticmethod
    async def _error(ctx, exception):
        await ctx.send(f"Invalid input: {exception}", delete_after=10)

    @neko_commands.command(name="toss", brief="Toss a coin")
    async def toss_command(self, ctx, n: int = 1):
        f"""Given a number of times between 1 and {MAX_ROLLS_PER_COMMAND}"""
        if 1 <= n <= MAX_ROLLS_PER_COMMAND:
            await ctx.send(", ".join(random.choice(("Heads", "Tails")) for _ in range(n)))
        else:
            await ctx.send("Invalid input")

    @neko_commands.command(name="pick", brief="Pick from a set of items")
    async def pick_command(self, ctx, *options: neko3.converters.clean_content):
        """
        Options are separated by spaces; to include spaces in an option,
        you should put quotes around the option.
        """
        if not options or len(options) == 1:
            await ctx.send("Provide two or more options")
        else:
            await ctx.send(random.choice(options))

    @neko_commands.command(name="roll", brief="Roll a die")
    async def roll_command(self, ctx, argument: neko3.converters.clean_content = "1d6"):
        """
        Provide the input as `xdy` where `x` is the number of times to roll,
        and `y` is the number of sides the die has. `d` is the literal character `d`.

        Defaults to `1d6`

        Will roll a maximum of 200 times, with a maximum of 65,536 sides.
        """
        output = []

        try:
            times, _, sides = argument.lower().partition("d")
            if not times:
                times = 1
            if not sides:
                sides = 6
            times, sides = abs(int(times)), abs(int(sides))

        except Exception as ex:
            return await self._error(ctx, ex)

        actual_times = min(MAX_ROLLS_PER_COMMAND, times) or 1
        if actual_times != times:
            output.append(f"Invalid number of rolls given, setting to {actual_times}")

        actual_sides = min(MAX_SIDES_PER_DIE, sides) or 1
        if actual_sides != sides:
            output.append(f"Invalid sides per die given, setting to {actual_sides}")

        if output:
            output.append("\n")

        rolls = [random.randint(1, actual_sides) for _ in range(actual_times)]
        str_rolls = map(str, rolls)
        output.append(", ".join(str_rolls))
        output.append(f"Total: {sum(rolls):,}")

        await ctx.send("\n".join(output))

    @neko_commands.group(name="random")
    async def random_group(self, ctx):
        """
        Special random number functions.

        See `roll`, `toss` and `pick` for general purpose functions.
        """
        await neko_commands.send_usage(ctx)

    @random_group.command(name="int", brief="Pick a random integer between the given bounds.")
    async def random_int_command(self, ctx, *arguments: int):
        """
        Takes two potential syntaxes:

        - randint max
            min = 0 (inclusive).
            max = max non inclusive value.

        - randint min max
            min = min inclusive value.
            max = max non inclusive value.

        Returns [min, max)
        """
        if 1 <= len(arguments) <= 2:
            if len(arguments) == 1:
                min, max = 0, arguments[0]
            else:
                min, max = arguments

            try:
                await ctx.send(random.randint(min, max))
            except Exception as ex:
                await self._error(ctx, ex)
        else:
            await ctx.send("Incorrect number of arguments passed")

    @random_group.command(name="range", brief="Pick a random integer between the given bounds.")
    async def random_range_command(self, ctx, *arguments: int):
        """
        Takes three potential syntaxes:

        - randrange max
            min = 0 (inclusive).
            max = max inclusive value.
            step = 1

        - randrange min max
            min = min inclusive value.
            max = max inclusive value.
            step = 1

        - randrange min max step
            min = min inclusive value.
            max = max inclusive value.
            step = step to increment by each time

        Returns [min, max]
        """
        if 1 <= len(arguments) <= 3:
            if len(arguments) == 1:
                min, max, step = 0, arguments[0], 1
            elif len(arguments) == 2:
                min, max = arguments
                step = 1
            else:
                min, max, step = arguments

            try:
                await ctx.send(random.randrange(min, max, step))
            except Exception as ex:
                await self._error(ctx, ex)
        else:
            return await ctx.send("Incorrect number of arguments passed")

    @random_group.command(name="real", brief="Random number in the range [0, 1)", aliases=["float", "double"])
    async def random_real_command(self, ctx):
        await ctx.send(random.random())

    @random_group.command(name="uniform", brief="Return a uniform random number", aliases=["uni"])
    async def random_uniform_command(self, ctx, a: float, b: float):
        """
        Return a random uniform floating point number N such that
        a ≤ N ≤ b (or a ≤ N < b, depending on the value of b given).

        Determined by a random value [0, 1) multiplied by a + (b - a)
        """
        try:
            await ctx.send(random.uniform(a, b))
        except Exception as ex:
            await self._error(ctx, ex)

    @random_group.command(name="triangular", brief="Return a random triangular number", aliases=["tri", "triangle"])
    async def random_triangular_command(self, ctx, low: float, high: float, mode: float = None):
        """
        Generate a random number in the range [low, high], with a specified mode
        between the bounds. The mode should be the median between the two bounds. This
        provides some skew if not at the midpoint. If mode is omitted, it is set to be the
        midpoint to give a symmetric distribution.
        """
        try:
            if mode is None:
                mode = (low + high) / 2
            await ctx.send(random.triangular(low, high, mode))
        except Exception as ex:
            await self._error(ctx, ex)

    @random_group.command(name="betavariate", brief="Return a random betavariate number", aliases=["beta"])
    async def random_beta_variate_command(self, ctx, alpha: float, beta: float):
        try:
            await ctx.send(random.betavariate(alpha, beta))
        except Exception as ex:
            await self._error(ctx, ex)

    @random_group.command(
        name="expovariate", brief="Return a random expovariate number", usage="lambda", aliases=["expo"]
    )
    async def random_expovariate_command(self, ctx, lambda_: float):
        """
        Exponential distribution. λ (lambda) is 1.0 divided by the desired mean.

        It should be nonzero.

        Returned values range from 0 to positive infinity if λ is positive, and
        from negative infinity to 0 if λ is negative.
        """
        try:
            await ctx.send(f"{random.expovariate(lambda_):,g}")
        except Exception as ex:
            await self._error(ctx, ex)

    @random_group.command(name="gammavariate", brief="Return a random gammavariate number", aliases=["gamma"])
    async def random_gamma_variate_command(self, ctx, alpha: float, beta: float):
        """
        Gamma distribution. (Not the gamma function!) Conditions on the parameters
        are α (alpha) > 0 and ß (beta) > 0.
        """
        try:
            await ctx.send(random.gammavariate(alpha, beta))
        except Exception as ex:
            await self._error(ctx, ex)

    @random_group.command(
        name="gauss", brief="Return a Gaussian distributed number", aliases=["gaussian", "guass", "guassian"]
    )
    async def random_gauss_command(self, ctx, mu: float, sigma: float):
        """
        Gaussian distribution such that µ (mu) is the mean and σ (sigma) is the
        standard deviation.
        """
        try:
            await ctx.send(random.gauss(mu, sigma))
        except Exception as ex:
            await self._error(ctx, ex)

    @random_group.command(
        name="lognormvariate",
        brief="Return a random log-normal distributed value",
        aliases=["lognorm", "lognormalvariate", "lognormal"],
    )
    async def random_log_normal_variate(self, ctx, mu: float, sigma: float):
        """
        If you take the natural logarithm of this distribution, you’ll get a normal
        distribution with mean µ (mu) and standard deviation σ (sigma). µ can have
        any value, and σ must be greater than zero.
        """
        try:
            await ctx.send(random.lognormvariate(mu, sigma))
        except Exception as ex:
            await self._error(ctx, ex)

    @random_group.command(name="vonmisesvariate", brief="Generate a random von Mises value.", aliases=["vonmises"])
    async def random_von_mises_variate_command(self, ctx, mu: float, kappa: float):
        """
        Mu is the mean angle, expressed in radians between 0 and 2*pi, and kappa is
        the concentration parameter, which must be greater than or equal to zero.
        If kappa is equal to zero, this distribution reduces to a uniform random
        angle over the range 0 to 2*pi.
        """
        try:
            await ctx.send(random.vonmisesvariate(mu, kappa))
        except Exception as ex:
            await self._error(ctx, ex)

    @random_group.command(name="paretovariate", brief="Return a random Pareto-distributed number", aliases=["pareto"])
    async def random_pareto_variate_command(self, ctx, alpha: float):
        """Alpha is the shape parameter"""
        try:
            await ctx.send(random.paretovariate(alpha))
        except Exception as ex:
            await self._error(ctx, ex)

    @random_group.command(
        name="weibullvariate", brief="Return a random Weibull-distributed number", aliases=["weibull"]
    )
    async def random_weibull_variate_command(self, ctx, alpha: float, beta: float):
        """Alpha is the scale parameter, beta is the shape."""
        try:
            await ctx.send(random.weibullvariate(alpha, beta))
        except Exception as ex:
            await self._error(ctx, ex)


def setup(bot):
    bot.add_cog(RandomCog())
