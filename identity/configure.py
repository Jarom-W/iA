"""Generate private first-install configuration; never print credentials."""
import argparse
import json
import os
from pathlib import Path
import secrets
import uuid

PERMISSIONS = ['platform:manage', 'feedback:read', 'feedback:write', 'time:read', 'time:write',
               'time:documents:read', 'time:documents:write', 'vault:access']


def realm_config(origin, app_origins, owner_id, owner_password, client_secrets, testing=False):
    def client(name, redirect, roles):
        return {'clientId': name, 'enabled': True, 'protocol': 'openid-connect', 'publicClient': False,
            'secret': client_secrets[name], 'standardFlowEnabled': True, 'implicitFlowEnabled': False,
            'directAccessGrantsEnabled': False, 'serviceAccountsEnabled': False, 'fullScopeAllowed': False,
            'redirectUris': [redirect + '/auth/callback'], 'webOrigins': [], 'defaultClientScopes': ['platform-permissions'],
            'protocolMappers': [{'name':'application-audience', 'protocol':'openid-connect', 'protocolMapper':'oidc-audience-mapper',
                'config': {'included.client.audience':name, 'access.token.claim':'true', 'id.token.claim':'false', 'introspection.token.claim':'true'}}],
            'attributes': {'pkce.code.challenge.method': 'S256', 'post.logout.redirect.uris': redirect + ('/admin/login' if name == 'ia-admin' else '/login')}}
    clients = [client('ia-time', app_origins['time'], []), client('ia-admin', app_origins['admin'], [])]
    # Vault remains disabled until its actual implementation and exact callback are known.
    clients.append({'clientId': 'ia-vault', 'enabled': False, 'protocol': 'openid-connect', 'publicClient': False,
        'secret': client_secrets['ia-vault'], 'standardFlowEnabled': True, 'implicitFlowEnabled': False,
        'directAccessGrantsEnabled': False, 'fullScopeAllowed': False, 'redirectUris': [],
        'attributes': {'pkce.code.challenge.method': 'S256'}, 'defaultClientScopes': ['platform-permissions']})
    clients.append({'clientId': 'ia-access-admin', 'enabled': True, 'protocol': 'openid-connect', 'publicClient': False,
        'secret': client_secrets['ia-access-admin'], 'standardFlowEnabled': False, 'directAccessGrantsEnabled': False,
        'serviceAccountsEnabled': True, 'fullScopeAllowed': True, 'defaultClientScopes': [],
        'protocolMappers': [{'name': 'management-roles', 'protocol': 'openid-connect', 'protocolMapper': 'oidc-usermodel-client-role-mapper',
            'config': {'usermodel.clientRoleMapping.clientId': 'realm-management', 'claim.name': 'resource_access.realm-management.roles',
                'multivalued': 'true', 'jsonType.label': 'String', 'access.token.claim': 'true'}}]})
    claims = {'access.token.claim': 'true', 'id.token.claim': 'true', 'userinfo.token.claim': 'true', 'introspection.token.claim': 'true', 'jsonType.label': 'String'}
    return {'realm': 'inflection', 'enabled': True, 'displayName': 'Inflection Architectures', 'sslRequired': 'none' if testing else 'external',
        'registrationAllowed': False, 'resetPasswordAllowed': False, 'rememberMe': True, 'loginWithEmailAllowed': False,
        'bruteForceProtected': True, 'failureFactor': 5, 'waitIncrementSeconds': 60, 'maxFailureWaitSeconds': 900,
        'accessTokenLifespan': 300, 'ssoSessionIdleTimeout': 3600, 'ssoSessionMaxLifespan': 43200, 'accessCodeLifespan': 60,
        'revokeRefreshToken': True, 'refreshTokenMaxReuse': 0, 'defaultSignatureAlgorithm': 'RS256',
        'passwordPolicy': 'length(16) and notUsername(undefined)', 'loginTheme': 'ia',
        'eventsEnabled': True, 'eventsExpiration': 2592000, 'adminEventsEnabled': True, 'adminEventsDetailsEnabled': False,
        'roles': {'realm': [{'name': name, 'description': name} for name in PERMISSIONS]},
        'clientScopes': [{'name': 'platform-permissions', 'protocol': 'openid-connect', 'attributes': {'include.in.token.scope': 'true'},
            'protocolMappers': [
                {'name':'subject', 'protocol':'openid-connect', 'protocolMapper':'oidc-sub-mapper',
                 'config': {'access.token.claim':'true', 'introspection.token.claim':'true'}},
                {'name': 'permissions', 'protocol': 'openid-connect', 'protocolMapper': 'oidc-usermodel-realm-role-mapper',
                 'config': dict(claims, **{'claim.name': 'permissions', 'multivalued': 'true'})},
                {'name': 'username', 'protocol': 'openid-connect', 'protocolMapper': 'oidc-usermodel-property-mapper',
                 'config': dict(claims, **{'claim.name': 'preferred_username', 'user.attribute': 'username'})}]}],
        'clients': clients,
        'scopeMappings': [{'client': 'ia-time', 'roles': [x for x in PERMISSIONS if x.startswith('time:')]},
            {'client': 'ia-admin', 'roles': [x for x in PERMISSIONS if x.startswith(('platform:', 'feedback:'))]},
            {'client': 'ia-vault', 'roles': ['vault:access']}],
        'users': [{'id': owner_id, 'username': 'jarom', 'enabled': True, 'realmRoles': PERMISSIONS,
            **({'firstName': 'Test', 'lastName': 'Owner', 'email': 'owner@example.test'} if testing else {}),
            'credentials': [{'type': 'password', 'value': owner_password, 'temporary': not testing}],
            'requiredActions': [] if testing else ['UPDATE_PASSWORD', 'CONFIGURE_TOTP']},
            {'username': 'service-account-ia-access-admin', 'serviceAccountClientId': 'ia-access-admin', 'enabled': True,
             'clientRoles': {'realm-management': ['manage-users', 'query-users', 'view-users', 'view-realm']}}]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--test', action='store_true', help='Isolated CI fixtures only; never production')
    args = parser.parse_args()
    root = args.directory.resolve()
    if (root / '.env').exists() or (root / 'secrets').exists():
        raise SystemExit('Configuration already exists. Refusing to overwrite identity secrets.')
    os.umask(0o077)
    root.mkdir(parents=True, exist_ok=True)
    (root / 'secrets').mkdir(mode=0o700)
    owner_id = str(uuid.uuid4())
    password = secrets.token_urlsafe(32) + 'Aa1!'
    client_secrets = {name: secrets.token_urlsafe(48) for name in ['ia-time', 'ia-admin', 'ia-vault', 'ia-access-admin']}
    origin = 'http://127.0.0.1:8098' if args.test else 'https://auth.inflectionarchitectures.com'
    apps = {'time': 'http://127.0.0.1:8101', 'admin': 'http://127.0.0.1:8102'} if args.test else {'time': 'https://time.inflectionarchitectures.com', 'admin': 'https://admin.inflectionarchitectures.com'}
    realm = realm_config(origin, apps, owner_id, password, client_secrets, testing=args.test)
    (root / 'secrets/realm.json').write_text(json.dumps(realm, indent=2))
    # Keycloak is non-root in Docker. The parent directory remains owner-only;
    # only the import file itself is mounted into the container.
    (root / 'secrets/realm.json').chmod(0o444)
    def env(path, values):
        path.write_text(''.join(f"{key}='{value}'\n" for key, value in values.items()))
    env(root / '.env', {'POSTGRES_PASSWORD': secrets.token_urlsafe(48), 'KC_BOOTSTRAP_ADMIN_USERNAME': 'bootstrap-owner', 'KC_BOOTSTRAP_ADMIN_PASSWORD': secrets.token_urlsafe(40) + 'Aa1!'})
    (root / 'secrets/owner-initial-password').write_text(password + '\n')
    for app_name in ('time', 'admin'):
        values = {'AUTH_MODE': 'oidc', 'OIDC_ISSUER': origin + '/realms/inflection', 'OIDC_CLIENT_ID': 'ia-' + app_name,
            'OIDC_CLIENT_SECRET': client_secrets['ia-' + app_name]}
        if app_name == 'admin':
            values.update(OIDC_MANAGEMENT_BASE_URL='http://127.0.0.1:8098', OIDC_REALM='inflection',
                OIDC_MANAGEMENT_CLIENT_ID='ia-access-admin', OIDC_MANAGEMENT_CLIENT_SECRET=client_secrets['ia-access-admin'], OIDC_OWNER_SUB=owner_id)
        env(root / 'secrets' / (app_name + '-oidc.env'), values)
    print('Private identity configuration generated. Passwords and client secrets were not printed.')


if __name__ == '__main__':
    main()
