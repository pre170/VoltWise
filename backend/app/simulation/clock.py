from datetime import datetime, timedelta


class SimulationClock:
    def __init__(self, initial_time: datetime) -> None:
        self._initial_time = initial_time
        self._current_time = initial_time

    @property
    def now(self) -> datetime:
        return self._current_time

    def advance_hours(self, hours: float) -> datetime:
        if hours < 0:
            raise ValueError("Simulation clock cannot move backwards")
        self._current_time += timedelta(hours=hours)
        return self._current_time

    def advance_days(self, days: float) -> datetime:
        if days < 0:
            raise ValueError("Simulation clock cannot move backwards")
        self._current_time += timedelta(days=days)
        return self._current_time

    def reset(self) -> datetime:
        self._current_time = self._initial_time
        return self._current_time

