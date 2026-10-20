import json
import sqlite3
from collections.abc import Sequence
from contextlib import closing
from pathlib import Path
from typing import Protocol

from app.models import ApplicationEvent, ApplicationEventType


class EventRepository(Protocol):
    def append(self, event: ApplicationEvent) -> ApplicationEvent: ...

    def recent(self, limit: int = 50) -> Sequence[ApplicationEvent]: ...

    def get_state(self, key: str) -> str | None: ...

    def set_state(self, key: str, value: str) -> None: ...


class SQLiteEventRepository:
    def __init__(self, database_path: Path | str) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def append(self, event: ApplicationEvent) -> ApplicationEvent:
        with closing(self._connect()) as connection:
            with connection:
                cursor = connection.execute(
                    """
                    INSERT INTO application_events
                        (timestamp, event_type, device_id, action, outcome, details_json)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event.timestamp.isoformat(),
                        event.event_type.value,
                        event.device_id,
                        event.action,
                        event.outcome,
                        json.dumps(event.details, sort_keys=True),
                    ),
                )
                event_id = int(cursor.lastrowid)
        return event.model_copy(update={"event_id": event_id})

    def recent(self, limit: int = 50) -> Sequence[ApplicationEvent]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT id, timestamp, event_type, device_id, action, outcome, details_json
                FROM application_events
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return tuple(
            ApplicationEvent(
                event_id=row[0],
                timestamp=row[1],
                event_type=ApplicationEventType(row[2]),
                device_id=row[3],
                action=row[4],
                outcome=row[5],
                details=json.loads(row[6]),
            )
            for row in rows
        )

    def get_state(self, key: str) -> str | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT value FROM application_state WHERE key = ?", (key,)
            ).fetchone()
        return None if row is None else str(row[0])

    def set_state(self, key: str, value: str) -> None:
        with closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO application_state (key, value) VALUES (?, ?)
                    ON CONFLICT(key) DO UPDATE SET value = excluded.value
                    """,
                    (key, value),
                )

    def _initialize(self) -> None:
        with closing(self._connect()) as connection:
            with connection:
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS application_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        device_id TEXT,
                        action TEXT NOT NULL,
                        outcome TEXT NOT NULL,
                        details_json TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS application_state (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL
                    );
                    """
                )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database_path, timeout=5)
