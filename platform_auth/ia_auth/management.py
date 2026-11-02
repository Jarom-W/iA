"""Owner-authorized access administration backed by Keycloak's Admin REST API."""
from contextlib import closing
import json
import os
import re
import secrets
import sqlite3
import time
from urllib.parse import quote, urlsplit

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for
import requests
from . import PERMISSIONS


class ManagementAPI:
    def __init__(self, app):
        self.app = app
        self.base = app.config['OIDC_MANAGEMENT_BASE_URL'].rstrip('/')
        parsed = urlsplit(self.base)
        if not parsed.hostname or parsed.path or parsed.query or parsed.fragment or parsed.username:
            raise ValueError('Invalid management API origin.')
        if parsed.scheme != 'https' and not (parsed.scheme == 'http' and (parsed.hostname in ('127.0.0.1', 'localhost', 'keycloak') or app.testing)):
            raise ValueError('Management API must use HTTPS or a private configured local endpoint.')
        self.realm = app.config['OIDC_REALM']
        self.root = self.base + '/admin/realms/' + quote(self.realm, safe='')
        response = requests.post(self.base + '/realms/' + quote(self.realm, safe='') + '/protocol/openid-connect/token',
            data={'grant_type': 'client_credentials'}, auth=(app.config['OIDC_MANAGEMENT_CLIENT_ID'], app.config['OIDC_MANAGEMENT_CLIENT_SECRET']), timeout=8, allow_redirects=False)
        response.raise_for_status()
        self.token = response.json()['access_token']

    def call(self, method, path, body=None, params=None):
        response = requests.request(method, self.root + path, json=body, params=params,
            headers={'Authorization': 'Bearer ' + self.token}, timeout=8, allow_redirects=False)
        response.raise_for_status()
        if response.status_code == 201:
            return response.headers['Location'].rsplit('/', 1)[1]
        return response.json() if response.content else None

    def catalog(self):
        return [role for role in self.call('GET', '/roles') if role['name'] in PERMISSIONS]


