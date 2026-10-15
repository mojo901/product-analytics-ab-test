"""
Загрузка CSV из data/raw в базу SQLite data/shopflow.db.

На этапе загрузки делаем базовую очистку:
  * удаляем полные дубли событий (одинаковые user_id, event_time, event_type);
  * пропуски в платформе заменяем на 'unknown'.

Запуск:  python src/build_db.py
"""
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
DB_PATH = ROOT / "data" / "shopflow.db"


def build(db_path: Path = DB_PATH) -> Path:
    users = pd.read_csv(RAW / "users.csv")
    events = pd.read_csv(RAW / "events.csv")
    ab = pd.read_csv(RAW / "ab_groups.csv")

    users["platform"] = users["platform"].fillna("unknown")
    events = events.drop_duplicates(subset=["user_id", "event_time", "event_type"])

    db_path.unlink(missing_ok=True)
    with sqlite3.connect(db_path) as con:
        users.to_sql("users", con, index=False)
        events.to_sql("events", con, index=False)
        ab.to_sql("ab_groups", con, index=False)
        con.executescript("""
            CREATE INDEX idx_events_user ON events(user_id);
            CREATE INDEX idx_events_type_time ON events(event_type, event_time);
            CREATE UNIQUE INDEX idx_users_id ON users(user_id);
            CREATE UNIQUE INDEX idx_ab_user ON ab_groups(user_id);
        """)
    print(f"База создана: {db_path}  (events: {len(events):,})")
    return db_path


if __name__ == "__main__":
    build()
