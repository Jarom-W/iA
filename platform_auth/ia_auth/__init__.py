"""Shared OIDC client and server-enforced permissions. Keycloak owns authentication."""
import base64
from contextlib import closing
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import sqlite3
import time
from urllib.parse import urlencode, urlsplit

from authlib.integrations.flask_client import OAuth
from authlib.integrations.base_client.errors import OAuthError
from cryptography.fernet import Fernet, InvalidToken
from flask import Blueprint, abort, g, redirect, request, session, url_for
from joserfc.errors import JoseError
import requests

# Application permissions are deliberately distinct from OIDC identity scopes.
PERMISSIONS = {
    'platform:manage': ('Platform', 'Manage users and application access'),
    'feedback:read': ('Admin', 'Read forms, invitations, and feedback'),
    'feedback:write': ('Admin', 'Create invitations and manage testimonials'),
    'time:read': ('Time', 'Read all clients, sessions, calendar, and reports'),
    'time:write': ('Time', 'Manage clients, sessions, work logs, and calendar'),
    'time:documents:read': ('Time', 'Download client documents'),
    'time:documents:write': ('Time', 'Upload client documents'),
    'vault:access': ('Vault', 'Sign in to Vault (requires Vault integration)'),
}


def auth_settings():
    return dict(AUTH_MODE=os.getenv('AUTH_MODE', 'legacy'), OIDC_ISSUER=os.getenv('OIDC_ISSUER', ''),
        OIDC_CLIENT_ID=os.getenv('OIDC_CLIENT_ID', ''), OIDC_CLIENT_SECRET=os.getenv('OIDC_CLIENT_SECRET', ''),
        AUTH_DATABASE_PATH=os.getenv('AUTH_DATABASE_PATH', ''))


