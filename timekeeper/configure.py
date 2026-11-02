"""Create private workspace settings. Run from a terminal; never share passwords in chat."""
from getpass import getpass
import os
from pathlib import Path
import secrets
from werkzeug.security import generate_password_hash
from zoneinfo import ZoneInfo


def main():
    root = Path(__file__).resolve().parent
    if (root / '.env').exists():
        raise SystemExit('.env already exists. Edit settings locally to preserve your configuration.')
    username = input('Owner login [jarom]: ').strip() or 'jarom'
    password = getpass('Owner password (16+ characters; use your existing owner password if desired): ')
    if len(password) < 16 or password != getpass('Repeat password: '):
        raise SystemExit('Passwords must match and contain at least 16 characters.')
    zone = input('Timezone [America/Denver]: ').strip() or 'America/Denver'
    ZoneInfo(zone)
    currency = input('Currency [USD]: ').strip().upper() or 'USD'
    if len(currency) != 3 or not currency.isascii() or not currency.isalpha():
        raise SystemExit('Use a three-letter currency code.')
    docker = input('Deploy with Docker? [y/N]: ').strip().lower() == 'y'
    values = dict(TIME_SECRET_KEY=secrets.token_urlsafe(48), ADMIN_USERNAME=username,
        ADMIN_PASSWORD_HASH=generate_password_hash(password), TIME_ORIGIN='https://time.inflectionarchitectures.com',
        TIME_DATABASE_PATH='/data/timekeeper.sqlite3' if docker else str(root / 'data' / 'timekeeper.sqlite3'),
        TIME_TIMEZONE=zone, TIME_CURRENCY=currency)
    if any(any(c in v for c in "\r\n'\\") for v in values.values()):
        raise SystemExit('A setting contains unsupported characters.')
    os.umask(0o077)
    with (root / '.env').open('x') as file:
        file.write(''.join(f"{key}='{value}'\n" for key, value in values.items()))
    print('Private configuration saved. Follow README.md to start the workspace.')


if __name__ == '__main__':
    main()
