"""Integration against a real, isolated Keycloak container. No production credentials."""
from contextlib import closing
import html
import importlib.util
import json
from pathlib import Path
import re
import secrets
import shlex
import sys
import threading
import time
from urllib.parse import urlparse, parse_qs

import requests
from werkzeug.serving import make_server, WSGIRequestHandler

ROOT = Path(__file__).resolve().parents[1]


def load_app(name, directory):
    sys.path.insert(0, str(ROOT / directory))
    spec = importlib.util.spec_from_file_location(name, ROOT / directory / 'app.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # Flask resolves templates relative to this module.
    spec.loader.exec_module(module)
    return module.create_app


def settings(path):
    return {line.partition('=')[0]: shlex.split(line.partition('=')[2])[0] for line in path.read_text().splitlines() if '=' in line}


def csrf(response):
    return re.search(r'name="csrf" value="([^"]+)"', response.text)[1]


def signin(browser, origin, username, password):
    response = browser.get(origin + '/auth/login', timeout=15)
    if '/auth' in urlparse(response.url).path and 'kc-form-login' in response.text:
        # Requests lacks browsers' secure-context exception for loopback HTTP.
        # This fixture runs only against the isolated local CI provider.
        for cookie in browser.cookies:
            if cookie.domain in ('127.0.0.1', 'localhost.local'):
                cookie.secure = False
        action = html.unescape(re.search(r'<form[^>]+id="kc-form-login"[^>]+action="([^"]+)"', response.text)[1])
        response = browser.post(action, data={'username': username, 'password': password, 'credentialId': ''}, timeout=20)
    return response


class QuietHandler(WSGIRequestHandler):
    def log_request(self, *args):
        pass


def main():
    generated = Path(sys.argv[1])
    issuer = 'http://127.0.0.1:8098/realms/inflection'
    for _ in range(150):
        try:
            if requests.get(issuer + '/.well-known/openid-configuration', timeout=2).status_code == 200:
                break
        except requests.RequestException:
            pass
        time.sleep(1)
    else:
        raise RuntimeError('Identity provider did not become ready.')
    apps, servers = {}, []
    for name, directory, port in [('time','timekeeper',8101),('admin','feedback',8102)]:
        config = settings(generated / 'secrets' / (name + '-oidc.env'))
        config.update(TESTING=True,SECRET_KEY=secrets.token_urlsafe(48),ADMIN_PASSWORD_HASH='',
            DATABASE_PATH=str(generated / (name + '.sqlite3')),SESSION_COOKIE_SECURE=False,SESSION_COOKIE_NAME='ia-' + name + '-test')
        if name == 'time':
            config['ORIGIN']='http://127.0.0.1:8101'
        else:
            config.update(ADMIN_ORIGIN='http://127.0.0.1:8102',FEEDBACK_ORIGIN='http://localhost:8102',PUBLIC_SITE_ORIGIN='http://localhost:8103')
        apps[name] = load_app('integration_' + name,directory)(config)
        server = make_server('127.0.0.1',port,apps[name],threaded=True,request_handler=QuietHandler)
        threading.Thread(target=server.serve_forever,daemon=True).start()
        servers.append(server)
    try:
        time_origin, admin_origin = 'http://127.0.0.1:8101','http://127.0.0.1:8102'
        owner_password=(generated/'secrets/owner-initial-password').read_text().strip()
        owner=requests.Session()
        start=owner.get(time_origin+'/auth/login',allow_redirects=False,timeout=10)
        params=parse_qs(urlparse(start.headers['Location']).query)
        assert params['code_challenge_method']==['S256'] and params['nonce'] and params['state']
        response=signin(owner,time_origin,'jarom',owner_password)
        assert response.status_code==200 and urlparse(response.url).port==8101, f'Time sign-in failed: HTTP {response.status_code}, path {urlparse(response.url).path}'
        response=owner.get(admin_origin+'/auth/login',timeout=20)
        assert response.status_code==200 and urlparse(response.url).path=='/admin/access', f'Admin SSO failed: HTTP {response.status_code}, path {urlparse(response.url).path}'
        for name in ('time','admin'):
            cookie=owner.cookies.get('ia-'+name+'-test')
            value=apps[name].session_interface.get_signing_serializer(apps[name]).loads(cookie)
            assert 'sso_sid' in value and 'access_token' not in value and 'refresh_token' not in value
        response=owner.post(admin_origin+'/admin/access/users',data={'csrf':csrf(response),'username':'read-only-user','email':'reader@example.test','permissions':['time:read']},timeout=20)
        assert response.status_code==200, f'User creation failed: {response.status_code}'
        password=re.search(r'id="temporary-password"[^>]+value="([^"]+)"',response.text)[1]
        from ia_auth.management import ManagementAPI
        with apps['admin'].app_context():
            api=ManagementAPI(apps['admin'])
            reader=api.call('GET','/users',params={'username':'read-only-user','exact':'true'})[0]
            # CI simulates completed first-login setup. Production always requires password change and MFA.
            api.call('PUT','/users/'+reader['id'],{'requiredActions':[], 'firstName':'Test', 'lastName':'Reader'})
            api.call('PUT','/users/'+reader['id']+'/reset-password',{'type':'password','value':password,'temporary':False})
        reader_browser=requests.Session()
        response=signin(reader_browser,time_origin,'read-only-user',password)
        assert response.status_code==200 and urlparse(response.url).port==8101, f'Reader sign-in failed: HTTP {response.status_code}, path {urlparse(response.url).path}'
        response=reader_browser.post(time_origin+'/clock-in',data={'csrf':csrf(response),'client_id':'unknown'},timeout=15)
        assert response.status_code==403, 'Read-only user could mutate time data.'
        response=reader_browser.get(admin_origin+'/auth/login',timeout=15)
        assert response.status_code==403, 'Time-only user could enter feedback admin.'
        assert reader_browser.get(admin_origin+'/admin/access',timeout=15).status_code==403
        # Force the application to refresh a still-valid token; Keycloak rotates the refresh token.
        auth=apps['time'].extensions['platform_auth']
        cookie=owner.cookies.get('ia-time-test')
        sid=apps['time'].session_interface.get_signing_serializer(apps['time']).loads(cookie)['sso_sid']
        with closing(auth.connect()) as db,db:
            payload=db.execute('SELECT payload FROM auth_sessions WHERE id=?',(auth.digest(sid),)).fetchone()[0]
            record=json.loads(auth.cipher.decrypt(payload));old_refresh=record['token']['refresh_token'];record['token']['expires_at']=0
            db.execute('UPDATE auth_sessions SET payload=? WHERE id=?',(auth.cipher.encrypt(json.dumps(record).encode()),auth.digest(sid)))
        assert owner.get(time_origin+'/',timeout=15).status_code==200
        with closing(auth.connect()) as db:
            row=db.execute('SELECT payload FROM auth_sessions WHERE id=?',(auth.digest(sid),)).fetchone()[0]
            assert json.loads(auth.cipher.decrypt(row))['token']['refresh_token'] != old_refresh
        response=owner.get(admin_origin+'/admin/access/users/'+reader['id'],timeout=15)
        response=owner.post(admin_origin+'/admin/access/users/'+reader['id'],data={'csrf':csrf(response),'enabled':'yes','permissions':['time:read','time:write']},timeout=20)
        assert response.status_code==200
        assert reader_browser.get(time_origin+'/',allow_redirects=False,timeout=15).status_code==302, 'Old session survived permission revocation.'
        owner_sub=apps['admin'].config['OIDC_OWNER_SUB']
        response=owner.get(admin_origin+'/admin/access/users/'+owner_sub,timeout=15)
        assert owner.post(admin_origin+'/admin/access/users/'+owner_sub,data={'csrf':csrf(response)},timeout=15).status_code==403
        assert owner.get(time_origin+'/auth/callback?state=forged&code=forged',timeout=15).status_code==400
        print('PASS: real Keycloak PKCE login, cross-app SSO, encrypted server sessions, read/write enforcement, Admin user creation, token rotation, scope-change revocation, protected owner, and forged callback rejection.')
    finally:
        for server in servers:server.shutdown()


if __name__=='__main__':main()
