import json
import sqlite3
from contextlib import closing
from unittest.mock import patch, MagicMock
from test_app import FeedbackTestCase, ADMIN
from notifications import deliver_pending, publish


class NotificationTests(FeedbackTestCase):
    def setUp(self):
        super().setUp()
        self.app.config.update(NTFY_URL="https://notify.example.test", NTFY_TOPIC="client-feedback", NTFY_TOKEN="test-token")

    def test_submission_queues_once_and_publishes_private_metadata(self):
        self.login()
        token = self.invite(self.create_form())
        self.submit(token)
        self.submit(token)
        with closing(sqlite3.connect(self.database)) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM notification_outbox").fetchone()[0], 1)
        with patch("notifications.publish") as sender:
            self.assertEqual(deliver_pending(self.app.config), 1)
            self.assertEqual(deliver_pending(self.app.config), 0)
            sender.assert_called_once()
            _, message, click = sender.call_args.args
            self.assertIn("awaiting your approval", message)
            self.assertNotIn("Client Name", message)
            self.assertNotIn("Private details", message)
            self.assertEqual(click, ADMIN + "/admin/responses/" + self.response_id())

    def test_failure_retries_without_affecting_submission(self):
        self.login()
        result = self.submit(self.invite(self.create_form()), consent=False)
        self.assertEqual(result.status_code, 303)
        with patch("notifications.publish", side_effect=OSError("offline")) as sender:
            self.assertEqual(deliver_pending(self.app.config), 0)
            self.assertEqual(deliver_pending(self.app.config), 0)
            sender.assert_called_once()
        with closing(sqlite3.connect(self.database)) as db, db:
            self.assertEqual(db.execute("SELECT attempts,sent_at FROM notification_outbox").fetchone(), (1, None))
            db.execute("UPDATE notification_outbox SET next_attempt_at=0")
        with patch("notifications.publish") as sender:
            self.assertEqual(deliver_pending(self.app.config), 1)
            self.assertIn("private", sender.call_args.args[1])

    def test_deleted_response_cancels_pending_notification(self):
        self.login()
        self.submit(self.invite(self.create_form()))
        self.post(f"/admin/responses/{self.response_id()}/delete", {})
        with patch("notifications.publish") as sender:
            self.assertEqual(deliver_pending(self.app.config), 0)
            sender.assert_not_called()
        with closing(sqlite3.connect(self.database)) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM notification_outbox").fetchone()[0], 0)

    def test_publish_authenticated_json(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b'{"id":"test-id","event":"message"}'
        with patch("notifications.urlopen", return_value=response) as http:
            publish(self.app.config, "New feedback", ADMIN + "/admin")
            request = http.call_args.args[0]
            self.assertEqual(request.get_header("Authorization"), "Bearer test-token")
            payload = json.loads(request.data)
            self.assertEqual(payload["topic"], "client-feedback")
            self.assertEqual(payload["click"], ADMIN + "/admin")
            self.assertEqual(http.call_args.kwargs["timeout"], 5)

    def test_disabled_configuration_does_not_send(self):
        self.login()
        self.submit(self.invite(self.create_form()))
        self.app.config["NTFY_TOKEN"] = ""
        with patch("notifications.publish") as sender:
            self.assertEqual(deliver_pending(self.app.config), 0)
            sender.assert_not_called()

