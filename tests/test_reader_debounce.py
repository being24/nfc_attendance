from reader.debounce import Debouncer


def test_debounce_allows_after_cooldown():
    d = Debouncer(cooldown_seconds=2.0)
    assert d.allow("A", now=100.0) is True
    assert d.allow("A", now=101.0) is False
    assert d.allow("A", now=102.1) is True
