from __future__ import annotations

import pytest

from crane.utils.retry import retry, safe_execute


def test_retry_retries_until_success(monkeypatch: pytest.MonkeyPatch):
    calls = {"count": 0}
    delays = []

    monkeypatch.setattr("crane.utils.retry.time.sleep", delays.append)

    @retry(max_attempts=3, delay=0.5, backoff=3.0, exceptions=(ValueError,))
    def flaky():
        calls["count"] += 1
        if calls["count"] < 3:
            raise ValueError("temporary")
        return "ok"

    assert flaky() == "ok"
    assert calls["count"] == 3
    assert delays == [0.5, 1.5]


def test_retry_raises_last_exception(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("crane.utils.retry.time.sleep", lambda *_: None)

    @retry(max_attempts=2, delay=0.1, exceptions=(ValueError,))
    def always_fail():
        raise ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        always_fail()


def test_safe_execute_returns_value_or_default():
    assert safe_execute(lambda: 7, default=0) == 7
    assert safe_execute(lambda: (_ for _ in ()).throw(ValueError("x")), default=3) == 3


def test_safe_execute_reraises_unhandled_exception():
    with pytest.raises(KeyError):
        safe_execute(
            lambda: (_ for _ in ()).throw(KeyError("missing")),
            default="fallback",
            exceptions=(ValueError,),
        )
