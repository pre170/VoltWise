from datetime import datetime, timedelta

import pytest

from app.simulation import SimulationClock


def test_simulation_clock_advance_and_reset() -> None:
    initial = datetime(2026, 9, 15)
    clock = SimulationClock(initial)

    assert clock.advance_hours(6) == initial + timedelta(hours=6)
    assert clock.advance_days(2) == initial + timedelta(days=2, hours=6)
    assert clock.reset() == initial


def test_simulation_clock_rejects_backwards_advance() -> None:
    clock = SimulationClock(datetime(2026, 9, 15))

    with pytest.raises(ValueError, match="backwards"):
        clock.advance_days(-1)

