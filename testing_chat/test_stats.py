# tests/test_stats.py
import math
import random

from testing_chat.stats import median

def test_median_odd_count():
    assert median([3, 1, 2]) == 2
    assert median([5, 7, 1]) == 5
    assert median([10]) == 10

def test_median_even_count_simple():
    # Correct median is average of middle two after sorting.
    assert median([1, 3, 2, 4]) == 2.5
    assert median([10, 2, 4, 6]) == 5.0

def test_median_even_count_unsorted_negatives():
    assert median([0, -2, -1, 5]) == (-1 + 0) / 2  # -0.5

def test_raises_on_empty():
    import pytest
    with pytest.raises(ValueError):
        median([])

def test_property_random_even_lists():
    # Basic property: for even n, result should be average of the two middle elems
    # of the sorted list.
    for _ in range(50):
        n = 2 * random.randint(1, 10)
        xs = [random.randint(-100, 100) for _ in range(n)]
        s = sorted(xs)
        expected = (s[n//2 - 1] + s[n//2]) / 2
        assert median(xs) == expected
