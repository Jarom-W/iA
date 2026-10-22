"""Set the sole owner's password from a private terminal on the server."""
from getpass import getpass
from pathlib import Path
import os
import secrets
from werkzeug.security import generate_password_hash

root = Path(__file__).resolve().parent
password = getpass("New owner password (at least 16 characters): ")
if len(password) < 16 or password != getpass("Repeat password: "):
    raise SystemExit("Passwords must match and contain at least 16 characters.")
settings = (root / ".env").read_text().splitlines()
updates = {"ADMIN_PASSWORD_HASH": generate_password_hash(password), "SECRET_KEY": secrets.token_urlsafe(48)}
settings = [line for line in settings if line.partition("=")[0] not in updates]
settings.extend(f"{key}='{value}'" for key, value in updates.items())
os.umask(0o077)
temporary = root / ".env.new"
with temporary.open("x") as file:
    file.write("\n".join(settings) + "\n")
temporary.replace(root / ".env")
(root / "secrets" / "initial-password").unlink(missing_ok=True)
print("Password updated. Restart the feedback service to apply it and expire existing sessions.")
