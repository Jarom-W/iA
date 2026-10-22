"""Consistent local SQLite snapshots. Copy these to encrypted off-server storage too."""
from contextlib import closing
from datetime import datetime, timezone
import os
from pathlib import Path
import sqlite3


def main():
    source = Path(os.environ["DATABASE_PATH"])
    if not source.is_file():
        raise SystemExit("Database does not exist; no backup created.")
    os.umask(0o077)
    directory = source.parent / "backups"
    directory.mkdir(mode=0o700, exist_ok=True)
    destination = directory / datetime.now(timezone.utc).strftime("feedback-%Y%m%dT%H%M%S%f.sqlite3")
    with closing(sqlite3.connect(f"{source.as_uri()}?mode=ro", uri=True)) as db:
        with closing(sqlite3.connect(destination)) as backup:
            db.backup(backup)
            if backup.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise RuntimeError("Backup integrity check failed")
    for old in sorted(directory.glob("feedback-*.sqlite3"), reverse=True)[14:]:
        old.unlink()
    print("Database backup verified; retaining the latest 14 snapshots.")


if __name__ == "__main__":
    main()
