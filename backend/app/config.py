from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel


ROOT = Path(__file__).resolve().parents[2]


def load_local_env() -> None:
    """Small dotenv reader to keep the demo runnable without another dependency."""
    for path in (ROOT / ".env", ROOT / "backend" / ".env"):
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line or line.lstrip().startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_local_env()


class Settings(BaseModel):
    database_url: str = os.getenv("DATABASE_URL", f"sqlite:///{ROOT / 'data' / 'himalayan_sentinel.db'}")
    allowed_origins: list[str] = [
        item.strip() for item in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",") if item.strip()
    ]
    demo_mode: bool = os.getenv("DEMO_MODE", "true").lower() == "true"
    request_timeout_seconds: float = 10.0


settings = Settings()

