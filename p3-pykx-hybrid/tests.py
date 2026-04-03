"""Tests for p3-pykx-hybrid."""

import math
import random
from datetime import datetime, timedelta, timezone

import pytest

from challenge import hybrid_pipeline


BASE_TIME = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)


def make_trade(sym, seconds, price, size):
    return {
        "sym": sym,
        "time": BASE_TIME + timedelta(seconds=seconds),
        "price": float(price),
        "size": int(size),
    }


def simple_model(features: dict) -> float:
    """A simple test model: signal = spread * volatility."""
    return features["spread"] * features.get("volatility", 1.0)


def linear_model(features: dict) -> float:
    """Linear combination model."""
    return 0.5 * features["vwap"] + 0.3 * features["price"] - 0.2 * features["spread"]


def python_vwap(trades):
    """Reference Python VWAP for validation."""
    total_value = sum(t["price"] * t["size"] for t in trades)
    total_size = sum(t["size"] for t in trades)
    return total_value / total_size if total_size > 0 else 0.0


def python_sdev(prices):
    """Reference Python standard deviation."""
    if len(prices) < 2:
        return 0.0
    mean = sum(prices) / len(prices)
    variance = sum((p - mean) ** 2 for p in prices) / (len(prices) - 1)
    return math.sqrt(variance)


# Track model_fn calls for anti-cheat
call_tracker = {"count": 0, "last_features": None}


def tracked_model(features: dict) -> float:
    call_tracker["count"] += 1
    call_tracker["last_features"] = features.copy()
    return simple_model(features)


# === Section 1: Basic Correctness ===

class TestBasicCorrectness:
    def test_simple_pipeline(self):
        trades = [make_trade("AAPL", i, 150 + i * 0.5, 100) for i in range(10)]
        lookback = 3
        result = hybrid_pipeline(trades, simple_model, lookback)

        assert len(result) == len(trades) - lookback
        for r in result:
            assert "sym" in r
            assert "time" in r
            assert "price" in r
            assert "signal" in r
            assert "vwap" in r
            assert "volatility" in r
            assert "spread" in r

    def test_vwap_correctness(self):
        trades = [make_trade("X", i, 100 + i, 10 * (i + 1)) for i in range(6)]
        lookback = 3
        result = hybrid_pipeline(trades, simple_model, lookback)

        # Check VWAP at index 3 (lookback window: trades[0:3])
        window = trades[0:3]
        expected_vwap = python_vwap(window)
        assert abs(result[0]["vwap"] - expected_vwap) < 0.01

    def test_volatility_correctness(self):
        trades = [make_trade("X", i, 100 + i * 2, 10) for i in range(6)]
        lookback = 3
        result = hybrid_pipeline(trades, simple_model, lookback)

        # Volatility at index 3: sdev of prices[0:3] = sdev(100, 102, 104)
        prices = [t["price"] for t in trades[0:3]]
        expected_vol = python_sdev(prices)
        assert abs(result[0]["volatility"] - expected_vol) < 0.01

    def test_spread(self):
        trades = [make_trade("X", i, 100 + i, 100) for i in range(5)]
        lookback = 2
        result = hybrid_pipeline(trades, simple_model, lookback)
        for r in result:
            assert abs(r["spread"] - (r["price"] - r["vwap"])) < 0.01

    def test_model_fn_called(self):
        """model_fn must actually be called with correct features."""
        call_tracker["count"] = 0
        trades = [make_trade("A", i, 50 + i, 10) for i in range(8)]
        lookback = 3
        result = hybrid_pipeline(trades, tracked_model, lookback)
        assert call_tracker["count"] == len(trades) - lookback
        assert call_tracker["last_features"] is not None
        assert "vwap" in call_tracker["last_features"]
        assert "volatility" in call_tracker["last_features"]

    def test_output_length(self):
        trades = [make_trade("A", i, 100, 10) for i in range(20)]
        for lookback in [1, 5, 10, 15]:
            result = hybrid_pipeline(trades, simple_model, lookback)
            assert len(result) == len(trades) - lookback

    def test_different_model(self):
        """Using a different model_fn gives different signals."""
        trades = [make_trade("A", i, 100 + i, 50) for i in range(10)]
        r1 = hybrid_pipeline(trades, simple_model, 3)
        r2 = hybrid_pipeline(trades, linear_model, 3)
        signals1 = [r["signal"] for r in r1]
        signals2 = [r["signal"] for r in r2]
        assert signals1 != signals2


