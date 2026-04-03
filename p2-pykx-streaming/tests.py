"""Tests for p2-pykx-streaming."""

import math
import random
from datetime import datetime, timedelta, timezone

import pytest

from challenge import stream_agg


def make_tick(sym, time, price, size):
    return {"sym": sym, "time": time, "price": float(price), "size": int(size)}


BASE_TIME = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)


def t(seconds):
    return BASE_TIME + timedelta(seconds=seconds)


# === Section 1: Basic Correctness ===

class TestBasicCorrectness:
    def test_single_sym_vwap(self):
        ticks = [
            make_tick("AAPL", t(0), 150.0, 100),
            make_tick("AAPL", t(1), 151.0, 200),
            make_tick("AAPL", t(2), 149.0, 150),
        ]
        windows = {"vwap_3": {"type": "vwap", "n": 3}}
        result = stream_agg(ticks, windows)
        expected_vwap = (150 * 100 + 151 * 200 + 149 * 150) / (100 + 200 + 150)
        assert abs(result["AAPL"]["vwap_3"] - expected_vwap) < 0.01

    def test_rolling_max(self):
        ticks = [
            make_tick("GOOG", t(0), 100.0, 50),
            make_tick("GOOG", t(1), 105.0, 60),
            make_tick("GOOG", t(2), 103.0, 70),
            make_tick("GOOG", t(3), 108.0, 80),
            make_tick("GOOG", t(4), 102.0, 90),
        ]
        windows = {"max_3": {"type": "max", "field": "price", "n": 3}}
        result = stream_agg(ticks, windows)
        # Last 3 prices: 103, 108, 102 -> max = 108
        assert result["GOOG"]["max_3"] == 108.0

    def test_rolling_sum(self):
        ticks = [
            make_tick("MSFT", t(0), 200.0, 10),
            make_tick("MSFT", t(1), 201.0, 20),
            make_tick("MSFT", t(2), 202.0, 30),
            make_tick("MSFT", t(3), 203.0, 40),
        ]
        windows = {"sum_size_2": {"type": "sum", "field": "size", "n": 2}}
        result = stream_agg(ticks, windows)
        # Last 2 sizes: 30, 40 -> sum = 70
        assert result["MSFT"]["sum_size_2"] == 70

    def test_multi_sym(self):
        ticks = [
            make_tick("AAPL", t(0), 150.0, 100),
            make_tick("GOOG", t(0), 200.0, 50),
            make_tick("AAPL", t(1), 151.0, 200),
            make_tick("GOOG", t(1), 201.0, 60),
        ]
        windows = {"vwap_2": {"type": "vwap", "n": 2}}
        result = stream_agg(ticks, windows)
        aapl_vwap = (150 * 100 + 151 * 200) / (100 + 200)
        goog_vwap = (200 * 50 + 201 * 60) / (50 + 60)
        assert abs(result["AAPL"]["vwap_2"] - aapl_vwap) < 0.01
        assert abs(result["GOOG"]["vwap_2"] - goog_vwap) < 0.01

    def test_multiple_windows(self):
        ticks = [
            make_tick("X", t(i), 100.0 + i, 10 + i) for i in range(10)
        ]
        windows = {
            "vwap_5": {"type": "vwap", "n": 5},
            "max_3": {"type": "max", "field": "price", "n": 3},
            "sum_4": {"type": "sum", "field": "size", "n": 4},
        }
        result = stream_agg(ticks, windows)
        assert "X" in result
        assert "vwap_5" in result["X"]
        assert "max_3" in result["X"]
        assert "sum_4" in result["X"]
        # max of last 3 prices: 107, 108, 109 -> 109
        assert result["X"]["max_3"] == 109.0
        # sum of last 4 sizes: 16, 17, 18, 19 -> 70
        assert result["X"]["sum_4"] == 70

    def test_partial_window(self):
        """Fewer ticks than window size — use all available."""
        ticks = [make_tick("Z", t(0), 50.0, 10)]
        windows = {"vwap_5": {"type": "vwap", "n": 5}}
        result = stream_agg(ticks, windows)
        assert abs(result["Z"]["vwap_5"] - 50.0) < 0.01


