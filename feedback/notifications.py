"""Deliver durable submission alerts without delaying customer form submissions."""
from contextlib import closing
import json
import os
import sqlite3
import time
from urllib.request import Request, urlopen


def publish(config, message, click):
    payload = {"topic": config["NTFY_TOPIC"], "title": "New client feedback",
               "message": message, "click": click, "tags": ["speech_balloon"]}
    request = Request(config["NTFY_URL"].rstrip("/") + "/", data=json.dumps(payload).encode(),
                      headers={"Content-Type": "application/json",
                               "Authorization": "Bearer " + config["NTFY_TOKEN"]}, method="POST")
    with urlopen(request, timeout=5) as response:
        result = json.load(response)
        if not result.get("id") or result.get("event") != "message":
            raise ValueError("Notification was not confirmed accepted")


def deliver_pending(config, limit=10):
    if not all(config.get(key) for key in ("NTFY_URL", "NTFY_TOPIC", "NTFY_TOKEN")):
        return 0
    delivered = 0
    with closing(sqlite3.connect(config["DATABASE_PATH"], timeout=10)) as db:
        db.row_factory = sqlite3.Row
        for _ in range(limit):
            now = int(time.time())
            with db:
                db.execute("BEGIN IMMEDIATE")
                row = db.execute("SELECT n.*, r.consent FROM notification_outbox n JOIN responses r ON r.id=n.response_id WHERE n.sent_at IS NULL AND n.next_attempt_at<=? ORDER BY n.next_attempt_at LIMIT 1", (now,)).fetchone()
                if row is None:
                    break
                # Lease the job so concurrent workers do not send it together.
                db.execute("UPDATE notification_outbox SET next_attempt_at=?, attempts=attempts+1 WHERE response_id=?", (now + 60, row["response_id"]))
            message = "A client submitted feedback. " + ("A testimonial is awaiting your approval." if row["consent"] else "This response is private; publication permission was not granted.")
            click = config["ADMIN_ORIGIN"].rstrip("/") + "/admin/responses/" + row["response_id"]
            try:
                publish(config, message, click)
            except (OSError, ValueError):
                with db:
                    delay = min(3600, 60 * 2 ** min(row["attempts"], 6))
                    db.execute("UPDATE notification_outbox SET next_attempt_at=? WHERE response_id=?", (now + delay, row["response_id"]))
                print("Notification not confirmed; retained for retry.")
            else:
                with db:
                    db.execute("UPDATE notification_outbox SET sent_at=? WHERE response_id=?", (int(time.time()), row["response_id"]))
                delivered += 1
    return delivered


if __name__ == "__main__":
    print(f"Notifications delivered: {deliver_pending(os.environ)}")
