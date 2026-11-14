"""Product research surveys: OIDC administration and anonymous public participation."""

from collections import Counter
from contextlib import closing
import csv
from datetime import datetime, timedelta
import hashlib
import hmac
import io
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import time
from urllib.parse import urlsplit
import warnings
from zoneinfo import ZoneInfo

from werkzeug.exceptions import SecurityError
from flask import (
    Flask,
    abort,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from itsdangerous import URLSafeTimedSerializer, BadSignature
from PIL import Image, ImageOps, UnidentifiedImageError
import qrcode
import qrcode.image.svg
from ia_auth import auth_settings, init_auth

KINDS = {
    "single": "Choose one",
    "multiple": "Choose several",
    "rating": "Rating (1–5)",
    "text": "Written answer",
}


def validate_questions(raw, photo_ids):
    if not isinstance(raw, list) or not 1 <= len(raw) <= 20:
        raise ValueError("Add between 1 and 20 questions.")
    result, ids = [], set()
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("Invalid question.")
        qid = item.get("id", "")
        if (
            not isinstance(qid, str)
            or not re.fullmatch(r"[a-zA-Z0-9_-]{1,60}", qid)
            or qid in ids
        ):
            raise ValueError("Each question needs a unique ID.")
        ids.add(qid)
        label, kind = item.get("label"), item.get("kind")
        if (
            not isinstance(label, str)
            or not 1 <= len(label.strip()) <= 300
            or not isinstance(kind, str)
            or kind not in KINDS
        ):
            raise ValueError(
                "Every question needs a title (up to 300 characters) and a supported type."
            )
        photo = item.get("photo", "")
        if not isinstance(photo, str) or (photo and photo not in photo_ids):
            raise ValueError("Use a photo uploaded to this survey.")
        alt = item.get("alt", "")
        if not isinstance(alt, str) or len(alt) > 300:
            raise ValueError("Photo descriptions must be under 300 characters.")
        if photo and not alt.strip():
            raise ValueError("Add a photo description for accessibility.")
        options = item.get("options", []) if kind in ("single", "multiple") else []
        if not isinstance(options, list) or (
            kind in ("single", "multiple") and not 2 <= len(options) <= 20
        ):
            raise ValueError("Choice questions need 2–20 options.")
        cleaned, labels = [], set()
        for option in options:
            if not isinstance(option, dict):
                raise ValueError("Invalid answer option.")
            text, color = option.get("label", ""), option.get("color", "")
            if (
                not isinstance(text, str)
                or not 1 <= len(text.strip()) <= 100
                or text.strip().casefold() in labels
            ):
                raise ValueError(
                    "Options must have distinct labels of up to 100 characters."
                )
            if not isinstance(color, str) or (
                color and not re.fullmatch(r"#[0-9a-fA-F]{6}", color)
            ):
                raise ValueError("Choose a valid six-digit color.")
            labels.add(text.strip().casefold())
            cleaned.append({"label": text.strip(), "color": color})
        result.append(
            dict(
                id=qid,
                label=label.strip(),
                kind=kind,
                required=item.get("required") is True,
                photo=photo,
                alt=alt.strip(),
                options=cleaned,
            )
        )
    return result


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(auth_settings())
    app.config.update(
        SECRET_KEY=os.getenv("SURVEY_SECRET_KEY"),
        AUTH_MODE="oidc",
        ORIGIN=os.getenv("SURVEY_ORIGIN", "https://survey.inflectionarchitectures.com"),
        DATABASE_PATH=os.getenv("SURVEY_DATABASE_PATH", "/data/survey.sqlite3"),
        SESSION_COOKIE_NAME="__Host-ia-survey",
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
        MAX_CONTENT_LENGTH=9 * 1024 * 1024,
        MAX_FORM_MEMORY_SIZE=256 * 1024,
    )
    if config:
        app.config.update(config)
    if len(app.config["SECRET_KEY"] or "") < 32 or app.config["AUTH_MODE"] != "oidc":
        raise RuntimeError(
            "Survey requires a random SURVEY_SECRET_KEY and central OIDC authentication."
        )
    origin = urlsplit(app.config["ORIGIN"])
    if (
        not origin.hostname
        or origin.path
        or origin.query
        or origin.fragment
        or origin.username
        or (origin.scheme != "https" and not app.testing)
    ):
        raise RuntimeError("SURVEY_ORIGIN must be an HTTPS origin without a path.")
    app.config["TRUSTED_HOSTS"] = [origin.hostname, "localhost", "127.0.0.1"]
    database = Path(app.config["DATABASE_PATH"])
    database.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(database)) as conn:
        conn.executescript(Path(__file__).with_name("schema.sql").read_text())
    database.chmod(0o600)
    signer = URLSafeTimedSerializer(app.secret_key, salt="survey-response")

    def db():
        if "db" not in g:
            g.db = sqlite3.connect(database, timeout=20)
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys=ON")
        return g.db

    @app.teardown_appcontext
    def close(_error):
        if conn := g.pop("db", None):
            conn.close()

    def csrf():
        if "csrf" not in session:
            session["csrf"] = secrets.token_urlsafe(32)
        return session["csrf"]

    app.jinja_env.globals.update(csrf_token=csrf, kinds=KINDS)
    app.jinja_env.filters["date"] = lambda value: datetime.fromtimestamp(
        value, ZoneInfo("America/Denver")
    ).strftime("%b %d, %Y · %H:%M")

    @app.before_request
    def protect():
        if request.path == "/health":
            return None
        if request.host != origin.netloc:
            abort(404)
        if request.method == "POST":
            source = request.headers.get("Origin")
            if request.headers.get("Sec-Fetch-Site") == "cross-site" or (
                source and source != app.config["ORIGIN"]
            ):
                abort(403)
            token = request.headers.get("X-CSRF-Token") or request.form.get("csrf", "")
            if not hmac.compare_digest(
                token.encode(), session.get("csrf", "invalid").encode()
            ):
                abort(403, "Reload the page before submitting again.")
        if request.path.startswith("/admin"):
            return app.extensions["platform_auth"].require(
                "survey:read", *(["survey:write"] if request.method == "POST" else [])
            )

    @app.after_request
    def headers(response):
        response.headers.update(
            {
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "Referrer-Policy": "same-origin",
                "X-Robots-Tag": "noindex, nofollow",
                "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; base-uri 'none'; frame-ancestors 'none'; form-action 'self'",
            }
        )
        if not app.testing:
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        return response

    def survey(sid=None, token=None):
        row = (
            db()
            .execute(
                "SELECT * FROM surveys WHERE " + ("id=?" if sid else "token=?"),
                (sid or token,),
            )
            .fetchone()
        )
        if not row:
            abort(404)
        return dict(row, questions=json.loads(row["questions"]))

    def text(data, key, limit, required=True):
        value = data.get(key, "")
        if (
            not isinstance(value, str)
            or len(value) > limit
            or (required and not value.strip())
        ):
            raise ValueError(
                f'Complete {key.replace("_", " ")} (maximum {limit} characters).'
            )
        return value.strip()

    def url(s):
        return app.config["ORIGIN"] + "/s/" + s["token"]

    @app.get("/health")
    def health():
        db().execute("SELECT 1")
        return {"status": "ok"}

    @app.get("/")
    @app.get("/login")
    def login():
        return render_template("login.html", title="Product surveys")

    @app.get("/admin")
    def dashboard():
        rows = (
            db()
            .execute(
                "SELECT s.*, (SELECT COUNT(*) FROM responses r WHERE r.survey_id=s.id) AS count FROM surveys s ORDER BY created_at DESC"
            )
            .fetchall()
        )
        return render_template("dashboard.html", title="Surveys", surveys=rows)

    @app.post("/admin/new")
    def new():
        sid = secrets.token_urlsafe(16)
        with db():
            db().execute(
                "INSERT INTO surveys(id,token,title,description,thank_you,created_at) VALUES(?,?,?,?,?,?)",
                (
                    sid,
                    secrets.token_urlsafe(24),
                    "Untitled product survey",
                    "",
                    "Thanks for helping shape what comes next!",
                    int(time.time()),
                ),
            )
        return redirect(url_for("editor", sid=sid))

    @app.route("/admin/surveys/<sid>/edit", methods=["GET", "POST"])
    def editor(sid):
        s = survey(sid)
        if request.method == "GET":
            return render_template("editor.html", title="Survey builder", survey=s)
        if s["published_at"] is not None:
            abort(
                409,
                "Published questions are locked to keep results comparable. Duplicate this survey to make changes.",
            )
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            abort(400, "Invalid survey data.")
        try:
            title, description, thanks = (
                text(data, "title", 160),
                text(data, "description", 2000, False),
                text(data, "thank_you", 600),
            )
            photos = {
                row[0]
                for row in db().execute(
                    "SELECT id FROM photos WHERE survey_id=?", (sid,)
                )
            }
            questions = validate_questions(data.get("questions"), photos)
            revision = int(data.get("revision", -1))
        except (ValueError, TypeError) as exc:
            abort(400, str(exc))
        with db():
            changed = (
                db()
                .execute(
                    "UPDATE surveys SET title=?,description=?,thank_you=?,questions=?,revision=revision+1 WHERE id=? AND revision=? AND published_at IS NULL",
                    (title, description, thanks, json.dumps(questions), sid, revision),
                )
                .rowcount
            )
        if not changed:
            abort(409, "This survey changed in another tab. Reload before editing.")
        return jsonify(revision=revision + 1)

    @app.post("/admin/surveys/<sid>/photos")
    def upload(sid):
        s = survey(sid)
        if s["published_at"] is not None:
            abort(409, "Published photos are locked.")
        file = request.files.get("photo")
        if not file:
            abort(400, "Choose a JPEG, PNG or WebP image.")
        raw = file.read(8 * 1024 * 1024 + 1)
        if len(raw) > 8 * 1024 * 1024:
            abort(413, "Photos must be 8 MB or smaller.")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                im = Image.open(io.BytesIO(raw))
                if (
                    im.format not in ("JPEG", "PNG", "WEBP")
                    or im.width * im.height > 20_000_000
                ):
                    raise ValueError()
                im = ImageOps.exif_transpose(im)
                im.thumbnail((1600, 1600))
                # Re-encode pixels only: strip EXIF, GPS and other uploaded metadata.
                im = im.convert("RGB")
                output = io.BytesIO()
                im.save(output, format="JPEG", quality=88)
        except (
            UnidentifiedImageError,
            OSError,
            ValueError,
            Image.DecompressionBombError,
            Image.DecompressionBombWarning,
        ):
            abort(400, "Use a valid JPEG, PNG or WebP up to 20 megapixels.")
        pid = secrets.token_urlsafe(16)
        with db():
            db().execute("BEGIN IMMEDIATE")
            if (
                db()
                .execute("SELECT published_at FROM surveys WHERE id=?", (sid,))
                .fetchone()[0]
                is not None
            ):
                abort(409)
            if (
                db()
                .execute("SELECT COUNT(*) FROM photos WHERE survey_id=?", (sid,))
                .fetchone()[0]
                >= 40
            ):
                abort(400, "Maximum 40 uploaded photos per survey.")
            db().execute(
                "INSERT INTO photos VALUES(?,?,?)", (pid, sid, output.getvalue())
            )
        return jsonify(id=pid, url=url_for("admin_photo", sid=sid, pid=pid))

    def photo_file(s, pid):
        row = (
            db()
            .execute(
                "SELECT content FROM photos WHERE id=? AND survey_id=?", (pid, s["id"])
            )
            .fetchone()
        )
        if not row:
            abort(404)
        return send_file(io.BytesIO(row[0]), mimetype="image/jpeg")

    @app.get("/admin/surveys/<sid>/photos/<pid>")
    def admin_photo(sid, pid):
        return photo_file(survey(sid), pid)

    @app.get("/s/<token>/photos/<pid>")
    def public_photo(token, pid):
        s = survey(token=token)
        if s["state"] != "open" or pid not in {q["photo"] for q in s["questions"]}:
            abort(404)
        return photo_file(s, pid)

    @app.post("/admin/surveys/<sid>/state")
    def state(sid):
        target = request.form.get("state")
        if target not in ("open", "closed"):
            abort(400)
        with db():
            db().execute("BEGIN IMMEDIATE")
            s = survey(sid)
            if not s["questions"]:
                abort(400, "Save at least one question before publishing.")
            db().execute(
                "UPDATE surveys SET state=?,published_at=COALESCE(published_at,?),revision=revision+1 WHERE id=?",
                (target, int(time.time()), sid),
            )
        flash("Survey is now " + target + ".")
        return redirect(url_for("analytics", sid=sid))

    @app.post("/admin/surveys/<sid>/duplicate")
    def duplicate(sid):
        s = survey(sid)
        new_id = secrets.token_urlsafe(16)
        with db():
            questions = s["questions"]
            for q in questions:
                if q["photo"]:
                    pid = secrets.token_urlsafe(16)
                    q["old_photo"] = q["photo"]
                    q["photo"] = pid
            db().execute(
                "INSERT INTO surveys(id,token,title,description,thank_you,questions,created_at) VALUES(?,?,?,?,?,?,?)",
                (
                    new_id,
                    secrets.token_urlsafe(24),
                    s["title"][:150] + " (copy)",
                    s["description"],
                    s["thank_you"],
                    json.dumps(
                        [
                            {k: v for k, v in q.items() if k != "old_photo"}
                            for q in questions
                        ]
                    ),
                    int(time.time()),
                ),
            )
            for q in questions:
                if q.get("old_photo"):
                    db().execute(
                        "INSERT INTO photos SELECT ?,?,content FROM photos WHERE id=? AND survey_id=?",
                        (q["photo"], new_id, q["old_photo"], sid),
                    )
        return redirect(url_for("editor", sid=new_id))

    @app.get("/admin/surveys/<sid>/preview")
    def preview(sid):
        return render_template(
            "public.html",
            title="Preview",
            survey=survey(sid),
            preview=True,
            answers={},
            errors={},
        )

    @app.get("/admin/surveys/<sid>/qr.<fmt>")
    def qr(sid, fmt):
        s = survey(sid)
        if fmt not in ("png", "svg"):
            abort(404)
        output = io.BytesIO()
        code = qrcode.QRCode(
            error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=12, border=4
        )
        code.add_data(url(s))
        code.make(fit=True)
        image = (
            code.make_image(image_factory=qrcode.image.svg.SvgPathFillImage)
            if fmt == "svg"
            else code.make_image(fill_color="black", back_color="white")
        )
        image.save(output)
        output.seek(0)
        return send_file(
            output,
            mimetype="image/svg+xml" if fmt == "svg" else "image/png",
            as_attachment=request.args.get("download") == "1",
            download_name="survey-" + sid + "." + fmt,
        )

    @app.route("/s/<token>", methods=["GET", "POST"])
    def participate(token):
        s = survey(token=token)
        if s["state"] == "draft":
            abort(404)
        if s["state"] == "closed":
            return (
                render_template(
                    "message.html",
                    title="Survey closed",
                    message="Thanks for your interest. This survey is no longer accepting responses.",
                ),
                410,
            )
        answers, errors = {}, {}
        form_token = request.form.get("response_token", "")
        if request.method == "POST":
            try:
                ticket = signer.loads(form_token, max_age=7200)
                if ticket["survey"] != s["id"] or ticket["browser"] != session.get(
                    "visitor"
                ):
                    raise ValueError()
            except (BadSignature, ValueError, KeyError):
                abort(400, "This form expired. Reload the survey to start again.")
            if (
                db()
                .execute("SELECT 1 FROM responses WHERE nonce=?", (ticket["nonce"],))
                .fetchone()
            ):
                return redirect(url_for("thanks", token=token))
            for q in s["questions"]:
                values = request.form.getlist(q["id"])
                if q["kind"] == "text":
                    value = values[0].strip() if len(values) == 1 else ""
                    if len(value) > 2000:
                        errors[q["id"]] = (
                            "Please keep your answer under 2,000 characters."
                        )
                elif q["kind"] == "multiple":
                    value = list(dict.fromkeys(values))
                    valid = {str(i) for i in range(len(q["options"]))}
                    if any(v not in valid for v in value):
                        errors[q["id"]] = "Choose from the listed options."
                else:
                    value = values[0] if len(values) == 1 else ""
                    valid = {
                        str(i)
                        for i in (
                            range(1, 6)
                            if q["kind"] == "rating"
                            else range(len(q["options"]))
                        )
                    }
                    if values and (len(values) != 1 or value not in valid):
                        errors[q["id"]] = "Choose one of the listed answers."
                if q["required"] and not value:
                    errors[q["id"]] = "Please answer this question."
                answers[q["id"]] = value
            if request.form.get("website"):
                abort(400, "Unable to accept this response.")
            if not errors:
                bucket = hashlib.sha256(session["visitor"].encode()).hexdigest()
                now = int(time.time())
                with db():
                    db().execute("BEGIN IMMEDIATE")
                    if survey(token=token)["state"] != "open":
                        abort(409, "This survey has just closed.")
                    if (
                        db()
                        .execute(
                            "SELECT 1 FROM responses WHERE nonce=?", (ticket["nonce"],)
                        )
                        .fetchone()
                    ):
                        return redirect(url_for("thanks", token=token))
                    db().execute(
                        "DELETE FROM attempts WHERE created_at<?", (now - 3600,)
                    )
                    if (
                        db()
                        .execute(
                            "SELECT COUNT(*) FROM attempts WHERE bucket=?", (bucket,)
                        )
                        .fetchone()[0]
                        >= 20
                        or db().execute("SELECT COUNT(*) FROM attempts").fetchone()[0]
                        >= 2000
                    ):
                        abort(429, "Too many submissions. Please try again later.")
                    db().execute("INSERT INTO attempts VALUES(?,?)", (bucket, now))
                    db().execute(
                        "INSERT INTO responses VALUES(?,?,?,?,?)",
                        (
                            secrets.token_urlsafe(16),
                            s["id"],
                            ticket["nonce"],
                            json.dumps(answers),
                            now,
                        ),
                    )
                return redirect(url_for("thanks", token=token))
        if not form_token or request.method == "GET":
            session.setdefault("visitor", secrets.token_urlsafe(24))
            form_token = signer.dumps(
                {
                    "survey": s["id"],
                    "nonce": secrets.token_urlsafe(24),
                    "browser": session["visitor"],
                }
            )
        return render_template(
            "public.html",
            title=s["title"],
            survey=s,
            preview=False,
            answers=answers,
            errors=errors,
            response_token=form_token,
        ), (422 if errors else 200)

    @app.get("/s/<token>/thanks")
    def thanks(token):
        s = survey(token=token)
        if s["state"] == "draft":
            abort(404)
        return render_template(
            "message.html", title="Thank you", message=s["thank_you"]
        )

    def results(s):
        rows = (
            db()
            .execute(
                "SELECT * FROM responses WHERE survey_id=? ORDER BY created_at DESC",
                (s["id"],),
            )
            .fetchall()
        )
        return [dict(row, answers=json.loads(row["answers"])) for row in rows]

    @app.get("/admin/surveys/<sid>")
    def analytics(sid):
        s = survey(sid)
        rows = results(s)
        stats = []
        for q in s["questions"]:
            values = [
                r["answers"].get(q["id"])
                for r in rows
                if r["answers"].get(q["id"]) not in (None, "", [])
            ]
            counts = Counter(
                v
                for value in values
                for v in (value if isinstance(value, list) else [value])
            )
            options = (
                [{"label": str(i), "color": ""} for i in range(1, 6)]
                if q["kind"] == "rating"
                else q["options"]
            )
            stats.append(
                dict(
                    question=q,
                    answered=len(values),
                    skipped=len(rows) - len(values),
                    options=[
                        dict(
                            option,
                            count=counts[str(i + 1 if q["kind"] == "rating" else i)],
                            percent=(
                                round(
                                    100
                                    * counts[str(i + 1 if q["kind"] == "rating" else i)]
                                    / len(values),
                                    1,
                                )
                                if values
                                else 0
                            ),
                        )
                        for i, option in enumerate(options)
                    ],
                    average=(
                        round(sum(int(v) for v in values) / len(values), 2)
                        if values and q["kind"] == "rating"
                        else None
                    ),
                    written=(
                        [
                            {"text": r["answers"][q["id"]], "at": r["created_at"]}
                            for r in rows
                            if r["answers"].get(q["id"])
                        ]
                        if q["kind"] == "text"
                        else []
                    ),
                )
            )
        daily = Counter(
            datetime.fromtimestamp(r["created_at"], ZoneInfo("America/Denver"))
            .date()
            .isoformat()
            for r in rows
        )
        return render_template(
            "analytics.html",
            title=s["title"],
            survey=s,
            stats=stats,
            total=len(rows),
            daily=sorted(daily.items()),
            public_url=url(s),
        )

    @app.get("/admin/surveys/<sid>/export.csv")
    def export(sid):
        s = survey(sid)
        output = io.StringIO()
        writer = csv.writer(output)

        def safe(v):
            v = str(v)
            return (
                "'" + v
                if v.lstrip().startswith(("=", "+", "-", "@"))
                or v.startswith(("\t", "\r", "\n"))
                else v
            )

        writer.writerow(
            ["Response ID", "Submitted (UTC)"]
            + [safe(q["label"]) for q in s["questions"]]
        )
        for r in results(s):
            values = []
            for q in s["questions"]:
                value = r["answers"].get(q["id"], "")
                if q["kind"] in ("single", "multiple") and value not in ("", []):
                    value = "; ".join(
                        q["options"][int(v)]["label"]
                        for v in (value if isinstance(value, list) else [value])
                    )
                values.append(safe(value))
            writer.writerow(
                [
                    r["id"],
                    datetime.fromtimestamp(
                        r["created_at"], ZoneInfo("UTC")
                    ).isoformat(),
                ]
                + values
            )
        return send_file(
            io.BytesIO(output.getvalue().encode("utf-8-sig")),
            mimetype="text/csv",
            as_attachment=True,
            download_name="survey-" + sid + ".csv",
        )

    @app.errorhandler(400)
    @app.errorhandler(401)
    @app.errorhandler(403)
    @app.errorhandler(404)
    @app.errorhandler(409)
    @app.errorhandler(413)
    @app.errorhandler(422)
    @app.errorhandler(429)
    @app.errorhandler(503)
    def error(exc):
        if isinstance(exc, SecurityError):
            return "Invalid host.", 400
        if request.is_json or request.path.endswith("/photos"):
            return jsonify(error=exc.description), exc.code
        return (
            render_template(
                "message.html", title="Request not completed", message=exc.description
            ),
            exc.code,
        )

    init_auth(app, app.config["ORIGIN"], "/admin", "owner")
    return app
