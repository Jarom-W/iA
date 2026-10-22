# Client feedback service

The marketing site stays on GitHub Pages. This Docker service hosts both `feedback.inflectionarchitectures.com` (client forms and the public testimonial feed) and `admin.inflectionarchitectures.com` (single-owner login and password-protected form creation, invitation sending, and response management). Route both hosts to the same service while preserving the original Host header. Admin routes are rejected on the feedback hostname.

## What is implemented

- Create reusable forms with a title, introduction, service label, and up to eight private free-text questions.
- Every form includes a testimonial, name, optional role/company, and optional explicit publication consent.
- Every consented submission enters the approval queue. There is no automatic publication option, including for older forms. Feedback without consent remains private.
- Email invitations using authenticated SMTP with TLS. Links expire after 30 days and accept one response. Revoke unused links from admin.
- Public feed includes only approved, consented testimonials. No client emails or private answers are exposed.
- Publish or hide consented testimonials from admin. Original client wording is preserved; editing client quotes is not supported.
- Homepage displays up to 12 published testimonials, newest first. Empty/unavailable feeds hide the section without disrupting the site. Changes appear on the next page load.

## Server setup

Requires Docker Compose, persistent storage, HTTPS routing for both subdomains, and an SMTP provider authorized to send as `jarom@inflectionarchitectures.com`. The root domain does not need to move off GitHub Pages.

1. Verify `inflectionarchitectures.com` in [Resend](https://resend.com/docs/send-with-smtp), add the sender DNS records it supplies, and create a sending API key. We use SMTP over TLS on port 465; no client emails are sent during setup.
2. On the server, prepare the private configuration:

   ```sh
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   .venv/bin/python configure.py
   ```

   The helper prompts for your one login/password, hashes the password, generates a session secret, and stores settings in ignored `.env`. No account registration exists. Default login is `jarom`. To change your password later, replace `ADMIN_PASSWORD_HASH` with a Werkzeug hash and rotate `SECRET_KEY` to expire sessions; restart the service. Keep hashes single-quoted in `.env` to preserve `$` characters.
3. Choose either an existing host tunnel or a new dedicated Docker tunnel:
   - **Existing host tunnel:** leave the tunnel token blank in the helper, then run `docker compose up -d --build`. In that tunnel's Cloudflare dashboard, add both published application routes below with service **`http://localhost:8091`**. Do not replace existing routes.
   - **Dedicated Docker tunnel:** create a remotely managed tunnel in Cloudflare, paste its token privately into the helper, and run `docker compose -f compose.yaml -f compose.tunnel.yaml up -d --build`. Add both routes with service **`http://feedback:8000`**. The token is mounted as a file, not passed on the command line.

   | Public hostname | Path | Service |
   | --- | --- | --- |
   | `admin.inflectionarchitectures.com` | All | Origin chosen above |
   | `feedback.inflectionarchitectures.com` | All | Origin chosen above |

   Leave **HTTP Host Header** unset so the original hostname reaches the app. Cloudflare provides public HTTPS. No inbound router ports are needed. Keep the apex and `www` GitHub Pages records unchanged. Do not add interactive authentication to the feedback hostname: its testimonial feed must be public. Configure these hosts to bypass any custom “cache everything” rule; the application sends `Cache-Control: no-store`.
4. Confirm `docker compose ps` reports the app healthy and the tunnel dashboard reports Connected. Never put tunnel tokens, API keys, or passwords in GitHub. Avoid proxy logging of private `/f/…` invitation URLs.
5. Open `https://admin.inflectionarchitectures.com`, sign in, and create a form. First send a test invitation to an email address you control. Verify actual inbox receipt, complete the form, then approve/publish it and confirm the homepage displays it. Hide the test response afterward.

The public feed is `https://feedback.inflectionarchitectures.com/api/testimonials`. Its CORS origin defaults to `https://inflectionarchitectures.com`; keep `PUBLIC_SITE_ORIGIN` in sync with the canonical marketing domain. The React component supports `VITE_TESTIMONIALS_URL` for a different feed URL.

No production secrets, clients, testimonials, invitation sends, DNS changes, or server deployments are included in this repository. SMTP acceptance is recorded as `sent`; this is not proof of inbox delivery. An unconfirmed send revokes that invitation, and admin must send a fresh invitation after resolving email settings.

## Data and operations

SQLite lives in the named `feedback-data` volume at `/data/feedback.sqlite3`; recreating the container preserves forms, invitations, and responses. Do not run `docker compose down -v` unless you intend to delete that data. This is a single-host service, not a multi-server database deployment.

Back up the database using SQLite's online backup API; do not copy only the main SQLite file while writes are happening (WAL files may contain committed data):

```sh
docker compose exec feedback python -c 'import sqlite3; source=sqlite3.connect("/data/feedback.sqlite3"); target=sqlite3.connect("/data/feedback-backup.sqlite3"); source.backup(target); target.close(); source.close()'
mkdir -p backups
docker compose cp feedback:/data/feedback-backup.sqlite3 backups/feedback.sqlite3
```

Keep backups encrypted and off the server. Test restoration to a separate volume. Never commit databases or `.env` files. Configure recurring backups in the server's existing operations tooling before relying on the service.

The app uses host-only secure HttpOnly cookies, CSRF tokens on admin mutations, escaped templates, restrictive response headers, hashed invitation tokens, bounded inputs, and a shared limit of ten login attempts per five minutes. A burst of failed sign-ins can temporarily block all sign-ins; put an identity-aware access layer in front of the **admin hostname only** if you want stronger identity controls. Do not protect the public feed with interactive login.

## Development and verification

```sh
PYTHONPATH=feedback /path/to/venv/bin/python -m unittest discover -s feedback/tests -v
```

Tests mock SMTP and use isolated temporary databases. They cover mandatory approval, legacy automatic-publication bypass prevention, owner login, consent enforcement, public-field filtering, one-use tokens, revocation, expiry, SMTP failure, CSRF, admin isolation, validation, escaped text, and login throttling. They do not send real email.

The test configuration permits HTTP and non-secure cookies for isolated local browser previews. Production requires HTTPS origins and secure cookies.
