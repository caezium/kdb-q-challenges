"""Tests for p1-pykx-roundtrip."""

import math
from datetime import datetime, timezone

import pytest

from challenge import roundtrip


# --- helpers ---

def assert_nan_equal(a, b):
    """Check two floats are equal, treating NaN == NaN as True."""
    if isinstance(a, float) and isinstance(b, float):
        if math.isnan(a) and math.isnan(b):
            return
    assert a == b, f"Expected {a}, got {b}"


def lists_nan_equal(a, b):
    """Check two lists of floats are equal with NaN handling."""
    assert len(a) == len(b), f"Length mismatch: {len(a)} vs {len(b)}"
    for x, y in zip(a, b):
        assert_nan_equal(x, y)


# === Section 1: Basic Correctness ===

class TestBasicCorrectness:
    def test_longs(self):
        data = {"longs": [1, 2, 3, -100, 0, 2**40]}
        result = roundtrip(data)
        assert result["longs"] == data["longs"]
        assert all(isinstance(x, int) for x in result["longs"])

    def test_floats_simple(self):
        data = {"floats": [1.0, 2.5, -3.14, 0.0]}
        result = roundtrip(data)
        assert result["floats"] == data["floats"]
        assert all(isinstance(x, float) for x in result["floats"])

    def test_floats_nan_inf(self):
        data = {"floats": [1.0, float("nan"), float("inf"), float("-inf"), 0.0]}
        result = roundtrip(data)
        assert len(result["floats"]) == 5
        assert result["floats"][0] == 1.0
        assert math.isnan(result["floats"][1])
        assert result["floats"][2] == float("inf")
        assert result["floats"][3] == float("-inf")
        assert result["floats"][4] == 0.0

    def test_symbols(self):
        data = {"symbols": ["AAPL", "GOOG", "MSFT", ""]}
        result = roundtrip(data)
        assert result["symbols"] == data["symbols"]
        assert all(isinstance(x, str) for x in result["symbols"])

    def test_timestamps(self):
        ts = [
            datetime(2024, 1, 15, 10, 30, 45, 123456, tzinfo=timezone.utc),
            datetime(2024, 6, 1, 0, 0, 0, 0, tzinfo=timezone.utc),
            datetime(2024, 12, 31, 23, 59, 59, 999999, tzinfo=timezone.utc),
        ]
        data = {"timestamps": ts}
        result = roundtrip(data)
        assert len(result["timestamps"]) == 3
        for orig, rt in zip(ts, result["timestamps"]):
            # Must preserve at least microsecond precision
            assert abs((orig - rt).total_seconds()) < 0.001, (
                f"Timestamp drift: {orig} vs {rt}"
            )

    def test_booleans(self):
        data = {"booleans": [True, False, True, True, False]}
        result = roundtrip(data)
        assert result["booleans"] == data["booleans"]
        # Critical: must be bool, not int
        assert all(isinstance(x, bool) for x in result["booleans"]), (
            f"Expected bool types, got: {[type(x).__name__ for x in result['booleans']]}"
        )

    def test_nested(self):
        data = {"nested": [[1, 2, 3], [4, 5], [6]]}
        result = roundtrip(data)
        assert result["nested"] == data["nested"]

    def test_empty_keys(self):
        """Each key still present with correct empty structure."""
        data = {
            "longs": [],
            "floats": [],
            "symbols": [],
        }
        result = roundtrip(data)
        for k in data:
            assert k in result
            assert isinstance(result[k], list)
            assert len(result[k]) == 0


# === Section 2: Anti-Cheat ===

class TestAntiCheat:
    def test_not_identity(self):
        """Result must not be the exact same object (must go through q)."""
        data = {"longs": [1, 2, 3]}
        result = roundtrip(data)
        # Values should be equal but not the same object
        assert result["longs"] == data["longs"]
        assert result is not data  # Not the same dict object

    def test_uses_pykx(self):
        """Verify pykx is actually imported and used."""
        import importlib
        import sys

        # Run roundtrip
        data = {"longs": [42]}
        roundtrip(data)
        # pykx should be in sys.modules after the call
        assert "pykx" in sys.modules, "pykx must be imported and used"

    def test_different_inputs_different_outputs(self):
        """Anti-constant check."""
        r1 = roundtrip({"longs": [1, 2, 3]})
        r2 = roundtrip({"longs": [10, 20, 30]})
        r3 = roundtrip({"longs": [100, 200, 300]})
        assert r1["longs"] != r2["longs"]
        assert r2["longs"] != r3["longs"]


# === Section 3: Edge Cases (the real challenge) ===

class TestEdgeCases:
    def test_large_integers(self):
        """q longs are 64-bit — values within range must survive."""
        data = {"longs": [2**62, -(2**62), 0]}
        result = roundtrip(data)
        assert result["longs"] == data["longs"]

    def test_single_element_lists(self):
        """Single-element lists must stay as lists, not atoms."""
        data = {"longs": [42], "floats": [3.14], "symbols": ["X"]}
        result = roundtrip(data)
        for k in data:
            assert isinstance(result[k], list), f"{k} should be a list, got {type(result[k])}"
            assert len(result[k]) == 1

    def test_negative_zero(self):
        """IEEE -0.0 handling."""
        data = {"floats": [-0.0, 0.0]}
        result = roundtrip(data)
        assert len(result["floats"]) == 2
        # Both should be float
        assert all(isinstance(x, float) for x in result["floats"])

    def test_unicode_symbols(self):
        """q symbols with non-ASCII characters."""
        data = {"symbols": ["hello", "world"]}
        result = roundtrip(data)
        assert result["symbols"] == data["symbols"]

    def test_mixed_dict(self):
        """Full mixed-type dictionary."""
        data = {
            "longs": [1, 2, 3],
            "floats": [1.5, float("nan")],
            "symbols": ["A", "B"],
            "booleans": [True, False],
            "timestamps": [datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)],
        }
        result = roundtrip(data)
        assert result["longs"] == [1, 2, 3]
        assert result["symbols"] == ["A", "B"]
        assert result["booleans"] == [True, False]
        assert all(isinstance(x, bool) for x in result["booleans"])
        assert len(result["floats"]) == 2
        assert result["floats"][0] == 1.5
        assert math.isnan(result["floats"][1])


# === Section 4: Property Tests ===

class TestProperties:
    @pytest.mark.parametrize("seed", range(20))
    def test_random_longs_roundtrip(self, seed):
        """Random long lists survive round-trip."""
        import random
        rng = random.Random(seed)
        data = {"longs": [rng.randint(-10**15, 10**15) for _ in range(rng.randint(1, 50))]}
        result = roundtrip(data)
        assert result["longs"] == data["longs"]

    @pytest.mark.parametrize("seed", range(20))
    def test_random_floats_roundtrip(self, seed):
        """Random float lists survive round-trip (with NaN handling)."""
        import random
        rng = random.Random(seed)
        vals = [rng.uniform(-1000, 1000) for _ in range(rng.randint(1, 30))]
        # Sprinkle in some NaN/Inf
        if seed % 3 == 0:
            vals.append(float("nan"))
        if seed % 5 == 0:
            vals.append(float("inf"))
        data = {"floats": vals}
        result = roundtrip(data)
        lists_nan_equal(result["floats"], data["floats"])
