from contextlib import closing
import re
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from werkzeug.security import generate_password_hash
from app import create_app

ADMIN = "https://admin.example.test"
PUBLIC = "https://feedback.example.test"


class FeedbackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.database = str(Path(self.temp.name) / "test.sqlite3")
        self.app = create_app({"TESTING": True, "SECRET_KEY": "test-secret-" * 4,
            "ADMIN_PASSWORD_HASH": generate_password_hash("long-test-password"),
            "ADMIN_ORIGIN": ADMIN, "FEEDBACK_ORIGIN": PUBLIC,
            "PUBLIC_SITE_ORIGIN": "https://www.example.test", "DATABASE_PATH": self.database,
            "SMTP_HOST": "smtp.example.test"})
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp.cleanup()

    def get(self, path, public=False):
        return self.client.get(path, base_url=PUBLIC if public else ADMIN)

    def post(self, path, data, public=False, csrf=True):
        if csrf and not public:
            html = self.get("/admin/login").text
            data = {**data, "csrf": re.search('name="csrf" value="([^"]+)"', html)[1]}
        return self.client.post(path, data=data, base_url=PUBLIC if public else ADMIN)

    def login(self):
        result = self.post("/admin/login", {"username": "jarom", "password": "long-test-password"})
        self.assertEqual(result.status_code, 302)

    def create_form(self, automatic=False):
        result = self.post("/admin/forms/new", {"title": "Project feedback", "service": "Website", "introduction": "Thanks!", "questions": "What could improve?", "auto_publish": "yes" if automatic else ""})
        self.assertEqual(result.status_code, 302)
        return result.location.rsplit("/", 1)[1]

    def invite(self, form_id):
        with patch("app.smtplib.SMTP") as smtp:
            result = self.post(f"/admin/forms/{form_id}/invite", {"email": "client@example.test", "client_name": "Client"})
            self.assertEqual(result.status_code, 302)
            message = smtp.return_value.__enter__.return_value.send_message.call_args.args[0]
            token = re.search(r"/f/([\w-]+)", message.get_content())[1]
        return token

    def submit(self, token, consent=True):
        return self.post(f"/f/{token}", {"name": "Client Name", "company": "Test Co", "role": "Owner", "quote": "The project made a difference.", "answer_0": "Private details", "consent": "yes" if consent else ""}, public=True)

    def response_id(self):
        with closing(sqlite3.connect(self.database)) as db, db:
            return db.execute("SELECT id FROM responses").fetchone()[0]

    def test_approval_flow_and_public_field_allowlist(self):
        self.login()
        token = self.invite(self.create_form())
        self.assertEqual(self.get(f"/f/{token}", public=True).status_code, 200)
        self.assertEqual(self.submit(token).status_code, 303)
        self.assertEqual(self.get("/api/testimonials", public=True).json, {"testimonials": []})
        response_id = self.response_id()
        self.assertIn("Private details", self.get(f"/admin/responses/{response_id}").text)
        self.assertEqual(self.post(f"/admin/responses/{response_id}/status", {"status": "published"}).status_code, 302)
        feed = self.get("/api/testimonials", public=True)
        self.assertEqual(feed.headers["Access-Control-Allow-Origin"], "https://www.example.test")
        item = feed.json["testimonials"][0]
        self.assertEqual(set(item), {"id", "name", "company", "role", "quote", "service"})
        self.assertNotIn("Private details", feed.text)
        self.assertNotIn("client@example.test", feed.text)
        self.post(f"/admin/responses/{response_id}/status", {"status": "hidden"})
        self.assertEqual(self.get("/api/testimonials", public=True).json["testimonials"], [])

    def test_legacy_automatic_setting_cannot_bypass_approval_and_one_use(self):
        self.login()
        form_id = self.create_form(automatic=True)
        with closing(sqlite3.connect(self.database)) as db, db:
            self.assertEqual(db.execute("SELECT auto_publish FROM forms").fetchone()[0], 0)
            db.execute("UPDATE forms SET auto_publish=1")
        token = self.invite(form_id)
        self.submit(token)
        self.submit(token)
        self.assertEqual(len(self.get("/api/testimonials", public=True).json["testimonials"]), 0)
        self.assertIn("Client Name", self.get("/admin/queue").text)
        with closing(sqlite3.connect(self.database)) as db, db:
            self.assertEqual(db.execute("SELECT count(*) FROM responses").fetchone()[0], 1)
            self.assertNotEqual(db.execute("SELECT token_hash FROM invitations").fetchone()[0], token)

    def test_no_consent_cannot_be_published_even_by_admin(self):
        self.login()
        self.submit(self.invite(self.create_form(automatic=True)), consent=False)
        self.assertEqual(self.get("/api/testimonials", public=True).json["testimonials"], [])
        self.assertEqual(self.post(f"/admin/responses/{self.response_id()}/status", {"status": "published"}).status_code, 403)

    def test_auth_csrf_host_isolation_and_logout(self):
        self.assertEqual(self.get("/admin").status_code, 302)
        self.assertEqual(self.get("/admin", public=True).status_code, 404)
        self.assertEqual(self.post("/admin/login", {"username": "jarom", "password": "long-test-password"}, csrf=False).status_code, 403)
        self.login()
        self.assertEqual(self.get("/admin").status_code, 200)
        self.assertEqual(self.post("/admin/forms/new", {"title": "Attack"}, csrf=False).status_code, 403)
        self.post("/admin/logout", {})
        self.assertEqual(self.get("/admin").status_code, 302)

    def test_resend_ssl_delivery(self):
        self.login()
        form_id = self.create_form()
        self.app.config.update(SMTP_TLS="ssl", SMTP_PORT=465, SMTP_USERNAME="resend", SMTP_PASSWORD="test-key")
        with patch("app.smtplib.SMTP_SSL") as smtp:
            self.post(f"/admin/forms/{form_id}/invite", {"email": "client@example.test", "client_name": "Client"})
            smtp.return_value.__enter__.return_value.login.assert_called_once_with("resend", "test-key")
            smtp.return_value.__enter__.return_value.send_message.assert_called_once()
            self.assertIsNotNone(smtp.call_args.kwargs["context"])

    def test_failed_email_revokes_link(self):
        self.login()
        form_id = self.create_form()
        with patch("app.smtplib.SMTP", side_effect=OSError("Network failure")):
            self.post(f"/admin/forms/{form_id}/invite", {"email": "client@example.test", "client_name": "Client"})
        with closing(sqlite3.connect(self.database)) as db, db:
            self.assertEqual(db.execute("SELECT mail_status,revoked FROM invitations").fetchone(), ("failed", 1))

    def test_revoked_and_expired_links_rejected(self):
        self.login()
        form_id = self.create_form()
        token = self.invite(form_id)
        with closing(sqlite3.connect(self.database)) as db, db:
            invitation_id = db.execute("SELECT id FROM invitations").fetchone()[0]
        self.post(f"/admin/invitations/{invitation_id}/revoke", {})
        self.assertEqual(self.submit(token).status_code, 410)
        token2 = self.invite(form_id)
        with closing(sqlite3.connect(self.database)) as db, db:
            db.execute("UPDATE invitations SET expires_at=0")
        self.assertEqual(self.get(f"/f/{token2}", public=True).status_code, 410)

    def test_input_validation_and_html_escaping(self):
        self.login()
        form_id = self.create_form()
        self.post(f"/admin/forms/{form_id}/invite", {"email": "bad\naddress", "client_name": "Client"})
        with closing(sqlite3.connect(self.database)) as db, db:
            self.assertEqual(db.execute("SELECT count(*) FROM invitations").fetchone()[0], 0)
        token = self.invite(form_id)
        result = self.post(f"/f/{token}", {"name": "Client", "quote": "x" * 1501}, public=True)
        self.assertIn("maximum 1500", result.text)
        result = self.post(f"/f/{token}", {"name": "<script>alert(1)</script>", "quote": "fine"}, public=True)
        self.assertEqual(result.status_code, 303)
        self.assertIn("&lt;script&gt;", self.get(f"/admin/responses/{self.response_id()}").text)

    def test_null_origin_with_valid_csrf_and_cross_site_rejection(self):
        html = self.get("/admin/login").text
        token = re.search('name="csrf" value="([^\"]+)"', html)[1]
        data = {"username": "jarom", "password": "long-test-password", "csrf": token}
        result = self.client.post("/admin/login", data=data, base_url=ADMIN,
            headers={"Origin": "null", "Sec-Fetch-Site": "same-origin"})
        self.assertEqual(result.status_code, 302)
        self.assertEqual(self.client.post("/admin/login", data=data, base_url=ADMIN,
            headers={"Origin": "null", "Sec-Fetch-Site": "cross-site"}).status_code, 403)
        token = self.invite(self.create_form())
        self.assertEqual(self.client.post(f"/f/{token}", data={"name": "Client", "quote": "Hello"}, base_url=PUBLIC,
            headers={"Origin": "https://attacker.test", "Sec-Fetch-Site": "cross-site"}).status_code, 403)
        self.assertEqual(self.client.post(f"/f/{token}", data={"name": "Client", "quote": "Hello"}, base_url=PUBLIC,
            headers={"Origin": "null", "Sec-Fetch-Site": "same-origin"}).status_code, 303)

    def test_only_configured_owner_can_login(self):
        for username in ("", "someone-else"):
            self.post("/admin/login", {"username": username, "password": "long-test-password"})
            self.assertEqual(self.get("/admin/queue").status_code, 302)
        self.login()
        self.assertEqual(self.get("/admin/queue").status_code, 200)

    def test_login_throttle(self):
        for _ in range(10):
            self.assertEqual(self.post("/admin/login", {"password": "wrong"}).status_code, 200)
        self.assertEqual(self.post("/admin/login", {"password": "wrong"}).status_code, 429)


if __name__ == "__main__":
    unittest.main()
