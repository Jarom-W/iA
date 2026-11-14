from contextlib import closing
import io
import json
from pathlib import Path
import re
import secrets
import tempfile
import time
import unittest
from unittest.mock import patch

from PIL import Image
from app import create_app

ORIGIN = "https://survey.example.test"


def questions():
    return [
        dict(
            id="colors",
            label="Which colors?",
            kind="multiple",
            required=True,
            photo="",
            alt="",
            options=[
                {"label": "Green", "color": "#81f268"},
                {"label": "Blue", "color": "#4488ff"},
            ],
        ),
        dict(
            id="rating",
            label="How much do you like it?",
            kind="rating",
            required=False,
            photo="",
            alt="",
            options=[],
        ),
        dict(
            id="notes",
            label="Anything else?",
            kind="text",
            required=False,
            photo="",
            alt="",
            options=[],
        ),
    ]


class SurveyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.app = create_app(
            dict(
                TESTING=True,
                SECRET_KEY="test-only-" * 8,
                ORIGIN=ORIGIN,
                DATABASE_PATH=str(Path(self.temp.name) / "survey.sqlite3"),
                AUTH_MODE="oidc",
                OIDC_ISSUER="https://auth.example.test/realms/inflection",
                OIDC_CLIENT_ID="ia-survey",
                OIDC_CLIENT_SECRET="test-secret",
                AUTH_DATABASE_PATH="",
            )
        )
        self.admin = self.app.test_client()
        self.public = self.app.test_client()
        self.auth = self.app.extensions["platform_auth"]
        self.permissions = ["survey:read", "survey:write"]
        self.mock = patch.object(
            self.auth,
            "introspect",
            side_effect=lambda *_: dict(
                sub="owner", username="owner", permissions=self.permissions
            ),
        )
        self.mock.start()
        self.addCleanup(self.mock.stop)
        sid = secrets.token_urlsafe(24)
        record = {
            "sub": "owner",
            "token": {"access_token": "test-access", "expires_at": time.time() + 300},
        }
        with closing(self.auth.connect()) as db, db:
            db.execute(
                "INSERT INTO auth_sessions VALUES(?,?,?)",
                (
                    self.auth.digest(sid),
                    self.auth.cipher.encrypt(json.dumps(record).encode()),
                    int(time.time()) + 3600,
                ),
            )
        with self.admin.session_transaction(base_url=ORIGIN) as session:
            session.update(sso_sid=sid, csrf="admin-csrf")

    def get(self, path, public=False):
        return (self.public if public else self.admin).get(path, base_url=ORIGIN)

    def post(self, path, data=None, json_data=None):
        if json_data is not None:
            return self.admin.post(
                path,
                json=json_data,
                base_url=ORIGIN,
                headers={"X-CSRF-Token": "admin-csrf"},
            )
        return self.admin.post(
            path, data=dict(csrf="admin-csrf", **(data or {})), base_url=ORIGIN
        )

    def create(self, qs=None):
        r = self.post("/admin/new")
        self.assertEqual(r.status_code, 302)
        sid = r.location.split("/")[-2]
        r = self.post(
            f"/admin/surveys/{sid}/edit",
            json_data=dict(
                title="Market prints",
                description="Help choose the next colors.",
                thank_you="Thank you!",
                revision=0,
                questions=qs or questions(),
            ),
        )
        self.assertEqual(r.status_code, 200, r.text)
        with closing(self.database()) as db:
            token = db.execute(
                "SELECT token FROM surveys WHERE id=?", (sid,)
            ).fetchone()[0]
        return sid, token

    def database(self):
        return __import__("sqlite3").connect(self.app.config["DATABASE_PATH"])

    def publish(self, sid):
        return self.post(f"/admin/surveys/{sid}/state", {"state": "open"})

    def answer(self, token, answers=None, ticket=None):
        if ticket is None:
            page = self.get("/s/" + token, True).text
            ticket = re.search(r'name="response_token" value="([^"]+)"', page)[1]
        with self.public.session_transaction(base_url=ORIGIN) as s:
            csrf = s["csrf"]
        return (
            self.public.post(
                "/s/" + token,
                base_url=ORIGIN,
                data=dict(
                    csrf=csrf,
                    response_token=ticket,
                    **(
                        answers
                        or {"colors": ["0", "1"], "rating": "4", "notes": "Looks great"}
                    ),
                ),
            ),
            ticket,
        )

    def test_admin_requires_oidc_and_permissions(self):
        self.assertEqual(self.get("/admin", True).status_code, 302)
        self.permissions = ["time:read"]
        self.assertEqual(self.get("/admin").status_code, 403)
        self.permissions = ["survey:read"]
        self.assertEqual(self.get("/admin").status_code, 200)
        self.assertEqual(self.post("/admin/new").status_code, 403)
        self.assertEqual(
            self.admin.post("/admin/new", base_url=ORIGIN).status_code, 403
        )
        self.assertEqual(
            self.admin.get("/admin", base_url="https://wrong.example.test").status_code,
            400,
        )

    def test_publish_respond_analytics_and_retries(self):
        sid, token = self.create()
        self.assertEqual(self.get("/s/" + token, True).status_code, 404)
        self.assertEqual(self.publish(sid).status_code, 302)
        response, ticket = self.answer(token)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.answer(token, ticket=ticket)[0].status_code, 302)
        with closing(self.database()) as db:
            self.assertEqual(
                db.execute("SELECT COUNT(*) FROM responses").fetchone()[0], 1
            )
        page = self.get("/admin/surveys/" + sid)
        self.assertEqual(page.status_code, 200)
        self.assertIn("100.0%", page.text)
        self.assertIn("Average 4.0 / 5", page.text)
        self.assertIn("Looks great", page.text)
        for path in [
            f"/admin/surveys/{sid}",
            f"/admin/surveys/{sid}/export.csv",
            f"/admin/surveys/{sid}/qr.png",
        ]:
            self.assertEqual(self.get(path, True).status_code, 302)

    def test_invalid_answers_keep_input_and_do_not_count(self):
        sid, token = self.create()
        self.publish(sid)
        for data in [
            {"notes": "keep this"},
            {"colors": ["8"], "rating": "9"},
            {"colors": ["0"], "notes": "x" * 2001},
        ]:
            response, _ = self.answer(token, data)
            self.assertEqual(response.status_code, 422)
        with closing(self.database()) as db:
            self.assertEqual(
                db.execute("SELECT COUNT(*) FROM responses").fetchone()[0], 0
            )
        response, _ = self.answer(
            token, {"colors": ["0", "0"], "notes": "<script>alert(1)</script>"}
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("&lt;script&gt;", self.get("/admin/surveys/" + sid).text)

    def test_tampered_tickets_and_cross_browser_submissions_rejected(self):
        sid, token = self.create()
        self.publish(sid)
        page = self.get("/s/" + token, True).text
        ticket = re.search(r'name="response_token" value="([^"]+)"', page)[1]
        self.assertEqual(self.answer(token, ticket=ticket + "x")[0].status_code, 400)
        other = self.app.test_client()
        other.get("/s/" + token, base_url=ORIGIN)
        with other.session_transaction(base_url=ORIGIN) as s:
            csrf = s["csrf"]
        self.assertEqual(
            other.post(
                "/s/" + token,
                base_url=ORIGIN,
                data={"csrf": csrf, "response_token": ticket, "colors": "0"},
            ).status_code,
            400,
        )

    def test_closed_survey_and_published_edits(self):
        sid, token = self.create()
        self.publish(sid)
        page = self.get("/s/" + token, True).text
        ticket = re.search(r'name="response_token" value="([^"]+)"', page)[1]
        self.post(f"/admin/surveys/{sid}/state", {"state": "closed"})
        self.assertEqual(self.answer(token, ticket=ticket)[0].status_code, 410)
        self.assertEqual(self.get("/s/" + token, True).status_code, 410)
        self.assertEqual(
            self.post(f"/admin/surveys/{sid}/edit", json_data={}).status_code, 409
        )
        self.publish(sid)
        self.assertEqual(self.get("/s/" + token, True).status_code, 200)

    def test_stale_editor_and_invalid_questions(self):
        sid, token = self.create()
        data = dict(
            title="Changed",
            description="",
            thank_you="Thanks",
            revision=0,
            questions=questions(),
        )
        self.assertEqual(
            self.post(f"/admin/surveys/{sid}/edit", json_data=data).status_code, 409
        )
        data["revision"] = 1
        data["questions"][0]["options"][0]["color"] = "url(https://evil.test)"
        self.assertEqual(
            self.post(f"/admin/surveys/{sid}/edit", json_data=data).status_code, 400
        )
        data["questions"] = questions()
        data["questions"][0]["photo"] = "other-survey-photo"
        self.assertEqual(
            self.post(f"/admin/surveys/{sid}/edit", json_data=data).status_code, 400
        )

    def test_photo_reencoding_isolation_and_copy(self):
        sid, token = self.create()
        image = Image.new("RGB", (24, 24), "green")
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        buf.seek(0)
        response = self.post(
            f"/admin/surveys/{sid}/photos", {"photo": (buf, "print.png")}
        )
        self.assertEqual(response.status_code, 200)
        pid = response.json["id"]
        self.assertEqual(self.get(f"/s/{token}/photos/{pid}", True).status_code, 404)
        qs = questions()
        qs[0].update(photo=pid, alt="A small green printed planter")
        self.assertEqual(
            self.post(
                f"/admin/surveys/{sid}/edit",
                json_data=dict(
                    title="Photos",
                    description="",
                    thank_you="Thanks",
                    revision=1,
                    questions=qs,
                ),
            ).status_code,
            200,
        )
        self.publish(sid)
        response = self.get(f"/s/{token}/photos/{pid}", True)
        self.assertEqual(response.mimetype, "image/jpeg")
        self.assertEqual(Image.open(io.BytesIO(response.data)).format, "JPEG")
        sid2, token2 = self.create()
        self.publish(sid2)
        self.assertEqual(self.get(f"/s/{token2}/photos/{pid}", True).status_code, 404)
        copied = self.post(f"/admin/surveys/{sid}/duplicate")
        self.assertEqual(copied.status_code, 302)
        copy_id = copied.location.split("/")[-2]
        with closing(self.database()) as db:
            copied = db.execute(
                "SELECT state,questions FROM surveys WHERE id=?", (copy_id,)
            ).fetchone()
            self.assertEqual(copied[0], "draft")
            self.assertNotEqual(json.loads(copied[1])[0]["photo"], pid)
        self.assertEqual(
            self.post(
                f"/admin/surveys/{sid2}/photos",
                {"photo": (io.BytesIO(b"<svg/>"), "fake.png")},
            ).status_code,
            409,
        )

    def test_qr_and_csv(self):
        sid, token = self.create()
        self.publish(sid)
        self.answer(token, {"colors": ["0", "1"], "notes": "=SUM(A1)", "rating": "5"})
        response = self.get(f"/admin/surveys/{sid}/export.csv")
        self.assertEqual(response.status_code, 200)
        self.assertIn("'=SUM(A1)", response.text)
        self.assertIn("Green; Blue", response.text)
        png = self.get(f"/admin/surveys/{sid}/qr.png")
        self.assertEqual(png.mimetype, "image/png")
        self.assertEqual(Image.open(io.BytesIO(png.data)).format, "PNG")
        svg = self.get(f"/admin/surveys/{sid}/qr.svg")
        self.assertEqual(svg.mimetype, "image/svg+xml")
        self.assertIn(b"<svg", svg.data)
        with patch("app.qrcode.QRCode.add_data") as add:
            self.get(f"/admin/surveys/{sid}/qr.png")
            add.assert_called_once_with(ORIGIN + "/s/" + token)

    def test_headers_csrf_and_upload_validation(self):
        sid, token = self.create()
        self.assertEqual(
            self.post(
                f"/admin/surveys/{sid}/photos",
                {"photo": (io.BytesIO(b"<svg/>"), "fake.png")},
            ).status_code,
            400,
        )
        r = self.get("/admin")
        self.assertEqual(r.headers["Cache-Control"], "no-store")
        self.assertIn("frame-ancestors 'none'", r.headers["Content-Security-Policy"])
        self.publish(sid)
        self.get("/s/" + token, True)
        self.assertEqual(
            self.public.post("/s/" + token, base_url=ORIGIN, data={}).status_code, 403
        )

    def test_online_backup_preserves_questions_photos_and_responses(self):
        import os
        import subprocess
        import sys
        import sqlite3

        sid, token = self.create()
        image = io.BytesIO()
        Image.new("RGB", (24, 24), "green").save(image, format="PNG")
        image.seek(0)
        self.post(f"/admin/surveys/{sid}/photos", {"photo": (image, "print.png")})
        self.publish(sid)
        self.answer(token)
        subprocess.run(
            [sys.executable, str(Path(__file__).resolve().parents[1] / "backup.py")],
            env={
                **os.environ,
                "SURVEY_DATABASE_PATH": self.app.config["DATABASE_PATH"],
            },
            check=True,
            capture_output=True,
        )
        backups = list((Path(self.temp.name) / "backups").glob("*.sqlite3"))
        self.assertEqual(len(backups), 1)
        with closing(sqlite3.connect(backups[0])) as db:
            self.assertEqual(db.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            for table in ("surveys", "photos", "responses"):
                self.assertEqual(
                    db.execute("SELECT COUNT(*) FROM " + table).fetchone()[0], 1
                )
        self.assertEqual(backups[0].stat().st_mode & 0o777, 0o600)

    def test_submission_throttle(self):
        sid, token = self.create()
        self.publish(sid)
        self.get("/s/" + token, True)
        with self.public.session_transaction(base_url=ORIGIN) as s:
            visitor = s["visitor"]
        import hashlib

        with closing(self.database()) as db, db:
            db.executemany(
                "INSERT INTO attempts VALUES(?,?)",
                [(hashlib.sha256(visitor.encode()).hexdigest(), int(time.time()))] * 20,
            )
        self.assertEqual(self.answer(token)[0].status_code, 429)


if __name__ == "__main__":
    unittest.main()
