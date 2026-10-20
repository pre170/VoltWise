import json
import sqlite3
from collections.abc import Sequence
from contextlib import closing
from pathlib import Path
from typing import Protocol

from app.models import MCPTrace, MCPTraceTransport, SimulatorIntent


class MCPTraceRepository(Protocol):
    def append(self, trace: MCPTrace) -> MCPTrace: ...

    def recent(self, limit: int = 50) -> Sequence[MCPTrace]: ...


class SQLiteMCPTraceRepository:
    def __init__(self, database_path: Path | str) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def append(self, trace: MCPTrace) -> MCPTrace:
        with closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO mcp_traces (
                        trace_id, timestamp, transport, protocol_version, intent,
                        tool_name, tool_arguments_json, result_summary,
                        duration_ms, success, error
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        trace.trace_id,
                        trace.timestamp.isoformat(),
                        trace.transport.value,
                        trace.protocol_version,
                        trace.intent.value,
                        trace.tool_name,
                        json.dumps(trace.tool_arguments, sort_keys=True),
                        trace.result_summary,
                        trace.duration_ms,
                        int(trace.success),
                        trace.error,
                    ),
                )
        return trace

    def recent(self, limit: int = 50) -> Sequence[MCPTrace]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT trace_id, timestamp, transport, protocol_version, intent,
                       tool_name, tool_arguments_json, result_summary,
                       duration_ms, success, error
                FROM mcp_traces
                ORDER BY timestamp DESC, rowid DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return tuple(
            MCPTrace(
                trace_id=row[0],
                timestamp=row[1],
                transport=MCPTraceTransport(row[2]),
                protocol_version=row[3],
                intent=SimulatorIntent(row[4]),
                tool_name=row[5],
                tool_arguments=json.loads(row[6]),
                result_summary=row[7],
                duration_ms=row[8],
                success=bool(row[9]),
                error=row[10],
            )
            for row in rows
        )

    def _initialize(self) -> None:
        with closing(self._connect()) as connection:
            with connection:
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS mcp_traces (
                        trace_id TEXT PRIMARY KEY,
                        timestamp TEXT NOT NULL,
                        transport TEXT NOT NULL,
                        protocol_version TEXT,
                        intent TEXT NOT NULL,
                        tool_name TEXT NOT NULL,
                        tool_arguments_json TEXT NOT NULL,
                        result_summary TEXT NOT NULL,
                        duration_ms REAL NOT NULL CHECK (duration_ms >= 0),
                        success INTEGER NOT NULL CHECK (success IN (0, 1)),
                        error TEXT
                    );
                    CREATE INDEX IF NOT EXISTS idx_mcp_traces_timestamp
                        ON mcp_traces(timestamp DESC);
                    """
                )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database_path, timeout=5)
