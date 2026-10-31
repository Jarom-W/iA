"""Private time tracking and client workspace. All business data requires owner login."""
import calendar
from contextlib import closing
import csv
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import hmac
import io
import os
from pathlib import Path
import re
import secrets
import sqlite3
import time
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from flask import Flask, abort, flash, g, jsonify, redirect, render_template, request, send_file, session, url_for
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename

COLORS = ('green', 'teal', 'lilac', 'pink', 'blue')
KINDS = {'call': 'Call', 'focus': 'Focus time', 'off': 'Time off', 'deadline': 'Deadline'}


def earnings(seconds, rate):
    return int((Decimal(max(0, seconds)) * rate / 3600).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.getenv('TIME_SECRET_KEY'), ADMIN_USERNAME=os.getenv('ADMIN_USERNAME', 'jarom'),
        ADMIN_PASSWORD_HASH=os.getenv('ADMIN_PASSWORD_HASH', ''),
        ORIGIN=os.getenv('TIME_ORIGIN', 'https://time.inflectionarchitectures.com'),
        DATABASE_PATH=os.getenv('TIME_DATABASE_PATH', '/data/timekeeper.sqlite3'),
        TIMEZONE=os.getenv('TIME_TIMEZONE', 'America/Denver'), CURRENCY=os.getenv('TIME_CURRENCY', 'USD'),
        SESSION_COOKIE_NAME='__Host-ia-time', SESSION_COOKIE_SECURE=True, SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax', PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
        MAX_CONTENT_LENGTH=11 * 1024 * 1024, MAX_FORM_MEMORY_SIZE=128 * 1024,
    )
    if config:
        app.config.update(config)
    if len(app.config['SECRET_KEY'] or '') < 32 or not app.config['ADMIN_PASSWORD_HASH']:
        raise RuntimeError('Set TIME_SECRET_KEY (32+ random characters) and ADMIN_PASSWORD_HASH.')
    origin = urlsplit(app.config['ORIGIN'])
    if not origin.hostname or origin.path or origin.query or origin.fragment or origin.username or origin.scheme not in ('http', 'https'):
        raise RuntimeError('TIME_ORIGIN must be an origin without a path.')
    if origin.scheme != 'https' and not app.testing:
        raise RuntimeError('TIME_ORIGIN must use HTTPS.')
    if not re.fullmatch('[A-Z]{3}', app.config['CURRENCY']):
        raise RuntimeError('TIME_CURRENCY must be a three-letter currency code.')
    tz = ZoneInfo(app.config['TIMEZONE'])
    app.config['TRUSTED_HOSTS'] = [origin.hostname, 'localhost', '127.0.0.1']
    database = Path(app.config['DATABASE_PATH'])
    database.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(database)) as conn:
        conn.executescript(Path(__file__).with_name('schema.sql').read_text())
    database.chmod(0o600)

    def db():
        if 'db' not in g:
            g.db = sqlite3.connect(database, timeout=15)
            g.db.row_factory = sqlite3.Row
            g.db.execute('PRAGMA foreign_keys=ON')
        return g.db

    @app.teardown_appcontext
    def close_db(_error):
        if connection := g.pop('db', None):
            connection.close()

    def now():
        return int(app.config.get('CLOCK', time.time)())

    def csrf():
        if 'csrf' not in session:
            session['csrf'] = secrets.token_urlsafe(32)
        return session['csrf']

    def local(value):
        return datetime.fromtimestamp(value, tz)

    def money(cents):
        return f'{app.config["CURRENCY"]} {cents / 100:,.2f}'

    def duration(seconds):
        seconds = max(0, int(seconds))
        return f'{seconds // 3600:02d}:{seconds // 60 % 60:02d}:{seconds % 60:02d}'

    app.jinja_env.filters.update(money=money, duration=duration, local=local)
    app.jinja_env.globals.update(csrf_token=csrf, colors=COLORS, kinds=KINDS)

    @app.context_processor
    def context():
        return dict(timezone_name=app.config['TIMEZONE'], currency=app.config['CURRENCY'], server_now=now())

    @app.before_request
    def protection():
        if request.path == '/health' and request.method == 'GET':
            return None
        if request.host != origin.netloc:
            abort(404)
        if request.method == 'POST':
            source = request.headers.get('Origin')
            if request.headers.get('Sec-Fetch-Site') == 'cross-site' or (source and source not in (app.config['ORIGIN'], 'null')):
                abort(403)
            if not hmac.compare_digest(request.form.get('csrf', '').encode(), session.get('csrf', 'invalid').encode()):
                abort(403, 'Your session expired. Reload this page and try again.')
        if request.endpoint not in ('login', 'static') and not session.get('owner'):
            return redirect(url_for('login'))

    @app.after_request
    def headers(response):
        response.headers.update({'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY', 'Referrer-Policy': 'no-referrer', 'X-Robots-Tag': 'noindex, nofollow',
            'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"})
        if not app.testing:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000'
        return response

    def one(sql, params=()):
        row = db().execute(sql, params).fetchone()
        if row is None:
            abort(404)
        return row

    def field(key, limit=200, required=False):
        value = request.form.get(key, '').strip()
        if len(value) > limit or (required and not value):
            raise ValueError(f'Please complete {key.replace("_", " ")} (maximum {limit:,} characters).')
        return value

    def rate(value):
        try:
            number = Decimal(value)
            if not number.is_finite() or number < 0 or number > 100000 or number.as_tuple().exponent < -2:
                raise ValueError('Use a rate from 0 to 100,000 with at most two decimal places.')
            return int(number * 100)
        except InvalidOperation:
            raise ValueError('Enter a valid hourly rate.') from None

    def parse_local(value):
        try:
            naive = datetime.strptime(value, '%Y-%m-%dT%H:%M')
            if not 2000 <= naive.year <= 2100:
                raise ValueError()
            aware = naive.replace(tzinfo=tz)
            # Reject DST gaps instead of silently moving a scheduled event.
            if datetime.fromtimestamp(aware.timestamp(), tz).replace(tzinfo=None) != naive:
                raise ValueError()
            if aware.utcoffset() != naive.replace(tzinfo=tz, fold=1).utcoffset():
                raise ValueError('That time occurs twice during a daylight-saving change. Choose an unambiguous time.')
            return int(aware.timestamp())
        except ValueError as exc:
            raise ValueError(str(exc) if str(exc).startswith('That time') else 'Choose a valid date and time in the workspace timezone (2000–2100).') from None

    def open_entry():
        return db().execute("SELECT e.*, c.name, c.color FROM entries e JOIN clients c ON c.id=e.client_id WHERE e.status IN ('running','draft')").fetchone()

    def entry_rows(client_id=None, start=None, end=None):
        clauses, params = ["e.status='complete'"], []
        for clause, value in [('e.client_id=?', client_id), ('e.started_at>=?', start), ('e.started_at<?', end)]:
            if value is not None:
                clauses.append(clause)
                params.append(value)
        rows = db().execute('SELECT e.*, c.name, c.color FROM entries e JOIN clients c ON c.id=e.client_id WHERE ' + ' AND '.join(clauses) + ' ORDER BY e.started_at DESC', params).fetchall()
        return [dict(row, seconds=row['ended_at'] - row['started_at'], amount=earnings(row['ended_at'] - row['started_at'], row['rate_cents'])) for row in rows]

    @app.get('/health')
    def health():
        db().execute('SELECT 1')
        return {'status': 'ok'}

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        error = None
        if request.method == 'POST':
            with db():
                db().execute('BEGIN IMMEDIATE')
                db().execute('DELETE FROM login_attempts WHERE created_at<?', (now() - 300,))
                if db().execute('SELECT count(*) FROM login_attempts').fetchone()[0] >= 10:
                    abort(429, 'Too many sign-in attempts. Try again in five minutes.')
                db().execute('INSERT INTO login_attempts VALUES (?)', (now(),))
            valid_password = check_password_hash(app.config['ADMIN_PASSWORD_HASH'], request.form.get('password', ''))
            valid_name = hmac.compare_digest(request.form.get('username', '').encode(), app.config['ADMIN_USERNAME'].encode())
            if valid_password and valid_name:
                session.clear()
                session['owner'] = True
                session.permanent = True
                csrf()
                return redirect(url_for('dashboard'))
            error = 'That login or password was not accepted.'
        return render_template('login.html', error=error, title='Welcome back')

    @app.post('/logout')
    def logout():
        session.clear()
        return redirect(url_for('login'))

    @app.get('/')
    def dashboard():
        current = local(now())
        week_start = current.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=current.weekday())
        rows = entry_rows(start=int(week_start.timestamp()))
        return render_template('dashboard.html', title='Overview', active=open_entry(),
            clients=db().execute('SELECT * FROM clients WHERE archived=0 ORDER BY name').fetchall(),
            week_seconds=sum(row['seconds'] for row in rows), week_amount=sum(row['amount'] for row in rows),
            recent=entry_rows()[:5], current=current,
            upcoming=db().execute('SELECT ev.*, c.name FROM events ev LEFT JOIN clients c ON c.id=ev.client_id WHERE ev.ends_at>? ORDER BY ev.starts_at LIMIT 4', (now(),)).fetchall())

    @app.get('/api/timer')
    def timer_state():
        active = open_entry()
        return jsonify(server_now=now(), entry=dict(active) if active else None)

    @app.post('/clock-in')
    def clock_in():
        with db():
            db().execute('BEGIN IMMEDIATE')
            if active := open_entry():
                flash('Finish your current session before starting another.', 'error')
                return redirect(url_for('journal', entry_id=active['id']) if active['status'] == 'draft' else url_for('dashboard'))
            client = one('SELECT * FROM clients WHERE id=? AND archived=0', (request.form.get('client_id', ''),))
            db().execute("INSERT INTO entries(id,client_id,rate_cents,started_at,status) VALUES(?,?,?,?,'running')", (secrets.token_hex(12), client['id'], client['rate_cents'], now()))
        return redirect(url_for('dashboard'))

    @app.post('/clock-out/<entry_id>')
    def clock_out(entry_id):
        with db():
            db().execute('BEGIN IMMEDIATE')
            entry = one('SELECT * FROM entries WHERE id=?', (entry_id,))
            if entry['status'] == 'running':
                db().execute("UPDATE entries SET ended_at=?,status='draft' WHERE id=?", (max(now(), entry['started_at']), entry_id))
        return redirect(url_for('journal', entry_id=entry_id))

    @app.route('/journal/<entry_id>', methods=['GET', 'POST'])
    def journal(entry_id):
        entry = one('SELECT e.*, c.name FROM entries e JOIN clients c ON c.id=e.client_id WHERE e.id=?', (entry_id,))
        if entry['status'] == 'running':
            return redirect(url_for('dashboard'))
        error = None
        if request.method == 'POST':
            try:
                summary = field('summary', 2000, True)
                deliverables = field('deliverables', 6000, True)
                next_steps, private_notes = field('next_steps', 3000), field('private_notes', 6000)
                with db():
                    result = db().execute("UPDATE entries SET summary=?,deliverables=?,next_steps=?,private_notes=?,status='complete',revision=revision+1 WHERE id=? AND revision=?", (summary, deliverables, next_steps, private_notes, entry_id, request.form.get('revision', '-1')))
                    if result.rowcount != 1:
                        abort(409, 'This work log changed in another tab. Reload before editing it again.')
                flash('Work log saved. Your client report is ready.', 'success')
                return redirect(url_for('client_detail', client_id=entry['client_id']))
            except ValueError as exc:
                error = str(exc)
        return render_template('journal.html', title='Session wrap-up', entry=entry, error=error,
            seconds=entry['ended_at'] - entry['started_at'], amount=earnings(entry['ended_at'] - entry['started_at'], entry['rate_cents']))

    @app.get('/clients')
    def clients():
        return render_template('clients.html', title='Clients', clients=db().execute('SELECT * FROM clients ORDER BY archived,name').fetchall())

    @app.route('/clients/new', methods=['GET', 'POST'])
    @app.route('/clients/<client_id>/edit', methods=['GET', 'POST'])
    def client_form(client_id=None):
        client = one('SELECT * FROM clients WHERE id=?', (client_id,)) if client_id else None
        error = None
        if request.method == 'POST':
            try:
                name, contact, email = field('name', 160, True), field('contact', 160), field('email', 254)
                if email and not re.fullmatch(r'[^\s<>@]+@[^\s<>@]+\.[^\s<>@]+', email):
                    raise ValueError('Enter a valid email address.')
                phone, notes, color = field('phone', 80), field('notes', 6000), field('color', 20)
                if color not in COLORS:
                    raise ValueError('Choose one of the client colors.')
                cents = rate(field('rate', 20, True))
                with db():
                    if client:
                        db().execute('UPDATE clients SET name=?,contact=?,email=?,phone=?,rate_cents=?,color=?,notes=? WHERE id=?', (name, contact, email, phone, cents, color, notes, client_id))
                    else:
                        client_id = secrets.token_hex(12)
                        db().execute('INSERT INTO clients(id,name,contact,email,phone,rate_cents,color,notes,created_at) VALUES(?,?,?,?,?,?,?,?,?)', (client_id, name, contact, email, phone, cents, color, notes, now()))
                flash('Client saved.', 'success')
                return redirect(url_for('client_detail', client_id=client_id))
            except ValueError as exc:
                error = str(exc)
        return render_template('client-form.html', title='Edit client' if client else 'New client', client=client, error=error)

    @app.get('/clients/<client_id>')
    def client_detail(client_id):
        client = one('SELECT * FROM clients WHERE id=?', (client_id,))
        rows = entry_rows(client_id)
        return render_template('client.html', title=client['name'], client=client, entries=rows,
            total_seconds=sum(row['seconds'] for row in rows), total_amount=sum(row['amount'] for row in rows),
            documents=db().execute('SELECT id,name,size,created_at FROM documents WHERE client_id=? ORDER BY created_at DESC', (client_id,)).fetchall())

    @app.post('/clients/<client_id>/archive')
    def archive_client(client_id):
        with db():
            db().execute('BEGIN IMMEDIATE')
            client = one('SELECT * FROM clients WHERE id=?', (client_id,))
            if db().execute("SELECT 1 FROM entries WHERE client_id=? AND status IN ('running','draft')", (client_id,)).fetchone():
                flash('Finish this client’s open session before archiving.', 'error')
            else:
                db().execute('UPDATE clients SET archived=? WHERE id=?', (0 if client['archived'] else 1, client_id))
                flash('Client restored.' if client['archived'] else 'Client archived. Their history and documents are preserved.', 'success')
        return redirect(url_for('client_detail', client_id=client_id))

    @app.post('/clients/<client_id>/documents')
    def upload_document(client_id):
        one('SELECT id FROM clients WHERE id=?', (client_id,))
        file = request.files.get('document')
        name = secure_filename(file.filename or '') if file else ''
        if not name or len(name) > 180 or Path(name).suffix.lower() not in ('.pdf', '.docx', '.xlsx', '.txt', '.csv', '.png', '.jpg', '.jpeg'):
            abort(400, 'Choose a PDF, DOCX, XLSX, text, CSV, PNG, or JPEG document.')
        content = file.read(10 * 1024 * 1024 + 1)
        if not content or len(content) > 10 * 1024 * 1024:
            abort(400, 'Documents must contain data and be no larger than 10 MB.')
        with db():
            db().execute('INSERT INTO documents VALUES(?,?,?,?,?,?)', (secrets.token_hex(12), client_id, name, len(content), content, now()))
        flash('Document uploaded privately.', 'success')
        return redirect(url_for('client_detail', client_id=client_id))

    @app.get('/documents/<document_id>')
    def download_document(document_id):
        document = one('SELECT * FROM documents WHERE id=?', (document_id,))
        return send_file(io.BytesIO(document['content']), mimetype='application/octet-stream', as_attachment=True, download_name=document['name'])

    @app.get('/work-log')
    def work_log():
        selected = request.args.get('client') or None
        return render_template('work-log.html', title='Work log', entries=entry_rows(selected), active=open_entry(), selected=selected,
            clients=db().execute('SELECT id,name FROM clients ORDER BY name').fetchall())

    @app.get('/clients/<client_id>/report')
    def report(client_id):
        client = one('SELECT * FROM clients WHERE id=?', (client_id,))
        start_text, end_text = request.args.get('from', ''), request.args.get('to', '')
        start = end = None
        try:
            if start_text:
                start = parse_local(start_text + 'T00:00')
            if end_text:
                end = int((datetime.strptime(end_text, '%Y-%m-%d').replace(tzinfo=tz) + timedelta(days=1)).timestamp())
            if start is not None and end is not None and end <= start:
                raise ValueError('Choose an end date on or after the start date.')
        except ValueError:
            abort(400, 'Choose a valid report date range.')
        rows = entry_rows(client_id, start, end)
        if request.args.get('format') == 'csv':
            output = io.StringIO(newline='')
            writer = csv.writer(output)
            writer.writerow(['Client', 'Start (' + app.config['TIMEZONE'] + ')', 'End', 'Hours', 'Hourly rate (' + app.config['CURRENCY'] + ')', 'Estimated earnings', 'Summary', 'Deliverables', 'Next steps'])
            def safe(value):
                value = str(value)
                return "'" + value if value.lstrip().startswith(('=', '+', '-', '@')) or value.startswith(('\t', '\r', '\n')) else value
            for row in rows:
                writer.writerow([safe(client['name']), local(row['started_at']).isoformat(), local(row['ended_at']).isoformat(), f"{row['seconds']/3600:.4f}", f"{row['rate_cents']/100:.2f}", f"{row['amount']/100:.2f}", safe(row['summary']), safe(row['deliverables']), safe(row['next_steps'])])
            return send_file(io.BytesIO(output.getvalue().encode('utf-8-sig')), mimetype='text/csv', as_attachment=True, download_name='client-work-report.csv')
        return render_template('report.html', title='Client work report', client=client, entries=rows,
            total_seconds=sum(row['seconds'] for row in rows), total_amount=sum(row['amount'] for row in rows), start_text=start_text, end_text=end_text)

    @app.get('/calendar')
    def calendar_view():
        current = local(now())
        try:
            month = datetime.strptime(request.args.get('month', current.strftime('%Y-%m')), '%Y-%m').replace(tzinfo=tz)
            if not 2001 <= month.year <= 2099:
                raise ValueError()
        except ValueError:
            abort(400, 'Choose a calendar month between 2001 and 2099.')
        dates = list(calendar.Calendar(firstweekday=0).itermonthdates(month.year, month.month))
        begin = datetime.combine(dates[0], datetime.min.time(), tz)
        end = datetime.combine(dates[-1] + timedelta(days=1), datetime.min.time(), tz)
        events = db().execute('SELECT ev.*,c.name FROM events ev LEFT JOIN clients c ON c.id=ev.client_id WHERE ev.starts_at<? AND ev.ends_at>? ORDER BY ev.starts_at', (int(end.timestamp()), int(begin.timestamp()))).fetchall()
        days = [dict(date=day, events=[ev for ev in events if local(ev['starts_at']).date() <= day <= local(ev['ends_at'] - 1).date()]) for day in dates]
        next_month = (month.replace(day=28) + timedelta(days=4)).replace(day=1)
        return render_template('calendar.html', title='Calendar', month=month, days=days, events=events, today=current.date(),
            previous=(month - timedelta(days=1)).strftime('%Y-%m'), following=next_month.strftime('%Y-%m'))

    @app.route('/events/new', methods=['GET', 'POST'])
    @app.route('/events/<event_id>', methods=['GET', 'POST'])
    def event_form(event_id=None):
        event = one('SELECT * FROM events WHERE id=?', (event_id,)) if event_id else None
        error = None
        if request.method == 'POST':
            try:
                title, kind, notes = field('title', 160, True), field('kind', 20, True), field('notes', 4000)
                if kind not in KINDS:
                    raise ValueError('Choose an event type.')
                client_id = field('client_id', 40) or None
                if client_id:
                    one('SELECT id FROM clients WHERE id=?', (client_id,))
                start, end = parse_local(field('starts_at', 30, True)), parse_local(field('ends_at', 30, True))
                if end <= start:
                    raise ValueError('End time must be after start time.')
                with db():
                    if event:
                        changed = db().execute('UPDATE events SET title=?,kind=?,client_id=?,starts_at=?,ends_at=?,notes=?,revision=revision+1 WHERE id=? AND revision=?', (title, kind, client_id, start, end, notes, event_id, request.form.get('revision', '-1')))
                        if changed.rowcount != 1:
                            abort(409, 'This event changed in another tab. Reload before editing.')
                    else:
                        event_id = secrets.token_hex(12)
                        db().execute('INSERT INTO events(id,client_id,title,kind,starts_at,ends_at,notes) VALUES(?,?,?,?,?,?,?)', (event_id, client_id, title, kind, start, end, notes))
                flash('Calendar updated.', 'success')
                return redirect(url_for('calendar_view', month=local(start).strftime('%Y-%m')))
            except ValueError as exc:
                error = str(exc)
        return render_template('event-form.html', title='Edit event' if event else 'New event', event=event, error=error,
            clients=db().execute('SELECT id,name FROM clients ORDER BY archived,name').fetchall())

    @app.post('/events/<event_id>/delete')
    def delete_event(event_id):
        event = one('SELECT * FROM events WHERE id=?', (event_id,))
        with db():
            changed = db().execute('DELETE FROM events WHERE id=? AND revision=?', (event_id, request.form.get('revision', '-1')))
            if changed.rowcount != 1:
                abort(409, 'This event changed in another tab. Reload before deleting.')
        flash('Event removed.', 'success')
        return redirect(url_for('calendar_view', month=local(event['starts_at']).strftime('%Y-%m')))

    @app.errorhandler(400)
    @app.errorhandler(403)
    @app.errorhandler(404)
    @app.errorhandler(409)
    @app.errorhandler(413)
    @app.errorhandler(429)
    def error_page(error):
        return render_template('error.html', title='Request not completed', error=error.description), error.code

    return app
