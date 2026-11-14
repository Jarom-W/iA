# iA Product Surveys

Product research at `https://survey.inflectionarchitectures.com`. This is separate from the client testimonial/feedback app. Administration uses the existing iA Auth account; published surveys are public and require no sign-in.

## Using it

1. Sign in and select **Create survey**.
2. Add a title, introduction, and questions. **Color preferences** supplies editable color swatches. Choose-one, choose-several, 1–5 ratings, and written answers are supported.
3. Upload an optional product photo per question and describe it for accessibility. JPEG, PNG, and WebP are accepted up to 8 MB / 20 megapixels. Photos are resized and re-encoded without EXIF/GPS metadata.
4. **Save draft**, preview the saved survey, and return to **Survey overview** to publish.
5. Copy its public link, download a PNG/SVG QR code, or print the QR for your table. Test a scan before printing in quantity.
6. Open the overview for response counts, answer percentages, rating averages, written responses, daily totals, and a CSV export. Refresh to see new submissions.
7. Close/reopen collection using the same link. Published questions/photos are immutable so earlier answers retain their meaning. **Duplicate** creates an editable draft with copied photos, a new link, and no responses.

Limits: 20 questions, 20 choices per question, 40 uploaded photos per survey, 2,000 characters per written answer. Anonymous submissions are not verified unique people; percentages for choose-several questions can exceed 100%. QR scans/page visits are not tracked. Responses are stored until the operator removes them from storage; there is no automatic retention policy or deletion UI in this initial version. Avoid asking for sensitive personal information.

## Authentication and permissions

Confidential OIDC authorization-code flow with S256 PKCE through `platform_auth`. No separate survey password, password grant, or browser-stored tokens. Sessions use encrypted server-side token storage, host-only Secure/HttpOnly cookies, CSRF protection, and live token introspection.

- `survey:read`: view all surveys, previews, photos, results, QR codes, and CSV exports.
- `survey:write`: create/edit drafts, upload photos, publish/close, and duplicate; requires `survey:read`.

These appear in the existing admin access manager after installing the updated shared package. The owner receives both during provisioning. They apply to the whole survey workspace, not individual surveys. Public forms have signed expiring submission tickets, duplicate-submit protection, a honeypot, and cookie-based/global submission throttling. This reduces accidental duplicates and simple abuse, but does not establish respondent identity.

## Existing-server setup

Do not reimport the realm or run initial realm setup over existing accounts. `identity/provision-survey.py` adds only the survey client, its role mappings, and owner grants. It reads existing private bootstrap credentials via loopback and writes an app environment file without printing secrets. It is safe to rerun and preserves the survey signing key. If bootstrap administration has been disabled, an authorized Keycloak administrator must create the equivalent client manually; do not enable public access to the management port.

From the repository root:

```bash
bash survey/install-native.sh
```

The installer also updates `platform_auth` in the native admin/feedback virtualenv and restarts that service to expose the permission descriptions. It preserves existing survey data and environment keys on subsequent deployments. The new OIDC client is `ia-survey`, with exactly `https://survey.inflectionarchitectures.com/auth/callback` as its redirect URI, `https://survey.inflectionarchitectures.com/login` as post-logout URI, S256 PKCE required, implicit/direct grants disabled, and only the survey roles in its scope mapping. `platform-permissions` must be a default client scope and the audience mapper must include `ia-survey`.

In the existing Cloudflare Tunnel, add a published application route:

- Hostname: `survey.inflectionarchitectures.com`
- Service type: HTTP
- URL: `localhost:8096`

Use the same host connector as Time/Admin. Do not add an Access login wall to the entire hostname: customers need to reach `/s/...` anonymously. The application's `/admin` routes enforce iA authentication. Only loopback port 8096 should be exposed by the process.

Verify `curl http://127.0.0.1:8096/health`, then visit the public hostname and complete iA sign-in. An active iA session may sign you in without another password prompt. New permission grants may require signing in again to obtain a token containing them.

## Containers / fresh installations

`docker compose --project-directory survey -f survey/compose.yaml up -d --build` uses `survey/.env` (copy the example and supply real secrets), a named data volume, and loopback port 8096. It runs as a non-root user with a read-only root filesystem. The root CI builds and health-checks this container and exercises actual Survey SSO against a disposable Keycloak realm.

For a brand-new realm, `identity/configure.py` includes the survey client and generates `survey-oidc.env`. Supply those values plus a random `SURVEY_SECRET_KEY` of at least 32 characters and `SURVEY_DATABASE_PATH`.

## Data and backups

The SQLite database contains survey definitions, normalized photos, and responses. The auth database is separate and contains encrypted short-lived sessions. Keep the environment/signing key private and stable across deployments. Never commit databases, responses, uploads, or `.env` files.

The native backup timer makes a verified online SQLite snapshot daily and retains the latest 14. Copy snapshots to encrypted off-server storage as well. To restore: stop `ia-survey`, preserve the existing database and its WAL/SHM files, restore a verified snapshot at `SURVEY_DATABASE_PATH`, remove obsolete WAL/SHM sidecars while stopped, set owner-only permissions, and restart. Container operators must schedule `backup.py` with the same data volume themselves. Auth sessions can be discarded on recovery; users sign in again.

## Tests

```bash
PYTHONPATH=survey:platform_auth python -m unittest discover -s survey/tests -v
python -m unittest discover -s platform_auth/tests -v
```

The tests cover permissions, CSRF, publication locking, stale edits, photo isolation/re-encoding, response validation, duplicate prevention, closing/reopening, analytics, QR targets, CSV formula escaping, and throttling. The identity integration suite additionally checks real SSO and denial for a Time-only account.