def register_management(app):
    for key, default in dict(OIDC_MANAGEMENT_BASE_URL='https://auth.inflectionarchitectures.com',
        OIDC_REALM='inflection', OIDC_MANAGEMENT_CLIENT_ID='ia-access-admin', OIDC_MANAGEMENT_CLIENT_SECRET='', OIDC_OWNER_SUB='').items():
        app.config.setdefault(key, os.getenv(key, default))
    bp = Blueprint('access', __name__, url_prefix='/admin/access', template_folder='templates')

    @bp.before_request
    def protect():
        auth = app.extensions.get('platform_auth')
        if not auth:
            abort(404)
        denied = auth.require('platform:manage')
        if denied is not None:
            return denied
        if not app.config['OIDC_MANAGEMENT_CLIENT_SECRET'] or not app.config['OIDC_OWNER_SUB']:
            abort(503, 'Platform access administration has not been configured.')

    def api():
        if not hasattr(g, 'management_api'):
            g.management_api = ManagementAPI(app)
        return g.management_api

    def audit(action, target, permissions=(), outcome='success'):
        with closing(sqlite3.connect(app.config['DATABASE_PATH'])) as db, db:
            db.execute('CREATE TABLE IF NOT EXISTS platform_audit (at INTEGER, actor TEXT, action TEXT, target TEXT, permissions TEXT, outcome TEXT)')
            db.execute('INSERT INTO platform_audit VALUES(?,?,?,?,?,?)', (int(time.time()), g.platform_user['sub'], action, target, json.dumps(sorted(permissions)), outcome))

    def selected():
        roles = set(request.form.getlist('permissions'))
        if roles - PERMISSIONS.keys():
            abort(400, 'Unknown application permission.')
        dependencies = {'time:write': {'time:read'}, 'time:documents:read': {'time:read'},
            'time:documents:write': {'time:read', 'time:write'}, 'feedback:write': {'feedback:read'}}
        if any(role in roles and not required.issubset(roles) for role, required in dependencies.items()):
            abort(400, 'Write permissions need their application read permission. Document uploads also need Time write access.')
        return roles

    def protected_user(user_id):
        if not re.fullmatch('[A-Za-z0-9-]{1,80}', user_id):
            abort(404)
        if user_id == app.config['OIDC_OWNER_SUB']:
            abort(403, 'The platform owner cannot be disabled or have permissions changed here. Use the identity-provider recovery procedure for owner changes.')
        user = api().call('GET', '/users/' + user_id)
        if user.get('serviceAccountClientId') or user.get('username', '').startswith('service-account-'):
            abort(403, 'Service accounts cannot be changed through this page.')
        return user

    def set_permissions(user_id, wanted):
        roles = api().catalog()
        by_name = {role['name']: role for role in roles}
        if not wanted.issubset(by_name):
            abort(503, 'The identity provider is missing a configured application permission.')
        path = '/users/' + user_id + '/role-mappings/realm'
        existing = api().call('GET', path)
        # Only manage this platform's own roles, never realm/system roles.
        remove = [role for role in existing if role['name'] in PERMISSIONS and role['name'] not in wanted]
        if remove:
            api().call('DELETE', path, remove)
        if wanted:
            api().call('POST', path, [by_name[name] for name in sorted(wanted)])

    @bp.get('')
    def index():
        query = request.args.get('q', '').strip()[:100]
        try:
            page = max(0, min(1000, int(request.args.get('page', 0))))
        except ValueError:
            abort(400)
        users = api().call('GET', '/users', params={'search': query, 'first': page * 25, 'max': 25})
        with closing(sqlite3.connect(app.config['DATABASE_PATH'])) as db:
            db.row_factory = sqlite3.Row
            db.execute('CREATE TABLE IF NOT EXISTS platform_audit (at INTEGER, actor TEXT, action TEXT, target TEXT, permissions TEXT, outcome TEXT)')
            events = db.execute('SELECT * FROM platform_audit ORDER BY at DESC LIMIT 30').fetchall()
        return render_template('access/index.html', users=users, permissions=PERMISSIONS, owner_sub=app.config['OIDC_OWNER_SUB'], query=query, page=page, events=events, title='Platform access')

    @bp.post('/users')
    def create_user():
        username, email = request.form.get('username', '').strip(), request.form.get('email', '').strip()
        if not re.fullmatch('[A-Za-z0-9_.@-]{3,80}', username) or len(email) > 254 or (email and not re.fullmatch(r'[^\s<>@]+@[^\s<>@]+\.[^\s<>@]+', email)):
            abort(400, 'Enter a valid username and optional email.')
        wanted = selected()
        password = secrets.token_urlsafe(24) + 'Aa1!'
        audit('create-user', username, wanted, 'started')
        user_id = api().call('POST', '/users', {'username': username, 'email': email or None, 'enabled': False,
            'requiredActions': ['UPDATE_PASSWORD', 'CONFIGURE_TOTP'],
            'credentials': [{'type': 'password', 'value': password, 'temporary': True}]})
        set_permissions(user_id, wanted)
        api().call('PUT', '/users/' + user_id, {'enabled': True})
        audit('create-user', user_id, wanted)
        return render_template('access/credential.html', username=username, password=password, title='Account created')

    @bp.get('/users/<user_id>')
    def user_detail(user_id):
        if not re.fullmatch('[A-Za-z0-9-]{1,80}', user_id):
            abort(404)
        user = api().call('GET', '/users/' + user_id)
        roles = api().call('GET', '/users/' + user_id + '/role-mappings/realm/composite')
        return render_template('access/user.html', user=user, permissions=PERMISSIONS, assigned={r['name'] for r in roles}, protected=user_id == app.config['OIDC_OWNER_SUB'], title='User access')

    @bp.post('/users/<user_id>')
    def update_user(user_id):
        protected_user(user_id)
        wanted = selected()
        enabled = request.form.get('enabled') == 'yes'
        audit('update-access', user_id, wanted, 'started')
        # Fail closed during a partial API failure. Revoke sessions before changing grants.
        api().call('PUT', '/users/' + user_id, {'enabled': False})
        api().call('POST', '/users/' + user_id + '/logout')
        set_permissions(user_id, wanted)
        api().call('PUT', '/users/' + user_id, {'enabled': enabled})
        audit('update-access', user_id, wanted)
        flash('Access updated. Existing sessions were revoked; the user must sign in again.', 'success')
        return redirect(url_for('access.user_detail', user_id=user_id))

    @bp.post('/users/<user_id>/revoke')
    def revoke(user_id):
        protected_user(user_id)
        api().call('POST', '/users/' + user_id + '/logout')
        audit('revoke-sessions', user_id)
        flash('User sessions revoked.', 'success')
        return redirect(url_for('access.user_detail', user_id=user_id))

    @bp.post('/users/<user_id>/reset')
    def reset_password(user_id):
        user = protected_user(user_id)
        audit('reset-password', user_id, outcome='started')
        password = secrets.token_urlsafe(24) + 'Aa1!'
        api().call('POST', '/users/' + user_id + '/logout')
        api().call('PUT', '/users/' + user_id + '/reset-password', {'type': 'password', 'value': password, 'temporary': True})
        audit('reset-password', user_id)
        return render_template('access/credential.html', username=user['username'], password=password, title='Temporary password')

    @bp.errorhandler(requests.RequestException)
    @bp.errorhandler(ValueError)
    @bp.errorhandler(KeyError)
    def unavailable(_error):
        # Never display provider response bodies, tokens, or password material.
        return render_template('message.html', title='Access administration unavailable',
            message='The identity provider did not complete this request. Check the user before retrying; an interrupted access change leaves the account disabled.'), 503

    app.register_blueprint(bp)
