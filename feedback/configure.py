"""Run on the deployment server; credentials are never echoed or printed."""
from getpass import getpass
from pathlib import Path
import os
import secrets
from werkzeug.security import generate_password_hash


def main():
    root = Path(__file__).resolve().parent
    if (root / '.env').exists() or (root / 'secrets' / 'tunnel_token').exists():
        raise SystemExit('.env already exists; edit it locally to preserve existing settings.')
    username = input('Owner login [jarom]: ').strip() or 'jarom'
    password = getpass('Owner password (at least 16 characters): ')
    if len(password) < 16 or password != getpass('Repeat password: '):
        raise SystemExit('Passwords must match and contain at least 16 characters.')
    smtp_key = getpass('Resend API key (sending permission for your verified domain): ').strip()
    sender = input('Verified sender [jarom@inflectionarchitectures.com]: ').strip() or 'jarom@inflectionarchitectures.com'
    token = getpass('Cloudflare tunnel token (leave blank to use an existing host tunnel): ').strip()
    if not smtp_key:
        raise SystemExit('A Resend API key is required.')
    values = dict(SECRET_KEY=secrets.token_urlsafe(48), ADMIN_USERNAME=username,
                  ADMIN_PASSWORD_HASH=generate_password_hash(password),
                  ADMIN_ORIGIN='https://admin.inflectionarchitectures.com',
                  FEEDBACK_ORIGIN='https://feedback.inflectionarchitectures.com',
                  PUBLIC_SITE_ORIGIN='https://inflectionarchitectures.com',
                  DATABASE_PATH='/data/feedback.sqlite3', SMTP_HOST='smtp.resend.com',
                  SMTP_PORT='465', SMTP_USERNAME='resend', SMTP_PASSWORD=smtp_key,
                  SMTP_FROM=f'Inflection Architectures <{sender}>', SMTP_TLS='ssl')
    if any(any(c in v for c in "\r\n'\\") for v in values.values()):
        raise SystemExit('Settings contain unsupported characters.')
    if token and any(c.isspace() for c in token):
        raise SystemExit('Tunnel token must not contain whitespace.')
    os.umask(0o077)
    with (root / '.env').open('x') as file:
        file.write(''.join(f"{k}='{v}'\n" for k, v in values.items()))
    if token:
        directory = root / 'secrets'
        directory.mkdir(exist_ok=True, mode=0o700)
        with (directory / 'tunnel_token').open('x') as file:
            file.write(token)
        # cloudflared runs as a non-root user inside the container. The host
        # parent directory remains private; only this file is bind-mounted.
        (directory / 'tunnel_token').chmod(0o444)
    print('Configuration saved privately. Follow README.md to start the service.')


if __name__ == '__main__':
    main()
