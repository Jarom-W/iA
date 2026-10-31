from contextlib import closing
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from backup import main


class BackupTests(unittest.TestCase):
    def test_backup_contains_documents_and_committed_wal_data(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'time.sqlite3'
            with closing(sqlite3.connect(path)) as db:
                db.execute('PRAGMA journal_mode=WAL')
                db.execute('CREATE TABLE document(content BLOB)')
                db.execute('INSERT INTO document VALUES (?)', (b'private agreement',))
                db.commit()
                with patch.dict(os.environ, TIME_DATABASE_PATH=str(path)):
                    main()
                snapshots = list((path.parent / 'backups').glob('time-*.sqlite3'))
                self.assertEqual(len(snapshots), 1)
                with closing(sqlite3.connect(snapshots[0])) as backup:
                    self.assertEqual(backup.execute('SELECT content FROM document').fetchone()[0], b'private agreement')
                    self.assertEqual(backup.execute('PRAGMA integrity_check').fetchone()[0], 'ok')


if __name__ == '__main__':
    unittest.main()
