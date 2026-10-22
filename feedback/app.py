"""Client feedback service. Public reads are separated from authenticated admin routes."""
from contextlib import closing
import hashlib
import hmac
import json
import os
import re
import secrets
import smtplib
import sqlite3
import ssl
import time
from datetime import timedelta
from email.message import EmailMessage
from functools import wraps
from pathlib import Path
from urllib.parse import urlsplit

from flask import Flask, abort, flash, g, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.getenv("SECRET_KEY"),
        ADMIN_USERNAME=os.getenv("ADMIN_USERNAME", "jarom"),
        ADMIN_PASSWORD_HASH=os.getenv("ADMIN_PASSWORD_HASH", ""),
        ADMIN_ORIGIN=os.getenv("ADMIN_ORIGIN", "https://admin.inflectionarchitectures.com"),
        FEEDBACK_ORIGIN=os.getenv("FEEDBACK_ORIGIN", "https://feedback.inflectionarchitectures.com"),
        PUBLIC_SITE_ORIGIN=os.getenv("PUBLIC_SITE_ORIGIN", "https://inflectionarchitectures.com"),
        DATABASE_PATH=os.getenv("DATABASE_PATH", "/data/feedback.sqlite3"),
        SESSION_COOKIE_NAME="__Host-ia-admin", SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
        MAX_CONTENT_LENGTH=65536, MAX_FORM_PARTS=50,
        NTFY_URL=os.getenv("NTFY_URL", ""), NTFY_TOPIC=os.getenv("NTFY_TOPIC", ""),
        SMTP_HOST=os.getenv("SMTP_HOST", ""), SMTP_PORT=int(os.getenv("SMTP_PORT", "587")),
        SMTP_USERNAME=os.getenv("SMTP_USERNAME", ""), SMTP_PASSWORD=os.getenv("SMTP_PASSWORD", ""),
        SMTP_FROM=os.getenv("SMTP_FROM", "Inflection Architectures <jarom@inflectionarchitectures.com>"),
        SMTP_TLS=os.getenv("SMTP_TLS", "starttls"),
    )
    if config:
        app.config.update(config)
    if not app.config["SECRET_KEY"] or len(app.config["SECRET_KEY"]) < 32:
        raise RuntimeError("Set SECRET_KEY to a random value of at least 32 characters.")
    if not app.config["ADMIN_PASSWORD_HASH"]:
        raise RuntimeError("Set ADMIN_PASSWORD_HASH before starting the service.")
    for key in ("ADMIN_ORIGIN", "FEEDBACK_ORIGIN", "PUBLIC_SITE_ORIGIN"):
        value = app.config[key].rstrip("/")
        parsed = urlsplit(value)
        if not parsed.hostname or parsed.path or parsed.query or parsed.fragment or parsed.username or parsed.scheme not in ("https", "http"):
            raise RuntimeError(f"{key} must be an origin without a path.")
        if not app.testing and parsed.scheme != "https":
            raise RuntimeError(f"{key} must use HTTPS.")
        app.config[key] = value
    app.config["TRUSTED_HOSTS"] = list({urlsplit(app.config[key]).hostname for key in ("ADMIN_ORIGIN", "FEEDBACK_ORIGIN")}) + ["127.0.0.1", "localhost"]
    database = Path(app.config["DATABASE_PATH"])
    database.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(database)) as conn:
        conn.executescript(Path(__file__).with_name("schema.sql").read_text())
        # Preserve existing responses; historic feedback has no inferred rating.
        conn.execute("BEGIN IMMEDIATE")
        if "rating" not in {row[1] for row in conn.execute("PRAGMA table_info(responses)")}:
            conn.execute("ALTER TABLE responses ADD COLUMN rating INTEGER CHECK(rating BETWEEN 1 AND 5)")
        conn.commit()
    if not app.testing:
        database.chmod(0o600)

    def db():
        if "db" not in g:
            g.db = sqlite3.connect(database, timeout=10)
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys=ON")
        return g.db

    @app.teardown_appcontext
    def close_db(_error):
        connection = g.pop("db", None)
        if connection:
            connection.close()

    def csrf():
        if "csrf" not in session:
            session["csrf"] = secrets.token_urlsafe(32)
        return session["csrf"]

    app.jinja_env.globals["csrf_token"] = csrf

    @app.before_request
    def protect_requests():
        if request.path.startswith("/admin"):
            if request.host != urlsplit(app.config["ADMIN_ORIGIN"]).netloc:
                abort(404)
            if request.method == "POST":
                origin = request.headers.get("Origin")
                if request.headers.get("Sec-Fetch-Site") == "cross-site" or (origin and origin not in (app.config["ADMIN_ORIGIN"], "null")):
                    abort(403)
                if not hmac.compare_digest(request.form.get("csrf", ""), session.get("csrf", "invalid")):
                    abort(403, "Your session expired. Reload the page and try again.")
        elif request.path.startswith(("/f/", "/api/")):
            if request.host != urlsplit(app.config["FEEDBACK_ORIGIN"]).netloc:
                abort(404)

    @app.after_request
    def headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
        response.headers["X-Robots-Tag"] = "noindex, nofollow"
        response.headers["Cache-Control"] = "no-store"
        if not app.testing:
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        if request.path == "/api/testimonials":
            response.headers["Access-Control-Allow-Origin"] = app.config["PUBLIC_SITE_ORIGIN"]
        return response

    def admin_required(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            if not session.get("admin"):
                return redirect(url_for("login"))
            return fn(*args, **kwargs)
        return wrapped

    def field(name, limit, required=False):
        value = request.form.get(name, "").strip()
        if len(value) > limit or (required and not value):
            raise ValueError(f"Please complete {name.replace('_', ' ')} (maximum {limit} characters).")
        return value

    def row_or_404(sql, params):
        row = db().execute(sql, params).fetchone()
        if row is None:
            abort(404)
        return row

    def invite_record(token):
        digest = hashlib.sha256(token.encode()).hexdigest()
        invite = row_or_404("SELECT * FROM invitations WHERE token_hash=?", (digest,))
        if invite["revoked"] or invite["expires_at"] < time.time():
            abort(410, "This invitation has expired. Please ask Jarom for a new link.")
        return invite

    def send_invitation(recipient, name, title, token):
        if not app.config["SMTP_HOST"]:
            raise RuntimeError("Email delivery is not configured.")
        message = EmailMessage()
        message["From"] = app.config["SMTP_FROM"]
        message["To"] = recipient
        message["Subject"] = "Your experience with Inflection Architectures"
        message.set_content(f"Hi {name},\n\nI'd appreciate your feedback on our work together.\n\n{title}\n{app.config['FEEDBACK_ORIGIN']}/?form={token}\n\nThis personal link expires in 30 days and accepts one response. You can choose whether your testimonial may appear on our website.\n\nThank you,\nJarom\nInflection Architectures\n")
        if app.config["SMTP_TLS"] not in ("ssl", "starttls"):
            raise RuntimeError("SMTP_TLS must be ssl or starttls.")
        smtp_type = smtplib.SMTP_SSL if app.config["SMTP_TLS"] == "ssl" else smtplib.SMTP
        kwargs = {"context": ssl.create_default_context()} if smtp_type is smtplib.SMTP_SSL else {}
        with smtp_type(app.config["SMTP_HOST"], app.config["SMTP_PORT"], timeout=20, **kwargs) as smtp:
            if app.config["SMTP_TLS"] == "starttls":
                smtp.starttls(context=ssl.create_default_context())
            if app.config["SMTP_USERNAME"]:
                smtp.login(app.config["SMTP_USERNAME"], app.config["SMTP_PASSWORD"])
            smtp.send_message(message)

    @app.get("/health")
    def health():
        db().execute("SELECT 1")
        return {"status": "ok"}

    @app.route("/", methods=["GET", "POST"])
    def index():
        if request.host == urlsplit(app.config["ADMIN_ORIGIN"]).netloc:
            return redirect(url_for("dashboard"))
        if request.host == urlsplit(app.config["FEEDBACK_ORIGIN"]).netloc and request.args.get("form"):
            return feedback(request.args["form"])
        return render_template("message.html", title="Your experience matters.", message="Open the personal link Jarom shared with you to leave your feedback.")

    @app.route("/admin/login", methods=["GET", "POST"])
    def login():
        error = None
        if request.method == "POST":
            now = int(time.time())
            # Shared DB-backed limit remains effective across workers; do not trust proxy IP headers.
            with db():
                db().execute("BEGIN IMMEDIATE")
                db().execute("DELETE FROM login_attempts WHERE created_at < ?", (now - 300,))
                if db().execute("SELECT count(*) FROM login_attempts").fetchone()[0] >= 10:
                    abort(429, "Too many sign-in attempts. Try again in five minutes.")
                db().execute("INSERT INTO login_attempts VALUES (?)", (now,))
            password_ok = check_password_hash(app.config["ADMIN_PASSWORD_HASH"], request.form.get("password", ""))
            username_ok = hmac.compare_digest(request.form.get("username", "").encode(), app.config["ADMIN_USERNAME"].encode())
            if password_ok and username_ok:
                session.clear()
                session["admin"] = True
                session.permanent = True
                csrf()
                return redirect(url_for("dashboard"))
            error = "That login or password was not accepted."
        return render_template("login.html", error=error)

    @app.post("/admin/logout")
    @admin_required
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.get("/admin")
    @admin_required
    def dashboard():
        return render_template("dashboard.html", forms=db().execute("SELECT * FROM forms ORDER BY created_at DESC").fetchall(),
            responses=db().execute("SELECT r.*, f.title, f.service, i.email FROM responses r JOIN invitations i ON i.id=r.invitation_id JOIN forms f ON f.id=i.form_id ORDER BY r.created_at DESC").fetchall())

    @app.get("/admin/queue")
    @admin_required
    def approval_queue():
        responses = db().execute("SELECT r.*, f.title FROM responses r JOIN invitations i ON i.id=r.invitation_id JOIN forms f ON f.id=i.form_id WHERE r.status='pending' ORDER BY r.created_at ASC").fetchall()
        return render_template("queue.html", responses=responses)

    @app.route("/admin/forms/new", methods=["GET", "POST"])
    @admin_required
    def new_form():
        error = None
        if request.method == "POST":
            try:
                title, introduction, service = field("title", 120, True), field("introduction", 1000), field("service", 80)
                questions = [line.strip() for line in field("questions", 2500).splitlines() if line.strip()]
                if len(questions) > 8 or len(set(questions)) != len(questions) or any(len(q) > 240 for q in questions):
                    raise ValueError("Use up to eight distinct questions, each no more than 240 characters.")
                form_id = secrets.token_hex(12)
                with db():
                    db().execute("INSERT INTO forms VALUES (?,?,?,?,?,?,?)", (form_id, title, introduction, service, json.dumps(questions), 0, int(time.time())))
                return redirect(url_for("form_detail", form_id=form_id))
            except ValueError as exc:
                error = str(exc)
        return render_template("new-form.html", error=error)

    @app.get("/admin/forms/<form_id>")
    @admin_required
    def form_detail(form_id):
        form = row_or_404("SELECT * FROM forms WHERE id=?", (form_id,))
        invitations = db().execute("SELECT i.*, r.id AS response_id FROM invitations i LEFT JOIN responses r ON r.invitation_id=i.id WHERE i.form_id=? ORDER BY i.created_at DESC", (form_id,)).fetchall()
        return render_template("form-detail.html", form=form, questions=json.loads(form["questions"]), invitations=invitations)

    @app.route("/admin/forms/<form_id>/delete", methods=["GET", "POST"])
    @admin_required
    def delete_form(form_id):
        form = row_or_404("SELECT * FROM forms WHERE id=?", (form_id,))
        if request.method == "POST":
            with db():
                db().execute("BEGIN IMMEDIATE")
                db().execute("DELETE FROM responses WHERE invitation_id IN (SELECT id FROM invitations WHERE form_id=?)", (form_id,))
                db().execute("DELETE FROM invitations WHERE form_id=?", (form_id,))
                db().execute("DELETE FROM forms WHERE id=?", (form_id,))
            flash("Form, invitations, and responses deleted.", "success")
            return redirect(url_for("dashboard"))
        counts = db().execute("SELECT count(*) AS invitations, count(r.id) AS responses FROM invitations i LEFT JOIN responses r ON r.invitation_id=i.id WHERE i.form_id=?", (form_id,)).fetchone()
        return render_template("delete.html", kind="form", label=form["title"], counts=counts,
            cancel_url=url_for("form_detail", form_id=form_id))

    @app.post("/admin/forms/<form_id>/invite")
    @admin_required
    def invite(form_id):
        form = row_or_404("SELECT * FROM forms WHERE id=?", (form_id,))
        try:
            delivery = request.form.get("delivery", "email")
            if delivery not in ("email", "link"):
                raise ValueError("Choose a valid delivery method.")
            email, name = field("email", 254, delivery == "email"), field("client_name", 120, True)
            if email and not re.fullmatch(r"[^\s<>@]+@[^\s<>@]+\.[^\s<>@]+", email):
                raise ValueError("Enter a valid client email address.")
        except ValueError as exc:
            flash(str(exc), "error")
            return redirect(url_for("form_detail", form_id=form_id))
        token, invitation_id, now = secrets.token_urlsafe(32), secrets.token_hex(12), int(time.time())
        with db():
            db().execute("INSERT INTO invitations (id,form_id,email,client_name,token_hash,expires_at,created_at) VALUES (?,?,?,?,?,?,?)", (invitation_id, form_id, email, name, hashlib.sha256(token.encode()).hexdigest(), now + 30 * 86400, now))
        if delivery == "link":
            with db():
                db().execute("UPDATE invitations SET mail_status='not_requested' WHERE id=?", (invitation_id,))
            return render_template("invitation-link.html", link=f"{app.config['FEEDBACK_ORIGIN']}/?form={token}", form=form, client_name=name)
        try:
            send_invitation(email, name, form["title"], token)
        except (OSError, smtplib.SMTPException, RuntimeError, ValueError):
            with db():
                db().execute("UPDATE invitations SET mail_status='failed',revoked=1 WHERE id=?", (invitation_id,))
            flash("The invitation was not confirmed sent. Its link has been revoked. Check email settings, then send a new invitation.", "error")
        else:
            with db():
                db().execute("UPDATE invitations SET mail_status='sent' WHERE id=?", (invitation_id,))
            flash("Invitation accepted by the email server. Delivery to the inbox is not yet confirmed.", "success")
        return redirect(url_for("form_detail", form_id=form_id))

    @app.post("/admin/invitations/<invitation_id>/revoke")
    @admin_required
    def revoke(invitation_id):
        invite = row_or_404("SELECT * FROM invitations WHERE id=?", (invitation_id,))
        with db():
            db().execute("UPDATE invitations SET revoked=1 WHERE id=?", (invitation_id,))
        flash("Invitation revoked.", "success")
        return redirect(url_for("form_detail", form_id=invite["form_id"]))

    @app.route("/f/<token>", methods=["GET", "POST"])
    def feedback(token):
        invite = invite_record(token)
        form = row_or_404("SELECT * FROM forms WHERE id=?", (invite["form_id"],))
        if db().execute("SELECT id FROM responses WHERE invitation_id=?", (invite["id"],)).fetchone():
            return render_template("message.html", title="Thank you for sharing.", message="Your response has been received. This invitation can only be used once.")
        questions, error = json.loads(form["questions"]), None
        if request.method == "POST":
            origin = request.headers.get("Origin")
            if request.headers.get("Sec-Fetch-Site") == "cross-site" or (origin and origin not in (app.config["FEEDBACK_ORIGIN"], "null")):
                abort(403)
            try:
                name, company, role, quote = field("name", 120, True), field("company", 120), field("role", 120), field("quote", 1500, True)
                rating_text = request.form.get("rating", "")
                if rating_text not in ("1", "2", "3", "4", "5"):
                    raise ValueError("Choose a star rating from 1 to 5.")
                rating = int(rating_text)
                answers = {q: field(f"answer_{i}", 2000) for i, q in enumerate(questions)}
                consent = request.form.get("consent") == "yes"
                status = "pending" if consent else "private"
                now = int(time.time())
                response_id = secrets.token_hex(12)
                with db():
                    db().execute("BEGIN IMMEDIATE")
                    # Recheck expiry/revocation inside the write transaction.
                    current = invite_record(token)
                    db().execute("INSERT INTO responses (id,invitation_id,name,company,role,quote,answers,consent,status,created_at,published_at,rating) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (response_id, current["id"], name, company, role, quote, json.dumps(answers), int(consent), status, now, None, rating))
                    if app.config["NTFY_URL"] and app.config["NTFY_TOPIC"]:
                        db().execute("INSERT INTO notification_outbox (response_id) VALUES (?)", (response_id,))
                return redirect(url_for("feedback", token=token), code=303)
            except ValueError as exc:
                error = str(exc)
            except sqlite3.IntegrityError:
                return redirect(url_for("feedback", token=token), code=303)
        return render_template("feedback.html", form=form, invite=invite, questions=questions, error=error)

    @app.get("/admin/responses/<response_id>")
    @admin_required
    def response_detail(response_id):
        response = row_or_404("SELECT r.*, f.title, f.service, i.email FROM responses r JOIN invitations i ON i.id=r.invitation_id JOIN forms f ON f.id=i.form_id WHERE r.id=?", (response_id,))
        return render_template("response.html", response=response, answers=json.loads(response["answers"]))

    @app.route("/admin/responses/<response_id>/delete", methods=["GET", "POST"])
    @admin_required
    def delete_response(response_id):
        response = row_or_404("SELECT * FROM responses WHERE id=?", (response_id,))
        if request.method == "POST":
            with db():
                db().execute("BEGIN IMMEDIATE")
                # Keep the consumed invitation unusable after its response is removed.
                db().execute("UPDATE invitations SET revoked=1 WHERE id=?", (response["invitation_id"],))
                db().execute("DELETE FROM responses WHERE id=?", (response_id,))
            flash("Client response deleted and its invitation revoked.", "success")
            return redirect(url_for("dashboard"))
        return render_template("delete.html", kind="response", label=response["name"],
            cancel_url=url_for("response_detail", response_id=response_id))

    @app.post("/admin/responses/<response_id>/status")
    @admin_required
    def response_status(response_id):
        with db():
            db().execute("BEGIN IMMEDIATE")
            response = row_or_404("SELECT * FROM responses WHERE id=?", (response_id,))
            status = request.form.get("status")
            if status not in ("published", "hidden"):
                abort(400)
            if status == "published" and not response["consent"]:
                abort(403, "This client did not give permission to publish their testimonial.")
            db().execute("UPDATE responses SET status=?,published_at=? WHERE id=?", (status, int(time.time()) if status == "published" else response["published_at"], response_id))
        flash("Testimonial published." if status == "published" else "Testimonial hidden from the website.", "success")
        return redirect(url_for("response_detail", response_id=response_id))

    @app.get("/api/testimonials")
    def testimonials():
        rows = db().execute("SELECT r.id,r.name,r.company,r.role,r.quote,r.rating,f.service FROM responses r JOIN invitations i ON i.id=r.invitation_id JOIN forms f ON f.id=i.form_id WHERE r.status='published' AND r.consent=1 ORDER BY r.published_at DESC LIMIT 12").fetchall()
        return jsonify(testimonials=[dict(row) for row in rows])

    @app.errorhandler(400)
    @app.errorhandler(403)
    @app.errorhandler(404)
    @app.errorhandler(410)
    @app.errorhandler(413)
    @app.errorhandler(429)
    def request_error(error):
        return render_template("message.html", title="We couldn’t open that request.", message=error.description), error.code

    return app