# === Section 2: Anti-Cheat ===

class TestAntiCheat:
    def test_uses_pykx(self):
        """Verify pykx is actually used."""
        import sys
        ticks = [make_tick("A", t(0), 100.0, 10)]
        stream_agg(ticks, {"v": {"type": "vwap", "n": 1}})
        assert "pykx" in sys.modules, "pykx must be imported and used"

    def test_not_constant(self):
        t1 = [make_tick("A", t(0), 100.0, 10)]
        t2 = [make_tick("A", t(0), 200.0, 20)]
        t3 = [make_tick("A", t(0), 300.0, 30)]
        w = {"v": {"type": "vwap", "n": 1}}
        r1 = stream_agg(t1, w)["A"]["v"]
        r2 = stream_agg(t2, w)["A"]["v"]
        r3 = stream_agg(t3, w)["A"]["v"]
        assert len({r1, r2, r3}) == 3, "Different inputs must produce different outputs"

    def test_result_structure(self):
        ticks = [make_tick("A", t(0), 100.0, 10)]
        result = stream_agg(ticks, {"v": {"type": "vwap", "n": 1}})
        assert isinstance(result, dict)
        assert isinstance(result["A"], dict)
        assert isinstance(result["A"]["v"], (int, float))


# === Section 3: Property Tests ===

class TestProperties:
    @pytest.mark.parametrize("seed", range(15))
    def test_vwap_correctness(self, seed):
        """VWAP computed through PyKX must match Python calculation."""
        rng = random.Random(seed)
        n_ticks = rng.randint(5, 30)
        window = rng.randint(2, min(n_ticks, 10))
        ticks = [
            make_tick("S", t(i), rng.uniform(50, 200), rng.randint(1, 500))
            for i in range(n_ticks)
        ]
        result = stream_agg(ticks, {"v": {"type": "vwap", "n": window}})

        # Compute expected: last `window` ticks
        last_ticks = ticks[-window:]
        expected = sum(t["price"] * t["size"] for t in last_ticks) / sum(
            t["size"] for t in last_ticks
        )
        assert abs(result["S"]["v"] - expected) < 0.01, (
            f"VWAP mismatch: expected {expected}, got {result['S']['v']}"
        )

    @pytest.mark.parametrize("seed", range(10))
    def test_max_correctness(self, seed):
        """Rolling max must match Python calculation."""
        rng = random.Random(seed)
        n_ticks = rng.randint(5, 20)
        window = rng.randint(2, min(n_ticks, 8))
        ticks = [
            make_tick("M", t(i), rng.uniform(10, 500), 10) for i in range(n_ticks)
        ]
        result = stream_agg(ticks, {"mx": {"type": "max", "field": "price", "n": window}})

        expected = max(t["price"] for t in ticks[-window:])
        assert abs(result["M"]["mx"] - expected) < 0.01


# === Section 4: Performance ===

class TestPerformance:
    def test_large_stream(self):
        """10K ticks across 5 syms with 3 windows — must complete in <10s."""
        import time as time_mod

        syms = ["AAPL", "GOOG", "MSFT", "AMZN", "META"]
        rng = random.Random(42)
        ticks = [
            make_tick(
                rng.choice(syms),
                t(i),
                rng.uniform(100, 300),
                rng.randint(10, 1000),
            )
            for i in range(10000)
        ]
        windows = {
            "vwap_50": {"type": "vwap", "n": 50},
            "max_100": {"type": "max", "field": "price", "n": 100},
            "sum_20": {"type": "sum", "field": "size", "n": 20},
        }

        start = time_mod.time()
        result = stream_agg(ticks, windows)
        elapsed = time_mod.time() - start

        assert elapsed < 10.0, f"Too slow: {elapsed:.1f}s"
        # Verify all syms present
        for sym in syms:
            assert sym in result, f"Missing sym: {sym}"
            assert "vwap_50" in result[sym]
