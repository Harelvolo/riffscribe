"""A daily usage cap per signed-in user (or per IP when anonymous) on the
compute-heavy endpoints, so the free tier stays affordable regardless of how
much traffic shows up.
"""

from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException, Request

from app import db

DAILY_LIMIT = 5

# Accounts exempt from the daily cap entirely (the product owner, for testing
# and demoing without tripping over their own rate limit).
UNLIMITED_EMAILS = {"harelvolo1@gmail.com"}


def is_unlimited(current_user: dict | None) -> bool:
    return bool(current_user) and current_user.get("email") in UNLIMITED_EMAILS


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def usage_key(request: Request, current_user: dict | None) -> str:
    if current_user:
        return f"user:{current_user['sub']}"
    return f"ip:{client_ip(request)}"


def check_and_increment(storage_dir: Path, key: str, limit: int = DAILY_LIMIT) -> None:
    """Raises HTTPException(429) if `key` has hit today's limit, else records one use."""
    conn = db.connect(storage_dir)
    try:
        today = _today()
        row = conn.execute(
            "SELECT count FROM usage_counters WHERE usage_key = ? AND day = ?", (key, today)
        ).fetchone()
        if row and row["count"] >= limit:
            raise HTTPException(
                status_code=429,
                detail=f"You've reached today's free limit of {limit}. Come back tomorrow for more!",
            )
        conn.execute(
            """
            INSERT INTO usage_counters (usage_key, day, count) VALUES (?, ?, 1)
            ON CONFLICT(usage_key, day) DO UPDATE SET count = count + 1
            """,
            (key, today),
        )
        conn.commit()
    finally:
        conn.close()
