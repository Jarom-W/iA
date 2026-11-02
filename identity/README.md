# Central platform authentication

Keycloak owns passwords, MFA, sessions and signing keys. Time and Admin use OpenID Connect Authorization Code with S256 PKCE through the shared `platform_auth` package. Authlib validates signed identity tokens, issuer, audience, nonce and state. Tokens remain encrypted in each application's server-side SQLite session store; browser cookies contain opaque session references. Each protected request checks token activity with Keycloak, so revocation and disabled accounts take effect without waiting for token expiry. Provider outages deny access rather than bypass permissions.

The public login matches the site's black/green styling. The owner manages accounts at `https://admin.inflectionarchitectures.com/admin/access`, with temporary passwords, first-login password changes/MFA, permission checkboxes, session revocation and an audit trail. `platform:manage` grants account administration. Other permissions cover Feedback read/write and Time read/write/document download/upload. These are application-wide privileges: **Time read access exposes all customers and work logs**, not a customer portal. A fixed catalog keeps grants aligned with permissions actually enforced by code; adding a new scope requires implementing its enforcement.

Vault is deliberately disabled until its actual service and OIDC callback are known. Assigning `vault:access` alone does not protect or integrate an existing Vault installation.

## First installation

Use a host account authorized to run Docker Compose. Do not expose the Docker socket to applications. Keep the checkout and generated configuration private.

```sh
cd identity
python3 configure.py
docker compose up -d --build
docker compose ps
```

The generator refuses to overwrite existing secrets. It creates private `.env` and `secrets/` files, client secrets, a protected owner ID, an initial owner password, and a Keycloak realm import. Never commit these. The realm import only bootstraps an absent realm; restarting containers does not overwrite live accounts or permissions. Do not rerun the generator to update an existing deployment.

Add a Cloudflare Tunnel published application route:

| Hostname | Service | Host override |
| --- | --- | --- |
| auth.inflectionarchitectures.com | http://localhost:8097 | unset |

Leave existing Time/Admin/Feedback routes intact. The gateway exposes only the Inflection realm and static assets. It fixes forwarding headers to the expected public HTTPS origin and blocks Keycloak's management endpoints and master realm. **Never publish port 8098 through Cloudflare**; it is loopback-only for the Admin application's management API. Do not cache auth, Admin or Time responses. The PostgreSQL database has no host port.

Verify the public discovery URL returns the exact HTTPS issuer:

`https://auth.inflectionarchitectures.com/realms/inflection/.well-known/openid-configuration`

Before changing either application's login, open `https://auth.inflectionarchitectures.com/realms/inflection/account/`, sign in as `jarom` using the generated `secrets/owner-initial-password`, change the password and enroll an authenticator. Open the password file privately on the server; never paste it into a ticket, chat or command argument. Keep the existing owner credentials and service environment backups for rollback.

## Activate Time and Admin

Install the shared Python package and each service's requirements into its own virtual environment. Example from the repository root:

```sh
~/services/ia-time/.venv/bin/pip install ./platform_auth -r timekeeper/requirements.txt
~/services/ia-feedback/.venv/bin/pip install ./platform_auth -r feedback/requirements.txt
```

Deploy the matching application files without replacing `.env`, `.venv`, `data` or backups. Keep each existing application session secret. Configure the generated variables using private systemd environment drop-ins (copy secrets locally, never through logs):

```sh
mkdir -p ~/.config/systemd/user/ia-time.service.d ~/.config/systemd/user/ia-feedback.service.d
```

Create `~/.config/systemd/user/ia-time.service.d/auth.conf`:

```ini
[Service]
EnvironmentFile=/absolute/path/to/iA/identity/secrets/time-oidc.env
```

Create `~/.config/systemd/user/ia-feedback.service.d/auth.conf`:

```ini
[Service]
EnvironmentFile=/absolute/path/to/iA/identity/secrets/admin-oidc.env
```

Replace the absolute paths with the installed location. For Docker applications, add these generated files to each service's `env_file`; the Admin management URL must be reachable from that container, for example `http://keycloak:8080` on a shared private network. Loopback in a container is not the Docker host.

Activate Time first, confirm owner login and logout, then activate Admin:

```sh
systemctl --user daemon-reload
systemctl --user restart ia-time.service
# Verify Time login before continuing.
systemctl --user restart ia-feedback.service
```

In OIDC mode local password login is disabled, not retained as an alternate entry point. Existing legacy cookies do not grant OIDC access. Check owner access to Time and `/admin/access`, use a separate browser for a limited account, and verify excluded operations return 403. Protect the generated owner account: the Admin portal refuses to disable, reset or alter its grants. Owner recovery uses the private Keycloak administrative path, not a public backdoor.

For rollback, remove only the added `auth.conf` drop-ins, reload systemd and restart affected services; the original private `.env` owner credentials remain available. Rollback intentionally restores the old single-owner authentication model and should be performed locally by the server owner.

## Backup and recovery

Back up PostgreSQL regularly, along with private client configuration and the application databases. From `identity/`:

```sh
umask 077
mkdir -p backups
docker compose exec -T postgres pg_dump -U keycloak -d keycloak -Fc > "backups/keycloak-$(date -u +%Y%m%dT%H%M%SZ).dump"
```

Copy backups to encrypted off-server storage. Test `pg_restore` into a separate database before relying on a backup. Never use `docker compose down -v` during routine maintenance: it deletes the identity database. The initial realm JSON is not a backup of live accounts, password changes, MFA credentials or signing keys.

Application auth-session databases contain encrypted tokens and are disposable. After recovery, stop the affected app, preserve and remove its separate `*.auth.sqlite3` database, then restart so users sign in again. Do not delete the business database. The Admin access audit table lives in the feedback database and is covered by its normal backup.

Use a local SSH port-forward for emergency Keycloak management; no public management route is configured. The bootstrap account is temporary recovery setup: replace it with a protected permanent administrative account according to Keycloak's administration guidance and remove bootstrap credentials from runtime configuration after verification. Keep recovery credentials offline.

## Validation and deployment status

CI builds the production image and runs an isolated real Keycloak integration: PKCE login, Time-to-Admin SSO, encrypted session storage, read-only enforcement, account creation, rotating refresh tokens, permission-change revocation, protected owner checks and forged callback rejection. Local unit tests cover fail-closed behavior and token/session validation. CI's HTTP loopback provider is test-only; production requires HTTPS.

The existing server account cannot currently run Docker, and the Auth Cloudflare route is not yet configured. Deploying application code alone does not activate SSO. Existing Time and Feedback owner logins remain enabled until the provider and owner MFA are verified and the OIDC environment files are installed. Vault integration still requires its service details.

## Updating the login theme

The `ia` login theme inherits Keycloak's authentication forms and applies the site's logo, black surfaces, green controls, typography and responsive layout. Password, authenticator and account-setup flows retain their native behavior. The image explicitly sets theme ownership and readability: private checkout permissions otherwise cause Keycloak to fall back to its default theme.

After updating the checkout, rebuild the identity container from `identity/`:

```sh
sudo docker compose up -d --build keycloak
```

This preserves PostgreSQL accounts and settings. The live realm must have `loginTheme=ia`; the initial import already configures it. Verify a fresh sign-in page includes `/login/ia/` resources and `css/ia.css`. An existing SSO session can skip the login screen; use a private browser window to inspect it.