class PlatformAuth:
    def __init__(self, app, origin, home, flag):
        self.app, self.origin, self.home, self.flag = app, origin, home, flag
        if app.config['AUTH_MODE'] != 'oidc':
            raise RuntimeError('PlatformAuth requires AUTH_MODE=oidc.')
        self.issuer = app.config['OIDC_ISSUER'].rstrip('/')
        parsed = urlsplit(self.issuer)
        if not parsed.hostname or parsed.query or parsed.fragment or parsed.username or (parsed.scheme != 'https' and not (app.testing and parsed.scheme == 'http')):
            raise RuntimeError('OIDC_ISSUER must be an HTTPS issuer URL.')
        self.client_id, self.secret = app.config['OIDC_CLIENT_ID'], app.config['OIDC_CLIENT_SECRET']
        if not self.client_id or not self.secret:
            raise RuntimeError('OIDC client ID and secret are required; local login is disabled in OIDC mode.')
        self.database = Path(app.config['AUTH_DATABASE_PATH'] or str(app.config['DATABASE_PATH']) + '.auth.sqlite3')
        self.database.parent.mkdir(parents=True, exist_ok=True)
        self.cipher = Fernet(base64.urlsafe_b64encode(hashlib.sha256(app.secret_key.encode()).digest()))
        with closing(self.connect()) as conn, conn:
            conn.execute('CREATE TABLE IF NOT EXISTS auth_sessions (id TEXT PRIMARY KEY, payload BLOB NOT NULL, expires INTEGER NOT NULL)')
        self.database.chmod(0o600)
        self.oauth = OAuth(app)
        self.remote = self.oauth.register('platform', client_id=self.client_id, client_secret=self.secret,
            server_metadata_url=self.issuer + '/.well-known/openid-configuration',
            client_kwargs={'scope': 'openid platform-permissions', 'code_challenge_method': 'S256',
                'token_endpoint_auth_method': 'client_secret_basic', 'default_timeout': 8})
        bp = Blueprint('platform_auth', __name__, url_prefix='/auth')
        bp.before_request(self.protect)
        bp.add_url_rule('/login', 'login', self.login)
        bp.add_url_rule('/callback', 'callback', self.callback)
        bp.add_url_rule('/logout', 'logout', self.logout, methods=['POST'])
        app.register_blueprint(bp)
        app.extensions['platform_auth'] = self
        app.context_processor(lambda: {'central_auth': True, 'can': self.can})

    def connect(self):
        conn = sqlite3.connect(self.database, timeout=20)
        conn.row_factory = sqlite3.Row
        return conn

    def protect(self):
        if request.host != urlsplit(self.origin).netloc:
            abort(404)
        if request.method == 'POST':
            source = request.headers.get('Origin')
            if request.headers.get('Sec-Fetch-Site') == 'cross-site' or (source and source not in (self.origin, 'null')):
                abort(403)
            if not hmac.compare_digest(request.form.get('csrf', '').encode(), session.get('csrf', 'invalid').encode()):
                abort(403)

    def metadata(self):
        data = self.remote.load_server_metadata()
        if data.get('issuer') != self.issuer:
            raise ValueError('Unexpected identity provider issuer.')
        for key in ('authorization_endpoint', 'token_endpoint', 'jwks_uri', 'introspection_endpoint', 'end_session_endpoint', 'revocation_endpoint'):
            parsed = urlsplit(data.get(key, ''))
            trusted = urlsplit(self.issuer)
            if parsed.scheme != trusted.scheme or parsed.netloc != trusted.netloc or not parsed.path.startswith(trusted.path + '/'):
                raise ValueError('Unexpected identity provider endpoint.')
        # The realm signs identity tokens with RS256; do not accept algorithm changes.
        data['id_token_signing_alg_values_supported'] = ['RS256']
        return data

    def post_provider(self, endpoint, data):
        response = requests.post(self.metadata()[endpoint], data=data, auth=(self.client_id, self.secret), timeout=8, allow_redirects=False)
        response.raise_for_status()
        return response.json()

    def introspect(self, token, subject):
        info = self.post_provider('introspection_endpoint', {'token': token, 'token_type_hint': 'access_token'})
        if info.get('active') is not True:
            return None
        if info.get('sub') != subject or info.get('client_id') != self.client_id or info.get('iss') != self.issuer:
            raise ValueError('Unexpected token subject, client, or issuer.')
        permissions = info.get('permissions', [])
        if not isinstance(permissions, list) or not all(isinstance(value, str) for value in permissions):
            raise ValueError('Invalid permission claim.')
        return {'sub': subject, 'username': info.get('preferred_username', subject), 'permissions': permissions}

    def login(self):
        try:
            self.metadata()
            return self.remote.authorize_redirect(self.origin + '/auth/callback')
        except (requests.RequestException, ValueError, OAuthError):
            abort(503, 'Central sign-in is temporarily unavailable. Please try again.')

    def callback(self):
        try:
            self.metadata()
            # Authlib validates the state, PKCE exchange, signature, nonce,
            # issuer, audience, and token expiry before returning userinfo.
            token = self.remote.authorize_access_token(leeway=30)
            claims = token.get('userinfo')
            if not claims or not claims.get('sub') or not token.get('id_token'):
                raise ValueError('A verified identity token is required.')
            user = self.introspect(token['access_token'], claims['sub'])
            if not user:
                raise ValueError('Inactive token.')
            sid = secrets.token_urlsafe(48)
            record = {'token': dict(token), 'sub': claims['sub']}
            record['token'].pop('userinfo', None)
            encrypted = self.cipher.encrypt(json.dumps(record).encode())
            with closing(self.connect()) as db, db:
                db.execute('DELETE FROM auth_sessions WHERE expires<?', (int(time.time()),))
                if old := session.get('sso_sid'):
                    db.execute('DELETE FROM auth_sessions WHERE id=?', (self.digest(old),))
                db.execute('INSERT INTO auth_sessions VALUES(?,?,?)', (self.digest(sid), encrypted, int(time.time()) + 43200))
            session.clear()
            session.update(sso_sid=sid, csrf=secrets.token_urlsafe(32), display_name=user['username'])
            session[self.flag] = True  # UI compatibility only; never used for OIDC authorization.
            session.permanent = True
            return redirect('/admin/access' if self.flag == 'admin' and 'platform:manage' in user['permissions'] else self.home)
        except (requests.RequestException, ValueError, KeyError, OAuthError, JoseError) as exc:
            # Exception messages may contain provider responses; log only the class.
            self.app.logger.warning('OIDC callback rejected: %s', type(exc).__name__)
            session.clear()
            abort(400, 'Sign-in could not be verified. Start a new sign-in request.')

    @staticmethod
    def digest(value):
        return hashlib.sha256(value.encode()).hexdigest()

    def current(self):
        if hasattr(g, 'platform_user'):
            return g.platform_user
        g.platform_user = None
        sid = session.get('sso_sid')
        if not sid:
            return None
        try:
            with closing(self.connect()) as db, db:
                # Serialize refreshes so two tabs cannot reuse a rotating refresh token.
                db.execute('BEGIN IMMEDIATE')
                row = db.execute('SELECT * FROM auth_sessions WHERE id=?', (self.digest(sid),)).fetchone()
                if row is None or row['expires'] <= time.time():
                    db.execute('DELETE FROM auth_sessions WHERE id=?', (self.digest(sid),))
                    session.clear()
                    return None
                record = json.loads(self.cipher.decrypt(row['payload']))
                token = record['token']
                if token.get('expires_at', 0) <= time.time() + 30:
                    if not token.get('refresh_token'):
                        session.clear()
                        db.execute('DELETE FROM auth_sessions WHERE id=?', (self.digest(sid),))
                        return None
                    try:
                        fresh = self.post_provider('token_endpoint', {'grant_type': 'refresh_token', 'refresh_token': token['refresh_token']})
                    except requests.HTTPError as exc:
                        if exc.response.status_code in (400, 401):
                            session.clear()
                            db.execute('DELETE FROM auth_sessions WHERE id=?', (self.digest(sid),))
                            return None
                        raise
                    fresh['expires_at'] = int(time.time()) + int(fresh['expires_in'])
                    token.update(fresh)
                user = self.introspect(token['access_token'], record['sub'])
                if user is None:
                    session.clear()
                    db.execute('DELETE FROM auth_sessions WHERE id=?', (self.digest(sid),))
                    return None
                db.execute('UPDATE auth_sessions SET payload=? WHERE id=?', (self.cipher.encrypt(json.dumps(record).encode()), self.digest(sid)))
                g.platform_user = user
                return user
        except InvalidToken:
            session.clear()
            return None
        except (requests.RequestException, ValueError, KeyError, sqlite3.OperationalError):
            abort(503, 'Access could not be verified with central authentication. Please try again.')

    def can(self, permission):
        user = self.current()
        return bool(user and permission in user['permissions'])

    def require(self, *permissions):
        user = self.current()
        if not user:
            if request.method == 'GET':
                return redirect(url_for('platform_auth.login'))
            abort(401, 'Sign in again before submitting this change. Nothing was saved.')
        if not set(permissions).issubset(user['permissions']):
            abort(403, 'Your account does not have permission for this action.')
        return None

    def logout(self):
        sid, record = session.get('sso_sid'), None
        with closing(self.connect()) as db, db:
            if sid:
                row = db.execute('SELECT * FROM auth_sessions WHERE id=?', (self.digest(sid),)).fetchone()
                if row:
                    try:
                        record = json.loads(self.cipher.decrypt(row['payload']))
                    except InvalidToken:
                        pass
                db.execute('DELETE FROM auth_sessions WHERE id=?', (self.digest(sid),))
        session.clear()
        try:
            metadata = self.metadata()
            params = {'client_id': self.client_id, 'post_logout_redirect_uri': self.origin + '/login' if self.flag == 'owner' else self.origin + '/admin/login'}
            if record:
                params['id_token_hint'] = record['token']['id_token']
            return redirect(metadata['end_session_endpoint'] + '?' + urlencode(params))
        except (requests.RequestException, ValueError):
            abort(503, 'You are signed out locally. Central sign-out is temporarily unavailable.')


def init_auth(app, origin, home, flag):
    if app.config['AUTH_MODE'] not in ('legacy', 'oidc'):
        raise RuntimeError('AUTH_MODE must be legacy or oidc.')
    if app.config['AUTH_MODE'] == 'oidc':
        return PlatformAuth(app, origin, home, flag)
    app.context_processor(lambda: {'central_auth': False, 'can': lambda _: True})
    return None
