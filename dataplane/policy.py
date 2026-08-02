import hashlib
import re

from .models import PolicyDecision

WRITE = {"insert", "update", "delete", "merge", "replace", "create", "drop", "alter", "truncate"}


def tables(sql: str) -> tuple[str, ...]:
    pattern = r'\b(?:from|join)\s+([a-zA-Z0-9_."`]+)'
    found = re.findall(pattern, sql, re.IGNORECASE)
    cleaned = [value.strip('"`').split('.')[-1] for value in found]
    return tuple(dict.fromkeys(cleaned))


def evaluate_query_policy(profile, sql, requested_limit, request_writeback=False):
    normalised = " ".join(sql.strip().lower().split())
    decision_id = hashlib.sha256(
        f"{profile.name}|{normalised}|{requested_limit}|{request_writeback}".encode()
    ).hexdigest()[:16]

    def deny(reason):
        return PolicyDecision(
            False,
            reason,
            False,
            profile.max_rows,
            profile.allowed_tables,
            decision_id,
        )

    if not normalised:
        return deny("Query is empty")
    if ";" in normalised.rstrip(";"):
        return deny("Multiple SQL statements are not allowed")

    first = normalised.split(" ", 1)[0]
    if first in WRITE and profile.read_only:
        return deny("Connection profile is read-only")
    if first not in {"select", "with"}:
        return deny("Only SELECT/CTE queries are allowed through the query node")

    blocked = sorted(set(tables(normalised)) - set(profile.allowed_tables)) if profile.allowed_tables else []
    if blocked:
        return deny("Tables not allowed by profile: " + ", ".join(blocked))

    return PolicyDecision(
        True,
        "Allowed by profile policy",
        not profile.read_only,
        max(1, min(int(requested_limit), profile.max_rows)),
        profile.allowed_tables,
        decision_id,
    )
