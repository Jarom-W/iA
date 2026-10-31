from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import csv
from datetime import datetime
import io
from pathlib import Path
import re
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

from werkzeug.security import generate_password_hash
from app import create_app, earnings

ORIGIN = 'https://time.example.test'
START = 1793440800


class WorkspaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.password_hash = generate_password_hash('test-owner-password')

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.database = str(Path(self.temp.name) / 'time.sqlite3')
        self.config = {'TESTING': True, 'SECRET_KEY': 'test-secret-value-' * 3,
            'ADMIN_USERNAME': 'jarom', 'ADMIN_PASSWORD_HASH': self.password_hash,
            'ORIGIN': ORIGIN, 'DATABASE_PATH': self.database, 'TIMEZONE': 'America/Denver', 'CURRENCY': 'USD'}
        self.app = create_app(self.config)
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp.cleanup()

    def get(self, path):
        return self.client.get(path, base_url=ORIGIN)

    def post(self, path, data=None, csrf=True):
        data = dict(data or {})
        if csrf:
            token = re.search('name="csrf" value="([^"]+)"', self.get('/login').text)[1]
            data['csrf'] = token
        response = self.client.post(path, data=data, base_url=ORIGIN)
        response.request.close()
        response.request.environ['wsgi.input'].close()
        return response

    def login(self):
        self.assertEqual(self.post('/login', {'username': 'jarom', 'password': 'test-owner-password'}).status_code, 302)

    def query(self, sql, params=()):
        with closing(sqlite3.connect(self.database)) as db, db:
            db.row_factory = sqlite3.Row
            return db.execute(sql, params).fetchall()

    def make_client(self, name='Example Studio', rate='150.00'):
        result = self.post('/clients/new', {'name': name, 'rate': rate, 'color': 'lilac', 'email': 'owner@example.test'})
        self.assertEqual(result.status_code, 302)
        return result.location.rsplit('/', 1)[1]

    def start(self, client_id, timestamp=START):
        with patch.dict(self.app.config, CLOCK=lambda: timestamp):
            result = self.post('/clock-in', {'client_id': client_id})
        self.assertEqual(result.status_code, 302)
        return self.query('SELECT id FROM entries ORDER BY started_at DESC')[0]['id']

    def stop(self, entry_id, timestamp=START + 3600):
        with patch.dict(self.app.config, CLOCK=lambda: timestamp):
            return self.post('/clock-out/' + entry_id)

    def save_journal(self, entry_id, **overrides):
        return self.post('/journal/' + entry_id, dict(summary='Build and refine', deliverables='Shipped the customer dashboard.', next_steps='Review together.', private_notes='Internal margin notes', revision='0', **overrides))

    def test_private_routes_and_documents_require_owner(self):
        for path in ['/', '/clients', '/calendar', '/api/timer', '/work-log', '/documents/unknown', '/clients/unknown/report']:
            self.assertEqual(self.get(path).status_code, 302)
        self.post('/login', {'username': 'other', 'password': 'test-owner-password'})
        self.assertEqual(self.get('/').status_code, 302)
        self.login()
        self.assertEqual(self.get('/').status_code, 200)
        self.post('/logout')
        self.assertEqual(self.get('/').status_code, 302)

    def test_csrf_origin_and_host_protection(self):
        self.assertEqual(self.post('/login', {'username': 'jarom', 'password': 'test-owner-password'}, csrf=False).status_code, 403)
        self.assertEqual(self.post('/login', {'csrf': '🚫'}, csrf=False).status_code, 403)
        self.login()
        with self.client.session_transaction(base_url=ORIGIN) as session:
            token = session['csrf']
        self.assertEqual(self.client.post('/clients/new', base_url=ORIGIN, data={'csrf': token}, headers={'Origin': 'https://evil.test'}).status_code, 403)
        self.assertEqual(self.client.post('/clients/new', base_url=ORIGIN, data={'csrf': token}, headers={'Origin': 'null', 'Sec-Fetch-Site': 'cross-site'}).status_code, 403)
        self.assertEqual(self.client.get('/clients', base_url='https://localhost').status_code, 404)
        response = self.get('/')
        self.assertEqual(response.headers['Cache-Control'], 'no-store')
        self.assertIn("frame-ancestors 'none'", response.headers['Content-Security-Policy'])

    def test_login_throttles_across_app_instances(self):
        for _ in range(10):
            self.assertEqual(self.post('/login', {'username': 'jarom', 'password': 'wrong'}).status_code, 200)
        self.app = create_app(self.config)
        self.client = self.app.test_client()
        self.assertEqual(self.post('/login', {'username': 'jarom', 'password': 'wrong'}).status_code, 429)

    def test_timer_persists_and_stops_before_journaling(self):
        self.login()
        client = self.make_client()
        entry = self.start(client)
        # A new process/browser reconnects to the same database.
        self.app = create_app(self.config)
        self.client = self.app.test_client()
        self.login()
        state = self.get('/api/timer').json['entry']
        self.assertEqual(state['started_at'], START)
        self.assertEqual(state['rate_cents'], 15000)
        self.stop(entry)
        self.stop(entry, START + 7200)  # Retried request must not add time.
        self.assertEqual(self.query('SELECT ended_at FROM entries')[0]['ended_at'], START + 3600)
        self.assertIn('Timer stopped', self.get('/journal/' + entry).text)
        self.assertNotIn('Build and refine', self.get(f'/clients/{client}/report').text)
        self.assertEqual(self.save_journal(entry).status_code, 302)
        report = self.get(f'/clients/{client}/report')
        self.assertEqual(report.status_code, 200)
        self.assertIn('USD 150.00', report.text)
        self.assertIn('Shipped the customer dashboard.', report.text)
        self.assertNotIn('Internal margin notes', report.text)

    def test_duplicate_and_pending_session_prevent_clock_in(self):
        self.login()
        client = self.make_client()
        entry = self.start(client)
        self.start(client, START + 10)
        self.assertEqual(len(self.query('SELECT * FROM entries')), 1)
        self.stop(entry)
        self.start(client, START + 7200)
        self.assertEqual(len(self.query('SELECT * FROM entries')), 1)
        self.save_journal(entry)
        self.start(client, START + 7200)
        self.assertEqual(len(self.query('SELECT * FROM entries')), 2)

    def test_concurrent_clock_in_is_serialized(self):
        self.login()
        client_id = self.make_client()
        def punch():
            client = self.app.test_client()
            with client.session_transaction(base_url=ORIGIN) as session:
                session.update(owner=True, csrf='parallel-csrf')
            return client.post('/clock-in', base_url=ORIGIN, data={'csrf': 'parallel-csrf', 'client_id': client_id}).status_code
        with ThreadPoolExecutor(max_workers=2) as workers:
            self.assertEqual(list(workers.map(lambda _: punch(), range(2))), [302, 302])
        self.assertEqual(len(self.query('SELECT * FROM entries')), 1)

    def test_rate_snapshot_and_archiving_preserve_history(self):
        self.login()
        client = self.make_client()
        entry = self.start(client)
        self.post(f'/clients/{client}/edit', {'name': 'Renamed Studio', 'rate': '250.50', 'color': 'blue'})
        self.assertEqual(self.get('/api/timer').json['entry']['rate_cents'], 15000)
        self.post(f'/clients/{client}/archive')
        self.assertEqual(self.query('SELECT archived FROM clients')[0]['archived'], 0)
        self.stop(entry)
        self.save_journal(entry)
        self.post(f'/clients/{client}/archive')
        self.assertEqual(self.query('SELECT archived FROM clients')[0]['archived'], 1)
        self.assertEqual(self.post('/clock-in', {'client_id': client}).status_code, 404)
        self.assertIn('Shipped the customer dashboard.', self.get(f'/clients/{client}/report').text)
        self.post(f'/clients/{client}/archive')
        self.start(client, START + 7200)
        self.assertEqual(self.get('/api/timer').json['entry']['rate_cents'], 25050)

    def test_journal_required_fields_and_stale_edit_protection(self):
        self.login()
        entry = self.start(self.make_client())
        self.stop(entry)
        response = self.post('/journal/' + entry, {'summary': 'Only title', 'revision': 0})
        self.assertIn('Please complete deliverables', response.text)
        self.assertEqual(self.query('SELECT status FROM entries')[0]['status'], 'draft')
        self.save_journal(entry)
        self.assertEqual(self.save_journal(entry).status_code, 409)
        self.assertEqual(self.query('SELECT summary FROM entries')[0]['summary'], 'Build and refine')

    def test_documents_are_private_bounded_and_download_only(self):
        self.login()
        client = self.make_client()
        result = self.post(f'/clients/{client}/documents', {'document': (io.BytesIO(b'%PDF-test-contract'), '../../agreement.pdf')})
        self.assertEqual(result.status_code, 302)
        document = self.query('SELECT id,name FROM documents')[0]
        self.assertEqual(document['name'], 'agreement.pdf')
        response = self.get('/documents/' + document['id'])
        self.assertEqual(response.data, b'%PDF-test-contract')
        self.assertIn('attachment', response.headers['Content-Disposition'])
        self.assertEqual(response.mimetype, 'application/octet-stream')
        self.assertEqual(self.post(f'/clients/{client}/documents', {'document': (io.BytesIO(b'<script>evil</script>'), 'evil.html')}).status_code, 400)
        self.assertEqual(self.post(f'/clients/{client}/documents', {'document': (io.BytesIO(b''), 'empty.pdf')}).status_code, 400)
        self.assertEqual(self.post(f'/clients/{client}/documents', {'document': (io.BytesIO(b'x' * (10 * 1024 * 1024 + 1)), 'large.pdf')}).status_code, 400)
        self.post('/logout')
        self.assertEqual(self.get('/documents/' + document['id']).status_code, 302)

    def test_invalid_rates_and_client_text_escaping(self):
        self.login()
        for value in ['NaN', 'Infinity', '-1', '1.123', '100001', 'abc']:
            self.assertEqual(self.post('/clients/new', {'name': 'Test', 'rate': value, 'color': 'green'}).status_code, 200)
        self.assertEqual(len(self.query('SELECT * FROM clients')), 0)
        client = self.make_client('<script>alert(1)</script>')
        self.assertIn('&lt;script&gt;', self.get('/clients/' + client).text)
        self.assertNotIn('<script>alert(1)</script>', self.get('/clients').text)

    def test_client_reports_filter_and_csv_formula_protection(self):
        self.login()
        client = self.make_client('=DANGEROUS()')
        other = self.make_client('Other client')
        entry = self.start(client)
        self.stop(entry)
        self.post('/journal/' + entry, {'summary': '=FORMULA()', 'deliverables': '@RISK', 'next_steps': '+RISK', 'private_notes': 'DO NOT EXPORT', 'revision': '0'})
        csv_response = self.get(f'/clients/{client}/report?format=csv')
        rows = list(csv.reader(io.StringIO(csv_response.data.decode('utf-8-sig'))))
        self.assertEqual(rows[1][0], "'=DANGEROUS()")
        self.assertEqual(rows[1][6], "'=FORMULA()")
        self.assertNotIn('DO NOT EXPORT', csv_response.text)
        self.assertNotIn('FORMULA', self.get(f'/clients/{other}/report').text)
        self.assertNotIn('FORMULA', self.get(f'/clients/{client}/report?from=2027-01-01').text)
        self.assertEqual(self.get(f'/clients/{client}/report?from=2027-02-01&to=2027-01-01').status_code, 400)

    def make_event(self, **overrides):
        data = dict(title='Planning call', kind='call', starts_at='2026-11-03T09:00', ends_at='2026-11-03T10:00', notes='Discuss next steps')
        data.update(overrides)
        return self.post('/events/new', data)

    def test_calendar_create_edit_delete_and_multiday_off(self):
        self.login()
        self.assertEqual(self.make_event().status_code, 302)
        self.assertEqual(self.make_event(title='Time away', kind='off', starts_at='2026-11-10T00:00', ends_at='2026-11-13T00:00').status_code, 302)
        calendar = self.get('/calendar?month=2026-11')
        self.assertEqual(calendar.status_code, 200)
        self.assertEqual(calendar.text.count('<strong>Time away</strong>'), 4)  # 3 days + agenda; exclusive end.
        event = self.query("SELECT * FROM events WHERE title='Planning call'")[0]
        result = self.post('/events/' + event['id'], {'title': 'Updated call', 'kind': 'focus', 'starts_at': '2026-11-03T11:00', 'ends_at': '2026-11-03T12:00', 'revision': '0'})
        self.assertEqual(result.status_code, 302)
        self.assertEqual(self.post('/events/' + event['id'] + '/delete', {'revision': '0'}).status_code, 409)
        self.assertEqual(self.post('/events/' + event['id'] + '/delete', {'revision': '1'}).status_code, 302)
        self.assertEqual(len(self.query('SELECT * FROM events')), 1)

    def test_calendar_rejects_reversed_and_dst_invalid_times(self):
        self.login()
        cases = [('2026-11-03T10:00','2026-11-03T09:00'), ('2027-03-14T02:30','2027-03-14T04:00'), ('2026-11-01T01:30','2026-11-01T03:00')]
        for start, end in cases:
            self.assertEqual(self.make_event(starts_at=start, ends_at=end).status_code, 200)
        self.assertEqual(len(self.query('SELECT * FROM events')), 0)
        self.assertEqual(self.get('/calendar?month=nonsense').status_code, 400)

    def test_earnings_round_half_up_and_elapsed_dst(self):
        self.assertEqual(earnings(3600, 15000), 15000)
        self.assertEqual(earnings(1, 1800), 1)
        self.assertEqual(earnings(-10, 1800), 0)
        self.login()
        tz = ZoneInfo('America/Denver')
        start = int(datetime(2026, 11, 1, 0, 30, tzinfo=tz).timestamp())
        end = int(datetime(2026, 11, 1, 2, 30, tzinfo=tz).timestamp())
        entry = self.start(self.make_client(rate='100'), start)
        self.stop(entry, end)
        self.save_journal(entry)
        self.assertIn('USD 300.00', self.get('/journal/' + entry).text)


if __name__ == '__main__':
    unittest.main()
