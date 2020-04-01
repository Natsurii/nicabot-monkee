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
Fuzzy-wuzzy fuzzy string matching utilities. Copied from several places and
rewritten so stuff makes sense to me.

Citations:
[1]: http://chairnerd.seatgeek.com/fuzzywuzzy-fuzzy-string-matching-in-python/
[2]: https://github.com/seatgeek/fuzzywuzzy (specifically the
fuzzywuzzy/fuzz.py
    and fuzzywuzzy/util.py files.
[3]: https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/utils/fuzzy.py
"""
import difflib  # Calculating string closeness
import heapq  # Built-in heap data-type.
import re  # Regex to match word boundaries.
import typing  # Type hinting.

__all__ = (
    "tokenize_sort",
    "float_to_ratio",
    "ratio",
    "quick_ratio",
    "real_quick_ratio",
    "deep_ratio",
    "sorted_token_ratio",
    "extract",
    "extract_best",
)

_word = re.compile(r"\w+")

# Function type for a ratio helper. Takes two strings and returns an int
# such that 0 <= int <= 100
_scorer = typing.Callable[[str, str], int]


def tokenize_sort(text: str) -> str:
    """
    Splits the input string up into words, discards any form of case
    sensitivity by casting to lower case, and then sorts each word
    lexicographically. The words are then rejoined by a single space.
    """
    tokens = _word.findall(text.lower())
    # In-place lexicographical sort.
    tokens.sort()
    return " ".join(tokens)


def float_to_ratio(value: float) -> int:
    """Casts to an int, but rounds to the nearest value first."""
    return int(round(value * 100))


def ratio(a: str, b: str) -> int:
    """
    Calculates string "closeness". This is only effective on short strings
    such as single words, or large strings such as multiple paragraphs, but
    is not as good for short word labels. It is very sensitive to missing words
    which is not great.

    Gets a ratio that represents how similar a is to b.
    This will be between 0 and 100, where 100 represents close match and
    0 represents little similarity.

    While more accurate than ``quick_ratio``, the documentation mentions the
    following:

        .ratio() is expensive to compute if you haven't already computed
        .get_matching_blocks() or .get_opcodes(), in which case you may
        want to try .quick_ratio() or .real_quick_ratio() first to get an
        upper bound.

    Thus, for work that requires quick throughput at the expense of accuracy,
    you should try ``quick_ratio`` instead.
    """
    float_ratio = difflib.SequenceMatcher(None, a, b).ratio()
    return float_to_ratio(float_ratio)


def quick_ratio(a: str, b: str) -> int:
    """
    Similar to ``ratio`` but less computationally expensive.

    It is defined to return a value within the upper bound of the result
    that ``ratio`` would normally provide.
    """

    float_ratio = difflib.SequenceMatcher(None, a, b).quick_ratio()
    return float_to_ratio(float_ratio)


def real_quick_ratio(a: str, b: str) -> int:
    """
    Similar to ``ratio`` but less computationally expensive than that, or
    ``quick_ratio``. It is even less accurate however.

    It is defined to return a value within the upper bound of the result
    that ``ratio`` would normally provide.
    """
    float_ratio = difflib.SequenceMatcher(None, a, b).real_quick_ratio()
    return float_to_ratio(float_ratio)


def best_partial(a: str, b: str) -> int:
    """
    Calculates the best partial string ratio between the first and second
    string by brute force checking the ratios for each matching block.
    """
    # Get the shortest and longest string.
    short, long = (a, b) if len(a) < len(b) else (b, a)

    # Get matching blocks. This is a collection of triplet tuples (i, j, n)
    # such that short[i:i+n] == long[j:j+n]
    short_long_matcher = difflib.SequenceMatcher(None, short, long)
    matching_blocks = short_long_matcher.get_matching_blocks()

    # Get the max score. We don't bother making it into an integer until the
    # end.
    max_float_ratio = 0.0

    for i, j, n in matching_blocks:
        # We look for the start index in the long string to substring from.
        start = max(j - i, 0)

        # The substring of the longer string we are interested in.
        sub_long = long[start : start + len(short)]

        block_matcher = difflib.SequenceMatcher(None, short, sub_long)

        max_float_ratio = max(max_float_ratio, block_matcher.ratio())

        # If we are approaching 1, then we should just return the value
        # now, as we are about as high as we are going to get.
        if 0.995 < max_float_ratio:
            break

    return float_to_ratio(max_float_ratio)


def deep_ratio(a: str, b: str) -> int:
    """
    A rather slow search that takes into account all four other matching
    ratio algorithms along with approximately how accurate they are.

    This works by reducing the percentage of scores as follows:

    - Partial = 25%
    - Ratio = 60%
    - Quick = 10%
    - Real Quick = 5%

    These are then summed to get the actual score.
    """

    partial = best_partial(a, b)
    normal = ratio(a, b)
    quick = quick_ratio(a, b)
    real_quick = real_quick_ratio(a, b)

    score = 0.25 * partial + 0.6 * normal + 0.1 * quick + 0.05 * real_quick

    return int(round(score))


def sorted_token_ratio(a: str, b: str, scorer: _scorer = quick_ratio) -> int:
    """
    Returns the ``scorer`` for a and b when the tokens are in lexicographical
    order.
    """
    return scorer(tokenize_sort(a), tokenize_sort(b))


_result_t = typing.Tuple[str, int]
_results_t = typing.Iterable[_result_t]


def _results_iterator(
    query: str, choices: typing.Iterable[str], *, scoring_algorithm: _scorer = quick_ratio, min_score: int = 0
) -> _results_t:
    """
    Generates an iterator of results for the given query out of the given
    choices.
    :param query: the query string input.
    :param choices: list of choices for matches we can pick from.
    :param scoring_algorithm: the scoring algorithm to use. Uses quick_ratio
        if unspecified.
    :param min_score: a score to cap at. If unspecified, this assumes zero.
    :return: an iterator over pair-tuples of the choice that matched, and the
        matching score. These will be in descending order of score.
    """
    for choice in choices:
        score = sorted_token_ratio(query, choice, scoring_algorithm)
        if score >= min_score:
            yield choice, score


def extract(
    query: str,
    choices: typing.Iterable[str],
    *,
    scoring_algorithm: _scorer = quick_ratio,
    min_score: int = 0,
    max_results: typing.Union[int, None] = 10,
) -> _results_t:
    """
    Extracts upto ``max_results`` of the best matches for ``query`` in the
    iterable ``choices`` using the ``scoring_algorithm`` and ignoring any
    scores less than ``min_score``.
    """

    it = _results_iterator(query, choices, scoring_algorithm=scoring_algorithm, min_score=min_score)

    def key(x):
        return x[1]

    # If we need the limit, construct a heap of the n largest elements first,
    # otherwise, we can just use the raw iterator.
    results = it if not max_results else heapq.nlargest(max_results, it, key=key)

    return sorted(results, reverse=True, key=key)


def extract_best(
    query: str, choices: typing.Iterable[str], *, scoring_algorithm: _scorer = quick_ratio, min_score: int = 0
) -> _result_t:
    """
    Extracts the best result for the query in the given choices... if there is
    one!
    """

    result = extract(query, choices, scoring_algorithm=scoring_algorithm, min_score=min_score, max_results=1)

    result = list(result)

    if result:
        return result[0]