# === Section 2: Anti-Cheat ===

class TestAntiCheat:
    def test_uses_pykx(self):
        import sys
        trades = [make_trade("A", i, 100, 10) for i in range(5)]
        hybrid_pipeline(trades, simple_model, 2)
        assert "pykx" in sys.modules, "pykx must be used for q computations"

    def test_model_receives_q_computed_vwap(self):
        """Verify the features passed to model_fn contain q-computed values."""
        received_features = []

        def capture_model(features):
            received_features.append(features.copy())
            return 0.0

        # Use prices that make VWAP distinguishable from simple mean
        trades = [
            make_trade("A", 0, 100.0, 10),   # low volume
            make_trade("A", 1, 200.0, 990),  # high volume
            make_trade("A", 2, 150.0, 100),  # current trade
        ]
        hybrid_pipeline(trades, capture_model, 2)

        # VWAP should be ~199 (heavily weighted toward 200 due to volume)
        # Simple mean would be 150. If we get ~199, q computed correctly.
        assert len(received_features) == 1
        vwap = received_features[0]["vwap"]
        assert vwap > 190, f"VWAP {vwap} looks like simple mean, not volume-weighted"

    def test_not_constant(self):
        t1 = [make_trade("A", i, 100 + i, 10) for i in range(5)]
        t2 = [make_trade("A", i, 200 + i * 3, 50) for i in range(5)]
        r1 = hybrid_pipeline(t1, simple_model, 2)
        r2 = hybrid_pipeline(t2, simple_model, 2)
        assert [r["signal"] for r in r1] != [r["signal"] for r in r2]


# === Section 3: Property Tests ===

class TestProperties:
    @pytest.mark.parametrize("seed", range(15))
    def test_vwap_matches_python(self, seed):
        """VWAP from pipeline must match Python reference for every output."""
        rng = random.Random(seed)
        n = rng.randint(8, 25)
        lookback = rng.randint(2, min(5, n - 2))
        trades = [
            make_trade("S", i, rng.uniform(50, 200), rng.randint(1, 500))
            for i in range(n)
        ]
        result = hybrid_pipeline(trades, simple_model, lookback)

        for idx, r in enumerate(result):
            trade_idx = idx + lookback
            window = trades[trade_idx - lookback : trade_idx]
            expected_vwap = python_vwap(window)
            assert abs(r["vwap"] - expected_vwap) < 0.1, (
                f"VWAP mismatch at index {trade_idx}: expected {expected_vwap}, got {r['vwap']}"
            )

    @pytest.mark.parametrize("seed", range(10))
    def test_volatility_matches_python(self, seed):
        """Volatility must match Python sdev reference."""
        rng = random.Random(seed)
        n = rng.randint(8, 20)
        lookback = rng.randint(3, min(6, n - 2))
        trades = [
            make_trade("S", i, rng.uniform(50, 200), rng.randint(1, 500))
            for i in range(n)
        ]
        result = hybrid_pipeline(trades, simple_model, lookback)

        for idx, r in enumerate(result):
            trade_idx = idx + lookback
            prices = [t["price"] for t in trades[trade_idx - lookback : trade_idx]]
            expected_vol = python_sdev(prices)
            assert abs(r["volatility"] - expected_vol) < 0.5, (
                f"Volatility mismatch at index {trade_idx}"
            )


# === Section 4: Performance ===

class TestPerformance:
    def test_large_pipeline(self):
        """5K trades, lookback 50 — must complete in <10s."""
        import time as time_mod

        rng = random.Random(42)
        trades = [
            make_trade("AAPL", i, rng.uniform(100, 200), rng.randint(10, 1000))
            for i in range(5000)
        ]

        start = time_mod.time()
        result = hybrid_pipeline(trades, simple_model, 50)
        elapsed = time_mod.time() - start

        assert elapsed < 10.0, f"Too slow: {elapsed:.1f}s"
        assert len(result) == 4950
