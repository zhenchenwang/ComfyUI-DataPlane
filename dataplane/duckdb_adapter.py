import hashlib
import time

import duckdb

from .models import QueryResult, WritebackResult


class DuckDBAdapter:
    def __init__(self, profile):
        self.profile = profile

    def connect(self):
        return duckdb.connect(self.profile.database, read_only=self.profile.read_only)

    def test_connection(self):
        with self.connect() as conn:
            conn.execute("SELECT 1").fetchone()
        return True, "DuckDB connection successful"

    def execute_query(self, sql, parameters, policy):
        if not policy.allowed:
            raise PermissionError(policy.reason)
        values = list(parameters.values.values())
        positional = sql
        for key in parameters.values:
            positional = positional.replace(f":{key}", "?", 1)
        wrapped = f"SELECT * FROM ({positional.rstrip().rstrip(';')}) AS dataplane_query LIMIT ?"
        values.append(policy.max_rows + 1)
        started = time.perf_counter()
        with self.connect() as conn:
            cursor = conn.execute(wrapped, values)
            raw = cursor.fetchall()
            columns = tuple(item[0] for item in cursor.description or ())
        truncated = len(raw) > policy.max_rows
        raw = raw[: policy.max_rows]
        rows = tuple(dict(zip(columns, item, strict=True)) for item in raw)
        query_hash = hashlib.sha256(
            f"{self.profile.name}|{sql}|{sorted(parameters.values.items())}".encode()
        ).hexdigest()
        return QueryResult(
            columns,
            rows,
            len(rows),
            self.profile.name,
            query_hash,
            truncated,
            round((time.perf_counter() - started) * 1000, 3),
        )

    def insert_row(self, table, row, policy, confirmation):
        if not policy.allowed or not policy.allow_writeback:
            raise PermissionError("Writeback is not allowed by policy")
        if confirmation != "CONFIRM_WRITE":
            raise PermissionError("Writeback confirmation token is missing")
        columns = list(row)
        quoted = ", ".join('"' + column + '"' for column in columns)
        placeholders = ", ".join("?" for _ in columns)
        sql = f'INSERT INTO "{table}" ({quoted}) VALUES ({placeholders})'
        with self.connect() as conn:
            conn.execute(sql, [row[column] for column in columns])
        return WritebackResult(True, 1, table, "insert", "Row inserted")
