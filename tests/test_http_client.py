"""Tests para http_client.py.

Verifican que el RateLimiter es por sesión y que no hay estado global
mutable: dos sesiones distintas deben tener limiters distintos y los rates
no deben pisarse.
"""
import asyncio
import time

import http_client as H


def test_rate_limiter_init():
    rl = H.RateLimiter(rate_limit=0.5)
    assert rl._rate_limit == 0.5
    assert rl._last_request_time == 0.0


def test_rate_limiter_enforces_delay():
    async def run():
        rl = H.RateLimiter(rate_limit=0.05)
        start = time.perf_counter()
        await rl.wait_if_needed()
        await rl.wait_if_needed()
        return time.perf_counter() - start

    elapsed = asyncio.run(run())
    assert elapsed >= 0.05


class FakeSession:
    """Mínimo stand-in para ClientSession en tests sin red."""
    pass


def test_session_rate_limiter_creates_lazy():
    session = FakeSession()
    config = {"rate_limit": 0.7}
    limiter = H._session_rate_limiter(session, config)
    assert isinstance(limiter, H.RateLimiter)
    assert limiter._rate_limit == 0.7
    # Segunda llamada devuelve la misma instancia adjunta a la sesión.
    assert H._session_rate_limiter(session, config) is limiter


def test_session_rate_limiter_independent_per_session():
    session_a = FakeSession()
    session_b = FakeSession()
    limiter_a = H._session_rate_limiter(session_a, {"rate_limit": 0.1})
    limiter_b = H._session_rate_limiter(session_b, {"rate_limit": 2.0})
    assert limiter_a is not limiter_b
    assert limiter_a._rate_limit == 0.1
    assert limiter_b._rate_limit == 2.0


def test_session_rate_limiter_uses_default_when_missing():
    import constants as const
    session = FakeSession()
    limiter = H._session_rate_limiter(session, {})
    assert limiter._rate_limit == const.DEFAULT_RATE_LIMIT
