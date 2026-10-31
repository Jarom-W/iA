from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest
from unittest.mock import patch

from flask import Flask, session
import requests
from ia_auth import PlatformAuth, init_auth


class AuthenticationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.app = Flask(__name__)
        self.app.config.update(TESTING=True, SECRET_KEY='test-secret-'*4, AUTH_MODE='oidc',
            OIDC_ISSUER='https://auth.example.test/realms/inflection', OIDC_CLIENT_ID='ia-time', OIDC_CLIENT_SECRET='test-client-secret',
            AUTH_DATABASE_PATH='', DATABASE_PATH=str(Path(self.temp.name)/'app.sqlite3'))
        self.auth = PlatformAuth(self.app,'https://time.example.test','/','owner')
        @self.app.get('/private')
        def private():
            denied = self.auth.require('time:read')
            return denied if denied is not None else {'ok':True}
        @self.app.post('/write')
        def write():
            denied = self.auth.require('time:read','time:write')
            return denied if denied is not None else {'ok':True}
        self.client=self.app.test_client()

    def tearDown(self):
        self.temp.cleanup()

    def record(self,expires=None):
        sid='opaque-session-id'
        value={'sub':'owner-sub','token':{'access_token':'private-access-token','refresh_token':'private-refresh-token','id_token':'private-id-token','expires_at':expires or time.time()+300}}
        with closing(self.auth.connect()) as db,db:
            db.execute('INSERT INTO auth_sessions VALUES(?,?,?)',(self.auth.digest(sid),self.auth.cipher.encrypt(json.dumps(value).encode()),time.time()+3600))
        with self.client.session_transaction(base_url='https://time.example.test') as s:
            s.update(sso_sid=sid,owner=True,csrf='csrf')
        return sid

    def user(self,permissions=('time:read',)):
        return {'sub':'owner-sub','username':'jarom','permissions':list(permissions)}

    def test_legacy_cookie_cannot_bypass_oidc(self):
        with self.client.session_transaction(base_url='https://time.example.test') as s:s['owner']=True
        self.assertEqual(self.client.get('/private',base_url='https://time.example.test').status_code,302)
        self.assertEqual(self.client.post('/write',base_url='https://time.example.test').status_code,401)

    def test_permission_enforced_server_side(self):
        self.record()
        with patch.object(self.auth,'introspect',return_value=self.user()):
            self.assertEqual(self.client.get('/private',base_url='https://time.example.test').status_code,200)
            self.assertEqual(self.client.post('/write',base_url='https://time.example.test').status_code,403)
        with patch.object(self.auth,'introspect',return_value=self.user(('time:read','time:write'))):
            self.assertEqual(self.client.post('/write',base_url='https://time.example.test').status_code,200)

    def test_tokens_encrypted_at_rest_and_not_in_cookie(self):
        self.record()
        raw=self.auth.database.read_bytes()
        self.assertNotIn(b'private-access-token',raw)
        self.assertNotIn(b'private-refresh-token',raw)
        with self.client.session_transaction(base_url='https://time.example.test') as s:
            self.assertNotIn('token',s)
            self.assertNotIn('private-access-token',str(s))

    def test_revoked_session_is_rejected(self):
        self.record()
        with patch.object(self.auth,'introspect',return_value=None):
            self.assertEqual(self.client.get('/private',base_url='https://time.example.test').status_code,302)
        with closing(self.auth.connect()) as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM auth_sessions').fetchone()[0],0)

    def test_provider_outage_fails_closed_without_erasing_session(self):
        self.record()
        with patch.object(self.auth,'introspect',side_effect=requests.ConnectionError()):
            self.assertEqual(self.client.get('/private',base_url='https://time.example.test').status_code,503)
        with closing(self.auth.connect()) as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM auth_sessions').fetchone()[0],1)

    def test_refresh_uses_same_subject_and_rotates_token(self):
        self.record(expires=time.time()-10)
        with patch.object(self.auth,'post_provider',return_value={'access_token':'new-access','refresh_token':'new-refresh','expires_in':300}) as refresh, patch.object(self.auth,'introspect',return_value=self.user()) as check:
            self.assertEqual(self.client.get('/private',base_url='https://time.example.test').status_code,200)
            check.assert_called_once_with('new-access','owner-sub')
            self.assertEqual(refresh.call_args.args[1]['grant_type'],'refresh_token')
        with closing(self.auth.connect()) as db:
            row=db.execute('SELECT payload FROM auth_sessions').fetchone()[0]
            self.assertEqual(json.loads(self.auth.cipher.decrypt(row))['token']['refresh_token'],'new-refresh')

    def test_introspection_rejects_substitution(self):
        for overrides in [{'sub':'another-user'},{'client_id':'another-client'},{'iss':'https://evil.test'},{'permissions':'time:read'}]:
            info=dict(active=True,sub='owner-sub',client_id='ia-time',iss=self.auth.issuer,permissions=['time:read']);info.update(overrides)
            with patch.object(self.auth,'post_provider',return_value=info),self.assertRaises(ValueError):self.auth.introspect('token','owner-sub')

    def test_callback_without_state_or_nonce_does_not_sign_in(self):
        with patch.object(self.auth,'metadata',return_value={}):
            result=self.client.get('/auth/callback?code=forged&state=forged',base_url='https://time.example.test')
        self.assertEqual(result.status_code,400)
        with self.client.session_transaction(base_url='https://time.example.test') as s:self.assertNotIn('sso_sid',s)

    def test_signed_identity_claims_and_signature_validation(self):
        from joserfc import jwt
        from joserfc.jwk import RSAKey
        from joserfc.errors import JoseError
        key = RSAKey.generate_key(2048, parameters={'kid':'test-key'})
        other = RSAKey.generate_key(2048, parameters={'kid':'test-key'})
        now = int(time.time())
        claims = dict(iss=self.auth.issuer, sub='owner-sub', aud='ia-time',
                      exp=now+300, iat=now, nonce='expected-nonce')
        metadata = {'issuer':self.auth.issuer, 'id_token_signing_alg_values_supported':['RS256']}
        def parse(values, signing_key=key):
            token = jwt.encode({'alg':'RS256', 'kid':'test-key'}, values, signing_key)
            return self.auth.remote.parse_id_token({'id_token':token, 'access_token':'access'}, nonce='expected-nonce', leeway=0)
        with self.app.test_request_context(), patch.object(self.auth.remote,'load_server_metadata',return_value=metadata), patch.object(self.auth.remote,'fetch_jwk_set',return_value={'keys':[key.as_dict(private=False)]}):
            self.assertEqual(parse(claims)['sub'],'owner-sub')
            for change in [{'iss':'https://attacker.test'}, {'aud':'other-client'}, {'nonce':'wrong'}, {'nonce':None}, {'exp':now-30}]:
                with self.subTest(change=change), self.assertRaises(JoseError):
                    parse(dict(claims, **change))
            with self.assertRaises(JoseError):
                parse(claims, other)

    def test_auth_routes_host_and_csrf(self):
        self.assertEqual(self.client.get('/auth/login',base_url='https://other.example.test').status_code,404)
        self.assertEqual(self.client.post('/auth/logout',base_url='https://time.example.test').status_code,403)

    def test_misconfigured_oidc_does_not_enable_local_login(self):
        self.app.config['OIDC_CLIENT_SECRET']=''
        with self.assertRaises(RuntimeError):PlatformAuth(self.app,'https://time.example.test','/','owner')


if __name__=='__main__':unittest.main()
