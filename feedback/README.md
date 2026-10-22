# Client feedback service

The marketing site stays on GitHub Pages. This Docker service hosts both `feedback.inflectionarchitectures.com` (client forms and the public testimonial feed) and `admin.inflectionarchitectures.com` (password-protected form creation, invitation sending, and response management). Route both hosts to the same service while preserving the original Host header. Admin routes are rejected on the feedback hostname.

## What is implemented

- Create reusable forms with a title, introduction, service label, and up to eight private free-text questions.
- Every form includes a testimonial, name, optional role/company, and optional explicit publication consent.
- Choose automatic publication per form, or leave it off to review responses first.
- Email invitations using authenticated SMTP with TLS. Links expire after 30 days and accept one response. Revoke unused links from admin.
- Public feed includes only approved, consented testimonials. No client emails or private answers are exposed.
- Publish or hide consented testimonials from admin. Original client wording is preserved; editing client quotes is not supported.
- Homepage displays up to 12 published testimonials, newest first. Empty/unavailable feeds hide the section without disrupting the site. Changes appear on the next page load.

## Server setup

Requires Docker Compose, persistent storage, HTTPS routing for both subdomains, and an SMTP provider authorized to send as `jarom@inflectionarchitectures.com`. The root domain does not need to move off GitHub Pages.

1. Copy `.env.example` to `.env` in this directory.
2. Generate a session secret with `python3 -c 'import secrets; print(secrets.token_urlsafe(48))'` and set `SECRET_KEY`.
3. Generate an admin password hash in a temporary Python environment with the requirements installed:

   ```sh
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   .venv/bin/python -c 'from getpass import getpass; from werkzeug.security import generate_password_hash; print(generate_password_hash(getpass("Admin password: ")))' 
   ```

   Set `ADMIN_PASSWORD_HASH` to the output, wrapped in **single quotes** in `.env` so Compose preserves the dollar signs. Use a strong unique password. To invalidate existing sessions as well as change the password, rotate `SECRET_KEY`.
4. Fill in `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, and `SMTP_FROM`. `SMTP_TLS=starttls` is normally used with port 587; use `ssl` for port 465. The service refuses unencrypted SMTP. Configure the provider's sender/domain verification and DNS records before sending invitations.
5. Run `docker compose up -d --build` from this directory. The service binds only to `127.0.0.1:8091`, ready for a host reverse proxy or tunnel. If the proxy is in Docker, connect it to this service's Docker network and route to `feedback:8000` instead of loopback.
6. Route both HTTPS subdomains to that listener. Preserve `Host`; do not rewrite it to `localhost`. The app does not trust client-provided forwarding headers. If using Cloudflare Tunnel, add both public hostnames to the tunnel; the apex domain can retain its existing GitHub Pages DNS records. Avoid logging client `/f/…` invitation URLs at your proxy, and do not put analytics on the client form pages.
7. Open `https://admin.inflectionarchitectures.com`, sign in, and create a form. First send a test invitation to an email address you control. Verify actual inbox receipt, complete the form, then approve/publish it and confirm the homepage displays it. Hide the test response afterward.

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

Tests mock SMTP and use isolated temporary databases. They cover approval/automatic publication, consent enforcement, public-field filtering, one-use tokens, revocation, expiry, SMTP failure, CSRF, admin isolation, validation, escaped text, and login throttling. They do not send real email.

The test configuration permits HTTP and non-secure cookies for isolated local browser previews. Production requires HTTPS origins and secure cookies.
