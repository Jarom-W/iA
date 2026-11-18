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

from itsdangerous import URLSafeTimedSerializer, BadSignature

from flask import Flask, abort, flash, g, jsonify, redirect, render_template, request, send_file, session, url_for
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
from ia_auth import auth_settings, init_auth
from reports import groups_for, pdf_report

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
    app.config.update(auth_settings())
    if config:
        app.config.update(config)
    if len(app.config['SECRET_KEY'] or '') < 32 or (app.config['AUTH_MODE'] == 'legacy' and not app.config['ADMIN_PASSWORD_HASH']):
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
        # Additive, transactional migration; historical rate amounts remain untouched.
        with conn:
            conn.execute('BEGIN IMMEDIATE')
            columns = {row[1] for row in conn.execute('PRAGMA table_info(entries)')}
            if 'rate_label' not in columns:
                conn.execute("ALTER TABLE entries ADD COLUMN rate_label TEXT NOT NULL DEFAULT 'Default'")
            if 'source' not in columns:
                conn.execute("ALTER TABLE entries ADD COLUMN source TEXT NOT NULL DEFAULT 'timer'")
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
        auth = app.extensions.get('platform_auth')
        if auth and request.endpoint not in ('login', 'static', 'logout') and not (request.endpoint or '').startswith('platform_auth.'):
            permissions = ['time:read']
            if request.method == 'POST':
                permissions.append('time:write')
            if request.endpoint == 'download_document':
                permissions.append('time:documents:read')
            if request.endpoint == 'upload_document':
                permissions.append('time:documents:write')
            # Edit forms contain private data too; require edit permission before rendering.
            if request.endpoint in ('client_form', 'event_form', 'journal', 'entry_form', 'rate_form'):
                permissions.append('time:write')
            return auth.require(*permissions)
        if not auth and request.endpoint not in ('login', 'static') and not session.get('owner'):
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

    def entry_rows(client_id=None, start=None, end=None, overlap=False):
        clauses, params = ["e.status='complete'"], []
        for clause, value in [('e.client_id=?', client_id), ('e.ended_at>?' if overlap else 'e.started_at>=?', start), ('e.started_at<?', end)]:
            if value is not None:
                clauses.append(clause)
                params.append(value)
        rows = db().execute('SELECT e.*, c.name, c.color FROM entries e JOIN clients c ON c.id=e.client_id WHERE ' + ' AND '.join(clauses) + ' ORDER BY e.started_at DESC', params).fetchall()
        result = []
        for row in rows:
            begin = max(row['started_at'], start) if overlap and start is not None else row['started_at']
            finish = min(row['ended_at'], end) if overlap and end is not None else row['ended_at']
            result.append(dict(row, started_at=begin, ended_at=finish, partial=(begin != row['started_at'] or finish != row['ended_at']),
                seconds=finish-begin, amount=earnings(finish-begin, row['rate_cents'])))
        return result

    @app.get('/health')
    def health():
        db().execute('SELECT 1')
        return {'status': 'ok'}

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if app.config['AUTH_MODE'] == 'oidc':
            if request.method == 'POST':
                abort(405)
            return render_template('login.html', title='Sign in')
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
        if auth := app.extensions.get('platform_auth'):
            return auth.logout()
        session.clear()
        return redirect(url_for('login'))

    @app.get('/')
    def dashboard():
        current = local(now())
        week_start = current.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=current.weekday())
        rows = entry_rows(start=int(week_start.timestamp()))
        return render_template('dashboard.html', title='Overview', active=open_entry(),
            clients=db().execute('SELECT * FROM clients WHERE archived=0 ORDER BY name').fetchall(), rate_options=rate_options(),
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
            try:
                cents, label = chosen_rate(client)
            except ValueError as exc:
                flash(str(exc), 'error')
                return redirect(url_for('dashboard'))
            db().execute("INSERT INTO entries(id,client_id,rate_cents,rate_label,started_at,status) VALUES(?,?,?,?,?,'running')", (secrets.token_hex(12), client['id'], cents, label, now()))
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

    def rate_options():
        options = [dict(id='default:' + c['id'], client_id=c['id'], label='Default', rate_cents=c['rate_cents'])
                   for c in db().execute('SELECT id,rate_cents FROM clients')]
        options.extend(dict(r) for r in db().execute('SELECT * FROM client_rates WHERE archived=0 ORDER BY label'))
        return options

    def chosen_rate(client, entry=None, custom=False):
        choice = request.form.get('rate_id', '')
        if choice == 'keep' and entry and entry['client_id'] == client['id']:
            return entry['rate_cents'], entry['rate_label']
        if choice == 'custom' and custom:
            return rate(field('custom_rate', 20, True)), field('custom_label', 100, True)
        if choice == 'default:' + client['id'] or (not choice and not db().execute('SELECT 1 FROM client_rates WHERE client_id=? AND archived=0', (client['id'],)).fetchone()):
            return client['rate_cents'], 'Default'
        selected = db().execute('SELECT * FROM client_rates WHERE id=? AND client_id=? AND archived=0', (choice, client['id'])).fetchone()
        if not selected:
            raise ValueError('Choose a billing rate for this client.')
        return selected['rate_cents'], selected['label']

    @app.route('/clients/<client_id>/rates/new', methods=['GET', 'POST'])
    @app.route('/clients/<client_id>/rates/<rate_id>', methods=['GET', 'POST'])
    def rate_form(client_id, rate_id=None):
        client = one('SELECT * FROM clients WHERE id=?', (client_id,))
        item = one('SELECT * FROM client_rates WHERE id=? AND client_id=?', (rate_id, client_id)) if rate_id else None
        error = None
        if request.method == 'POST':
            try:
                label, cents = field('label', 100, True), rate(field('rate', 20, True))
                archived = int(request.form.get('archived') == '1')
                with db():
                    if item:
                        result = db().execute('UPDATE client_rates SET label=?,rate_cents=?,archived=?,revision=revision+1 WHERE id=? AND revision=?',
                            (label,cents,archived,rate_id,request.form.get('revision','-1')))
                        if result.rowcount != 1: abort(409, 'This rate changed in another tab. Reload before editing.')
                    else:
                        db().execute('INSERT INTO client_rates(id,client_id,label,rate_cents) VALUES(?,?,?,?)', (secrets.token_hex(12),client_id,label,cents))
                flash('Rate saved. Existing sessions keep their recorded rate.', 'success')
                return redirect(url_for('client_detail',client_id=client_id))
            except ValueError as exc: error = str(exc)
        return render_template('rate-form.html', title='Edit billing rate' if item else 'Add billing rate', client=client, item=item, error=error)

    entry_signer = URLSafeTimedSerializer(app.secret_key, salt='manual-time-entry')

    @app.route('/entries/new', methods=['GET', 'POST'])
    @app.route('/entries/<entry_id>/edit', methods=['GET', 'POST'])
    def entry_form(entry_id=None):
        entry = one('SELECT * FROM entries WHERE id=?', (entry_id,)) if entry_id else None
        if entry and entry['status'] == 'running':
            flash('Clock out before changing the session time or rate.', 'error')
            return redirect(url_for('dashboard'))
        error = None
        ticket = request.form.get('creation_token', '') if request.method == 'POST' else entry_signer.dumps({'id':secrets.token_hex(12),'csrf':csrf()})
        if request.method == 'POST':
            try:
                client = one('SELECT * FROM clients WHERE id=?', (field('client_id',40,True),))
                if client['archived'] and (not entry or client['id'] != entry['client_id']):
                    raise ValueError('Restore this client before adding time.')
                cents, label = chosen_rate(client, entry, custom=True)
                start_text = field('started_at',30,True)
                start = entry['started_at'] if entry and start_text == local(entry['started_at']).strftime('%Y-%m-%dT%H:%M') else parse_local(start_text)
                # Preserve exact timer seconds when its displayed hours are unchanged.
                hours_text = field('hours',30,True)
                hours = Decimal(hours_text)
                if not hours.is_finite() or hours <= 0 or hours > 744:
                    raise ValueError('Enter hours greater than zero and no more than 744.')
                seconds = int((hours * 3600).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
                if entry and hours_text == f"{(entry['ended_at']-entry['started_at'])/3600:.6f}":
                    seconds = entry['ended_at']-entry['started_at']
                if seconds < 1 or start + seconds > now():
                    raise ValueError('Recorded time must end in the past and last at least one second.')
                summary = field('summary',2000,True)
                deliverables = field('deliverables',6000,True)
                next_steps, private_notes = field('next_steps',3000), field('private_notes',6000)
                values = (client['id'],cents,label,start,start+seconds,summary,deliverables,next_steps,private_notes)
                with db():
                    if entry:
                        changed = db().execute("UPDATE entries SET client_id=?,rate_cents=?,rate_label=?,started_at=?,ended_at=?,summary=?,deliverables=?,next_steps=?,private_notes=?,status='complete',revision=revision+1 WHERE id=? AND revision=? AND status!='running'", values+(entry_id,request.form.get('revision','-1')))
                        if changed.rowcount != 1: abort(409,'This entry changed in another tab. Reload before editing.')
                    else:
                        try:
                            signed = entry_signer.loads(ticket,max_age=86400)
                            if signed['csrf'] != csrf(): raise ValueError()
                        except (BadSignature,KeyError,ValueError):
                            abort(400,'This entry form expired. Open Add time again.')
                        entry_id = signed['id']
                        db().execute("INSERT INTO entries(client_id,rate_cents,rate_label,started_at,ended_at,summary,deliverables,next_steps,private_notes,id,status,source) VALUES(?,?,?,?,?,?,?,?,?,?,'complete','manual') ON CONFLICT(id) DO NOTHING", values+(entry_id,))
                flash('Time entry saved.', 'success')
                return redirect(url_for('calendar_view',month=local(start).strftime('%Y-%m'),client=client['id']))
            except (ValueError, InvalidOperation) as exc:
                error = str(exc) if not isinstance(exc,InvalidOperation) else 'Enter a valid number of hours.'
        default_date = request.args.get('date',local(now()).date().isoformat())
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',default_date): default_date=local(now()).date().isoformat()
        return render_template('entry-form.html',title='Edit time entry' if entry else 'Add time',entry=entry,error=error,creation_token=ticket,
            selected=request.args.get('client',''),default_start=default_date+'T09:00', rate_options=rate_options(),
            clients=db().execute('SELECT * FROM clients ORDER BY archived,name').fetchall())

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
            rates=db().execute('SELECT * FROM client_rates WHERE client_id=? ORDER BY archived,label', (client_id,)).fetchall(),
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

    def report_range():
        start_text, end_text = request.args.get('from', ''), request.args.get('to', '')
        start = end = None
        try:
            if start_text:
                start = parse_local(start_text + 'T00:00')
            if end_text:
                day = datetime.strptime(end_text, '%Y-%m-%d')
                if not 2000 <= day.year <= 2100:
                    raise ValueError()
                end = int((day.replace(tzinfo=tz) + timedelta(days=1)).timestamp())
            if start is not None and end is not None and end <= start:
                raise ValueError()
        except ValueError:
            abort(400, 'Choose a valid report date range, with the end on or after the start.')
        return start_text, end_text, start, end

    @app.get('/work-log')
    def work_log():
        selected = request.args.get('client') or None
        if selected:
            one('SELECT id FROM clients WHERE id=?', (selected,))
        start_text, end_text, start, end = report_range()
        rows = entry_rows(selected, start, end, overlap=True)
        current = local(now()).date()
        return render_template('work-log.html', title='Work log', entries=rows, active=open_entry(), selected=selected,
            clients=db().execute('SELECT id,name FROM clients ORDER BY name').fetchall(),
            start_text=start_text, end_text=end_text, total_seconds=sum(r['seconds'] for r in rows), total_amount=sum(r['amount'] for r in rows),
            month_start=current.replace(day=1).isoformat(), today=current.isoformat())

    @app.get('/work-log/report')
    @app.get('/clients/<client_id>/report')
    def report(client_id=None):
        selected = client_id or request.args.get('client') or None
        client = one('SELECT * FROM clients WHERE id=?', (selected,)) if selected else None
        start_text, end_text, start, end = report_range()
        rows = entry_rows(selected, start, end, overlap=True)
        if request.args.get('format') == 'pdf':
            return send_file(pdf_report(rows, app.config['TIMEZONE'], app.config['CURRENCY'], start_text, end_text, client['name'] if client else None),
                mimetype='application/pdf', as_attachment=True, download_name=f'work-report-{start_text or "all"}-to-{end_text or "latest"}.pdf')
        if request.args.get('format') == 'csv':
            output = io.StringIO(newline='')
            writer = csv.writer(output)
            writer.writerow(['Client', 'Start (' + app.config['TIMEZONE'] + ')', 'End', 'Hours', 'Hourly rate (' + app.config['CURRENCY'] + ')', 'Estimated earnings', 'Summary', 'Deliverables', 'Next steps', 'Session reference', 'Partial session', 'Rate name'])
            def safe(value):
                value = str(value)
                return "'" + value if value.lstrip().startswith(('=', '+', '-', '@')) or value.startswith(('\t', '\r', '\n')) else value
            for group in groups_for(rows):
                for row in group['entries']:
                    writer.writerow([safe(row['name']), local(row['started_at']).isoformat(), local(row['ended_at']).isoformat(), f"{row['seconds']/3600:.4f}", f"{row['rate_cents']/100:.2f}", f"{row['amount']/100:.2f}", safe(row['summary']), safe(row['deliverables']), safe(row['next_steps']), row['id'], 'yes' if row['partial'] else 'no', safe(row['rate_label'])])
                writer.writerow([safe(group['name']) + ' subtotal', '', '', f"{group['seconds']/3600:.4f}", '', f"{group['amount']/100:.2f}"])
            writer.writerow(['Grand total', '', '', f"{sum(r['seconds'] for r in rows)/3600:.4f}", '', f"{sum(r['amount'] for r in rows)/100:.2f}"])
            return send_file(io.BytesIO(output.getvalue().encode('utf-8-sig')), mimetype='text/csv', as_attachment=True, download_name='client-work-report.csv')
        return render_template('report.html', title='Client work report', client=client, selected=selected, groups=groups_for(rows), entries=rows,
            total_seconds=sum(row['seconds'] for row in rows), total_amount=sum(row['amount'] for row in rows), start_text=start_text, end_text=end_text)

    @app.get('/monthly-summary')
    def monthly_summary():
        current = local(now())
        try:
            month = datetime.strptime(request.args.get('month',current.strftime('%Y-%m')), '%Y-%m').replace(tzinfo=tz)
            if not 2001 <= month.year <= 2099: raise ValueError()
        except ValueError: abort(400,'Choose a month between 2001 and 2099.')
        following = (month.replace(day=28)+timedelta(days=4)).replace(day=1)
        selected = request.args.get('client') or None
        if selected: one('SELECT id FROM clients WHERE id=?',(selected,))
        start, end = int(month.timestamp()), int(following.timestamp())
        rows = entry_rows(selected,start,end,overlap=True)
        grouped = {}
        for row in sorted(rows,key=lambda r:(r['name'].casefold(),r['client_id'],r['rate_cents'],r['started_at'])):
            key = (row['client_id'],row['rate_cents'])
            group = grouped.setdefault(key,dict(name=row['name'],client_id=row['client_id'],rate_cents=row['rate_cents'],seconds=0,labels=set(),entries=[]))
            group['seconds'] += row['seconds']; group['labels'].add(row['rate_label']); group['entries'].append(row)
        groups = list(grouped.values())
        for group in groups:
            group['amount'] = earnings(group['seconds'],group['rate_cents'])
            group['labels'] = ', '.join(sorted(group['labels']))
            group['description'] = '\n\n'.join(
                local(row['started_at']).strftime('%b %d')+' · '+row['rate_label']+' · '+row['summary']+'\n'+row['deliverables']
                + ('\nNext steps: '+row['next_steps'] if row['next_steps'] else '')
                + ('\nOnly the portion within this month is included.' if row['partial'] else '')
                for row in group['entries'])
        pending_sql = "SELECT COUNT(*) FROM entries WHERE status!='complete' AND started_at<? AND COALESCE(ended_at,?)>?"
        pending_params = [end,now(),start]
        if selected: pending_sql += ' AND client_id=?'; pending_params.append(selected)
        pending = db().execute(pending_sql,pending_params).fetchone()[0]
        if request.args.get('format') == 'csv':
            output = io.StringIO(newline=''); writer=csv.writer(output)
            def safe(value):
                value=str(value)
                return "'"+value if value.lstrip().startswith(('=','+','-','@')) or value.startswith(('\t','\r','\n')) else value
            writer.writerow(['Month','Client','Rate labels','Hours','Hourly rate ('+app.config['CURRENCY']+')','Amount ('+app.config['CURRENCY']+')','Description'])
            for group in groups:
                writer.writerow([month.strftime('%Y-%m'),safe(group['name']),safe(group['labels']),f"{group['seconds']/3600:.6f}",f"{group['rate_cents']/100:.2f}",f"{group['amount']/100:.2f}",safe(group['description'])])
            return send_file(io.BytesIO(output.getvalue().encode('utf-8-sig')),mimetype='text/csv',as_attachment=True,download_name='monthly-time-'+month.strftime('%Y-%m')+'.csv')
        return render_template('monthly-summary.html',title='Monthly billing summary',month=month,selected=selected,groups=groups,pending=pending,
            total_seconds=sum(g['seconds'] for g in groups),total_amount=sum(g['amount'] for g in groups),
            clients=db().execute('SELECT id,name FROM clients ORDER BY name').fetchall(),
            start_text=month.date().isoformat(),end_text=(following-timedelta(days=1)).date().isoformat())

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
        selected = request.args.get('client') or None
        if selected: one('SELECT id FROM clients WHERE id=?', (selected,))
        if selected: events = [event for event in events if event['client_id'] == selected]
        rows = entry_rows(selected, int(begin.timestamp()), int(end.timestamp()), overlap=True)
        days = []
        for day in dates:
            day_start = int(datetime.combine(day,datetime.min.time(),tz).timestamp())
            day_end = int(datetime.combine(day+timedelta(days=1),datetime.min.time(),tz).timestamp())
            work = [dict(row, day_seconds=min(row['ended_at'],day_end)-max(row['started_at'],day_start)) for row in rows if row['started_at']<day_end and row['ended_at']>day_start]
            days.append(dict(date=day,entries=work,seconds=sum(row['day_seconds'] for row in work),events=[ev for ev in events if local(ev['starts_at']).date() <= day <= local(ev['ends_at'] - 1).date()]))
        next_month = (month.replace(day=28) + timedelta(days=4)).replace(day=1)
        return render_template('calendar.html', title='Calendar', month=month, days=days, events=events, today=current.date(), selected=selected, entries=rows, clients=db().execute('SELECT id,name FROM clients ORDER BY name').fetchall(),
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

    @app.errorhandler(401)
    @app.errorhandler(503)
    @app.errorhandler(400)
    @app.errorhandler(403)
    @app.errorhandler(404)
    @app.errorhandler(409)
    @app.errorhandler(413)
    @app.errorhandler(429)
    def error_page(error):
        return render_template('error.html', title='Request not completed', error=error.description), error.code

    init_auth(app, app.config['ORIGIN'], '/', 'owner')
    return app
