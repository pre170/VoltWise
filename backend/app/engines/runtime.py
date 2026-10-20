from datetime import datetime

from app.models import DeviceStateTransition, ReportedState


class RuntimeEngine:
    @staticmethod
    def calculate_hours(
        history: tuple[DeviceStateTransition, ...] | list[DeviceStateTransition],
        start: datetime,
        end: datetime,
    ) -> float:
        if end <= start:
            raise ValueError("Runtime period end must be after start")
        if not history:
            return 0.0

        ordered = sorted(history, key=lambda item: item.timestamp)
        for previous, current in zip(ordered, ordered[1:]):
            if previous.timestamp == current.timestamp and previous.state != current.state:
                raise ValueError("Conflicting device states at the same timestamp")

        state = ReportedState.OFF
        cursor = start
        total_seconds = 0.0

        for transition in ordered:
            if transition.timestamp <= start:
                state = transition.state
                continue
            if transition.timestamp >= end:
                break
            if transition.state is state:
                raise ValueError("Malformed history contains a repeated state transition")
            if state is ReportedState.ON:
                total_seconds += (transition.timestamp - cursor).total_seconds()
            cursor = transition.timestamp
            state = transition.state

        if state is ReportedState.ON:
            total_seconds += (end - cursor).total_seconds()
        return round(total_seconds / 3600.0, 3)

