"""Configure authenticated ntfy alerts from a private SSH terminal."""
from getpass import getpass
from pathlib import Path
import os
import re
import subprocess
from notifications import publish

root = Path(__file__).resolve().parent
if not (root / ".env").exists():
    raise SystemExit("Configure the feedback app first.")
token = getpass("ntfy access token (hidden): ").strip()
if not re.fullmatch(r"[A-Za-z0-9_-]+", token):
    raise SystemExit("Enter a valid ntfy access token.")
updates = {"NTFY_URL": "http://127.0.0.1:8085", "NTFY_TOPIC": "client-feedback", "NTFY_TOKEN": token}
try:
    publish(updates, "Setup test: client feedback notifications are connected.", "https://admin.inflectionarchitectures.com/admin")
except (OSError, ValueError):
    raise SystemExit("ntfy did not accept the setup notification. Check the token has write access to client-feedback. Settings were not changed.")
lines = (root / ".env").read_text().splitlines()
lines = [line for line in lines if line.partition("=")[0] not in updates]
lines.extend(f"{key}='{value}'" for key, value in updates.items())
os.umask(0o077)
temporary = root / ".env.new"
with temporary.open("x") as file:
    file.write("\n".join(lines) + "\n")
temporary.replace(root / ".env")
subprocess.run(["systemctl", "--user", "restart", "ia-feedback.service"], check=True)
subprocess.run(["systemctl", "--user", "enable", "--now", "ia-feedback-notify.timer"], check=True)
print("Connected. Subscribe to client-feedback on https://notify.inflectionarchitectures.com using your ntfy account. A setup notification was accepted by ntfy.")
