# iA Time — owner workspace

Private CRM, time tracking, client work reports, documents, and calendar at `https://time.inflectionarchitectures.com`. The marketing site and feedback service remain separate. This service uses the same Flask/SQLite stack and brand artwork as the existing owner portal.

## Working in the app

1. Add a client, contact information, hourly rate, color, and internal relationship notes.
2. Choose an active client on Overview and clock in. The server stores the start timestamp and a snapshot of that client's rate. Refreshing, navigating, signing out, or closing the browser does not stop the timer.
3. Clock out to stop time immediately. Fill in the required session summary and work completed/deliverables, with optional next steps and private notes. The session remains an unfinished draft until saved. Only one running or unfinished session is allowed, including across tabs and workers.
4. Open a client's report to select a date range, print/save PDF, or download CSV. Reports include completed sessions only, use the workspace timezone, and select sessions by start date. They exclude client relationship notes, internal session notes, and uploaded documents. Reports are owner-authenticated; export and send the resulting file yourself. There is no public share link or automatic client email.
5. Use the calendar for calls, focus time, deadlines, and multi-day time off. Click a day to prefill dates, or edit an event by opening it. The end is exclusive (e.g. Friday midnight through Monday midnight covers Friday–Sunday). Mobile includes a scrollable month and a full-width agenda. All times use the explicit workspace timezone, independent of the browser's timezone. Scheduling never starts the timer.
6. Upload agreements and other documents to each client (10 MB each). Downloads require owner login and are served as attachments. Files live inside SQLite, so one consistent database backup includes documents too. Allowed extensions: PDF, DOCX, XLSX, TXT, CSV, PNG, JPG/JPEG. Content is not malware-scanned; these are private owner uploads, not a public upload endpoint.

Estimates use actual elapsed seconds and the captured rate, rounded to cents per session (half up). They are not invoices, tax calculations, or payment records. Editing a client's rate affects future sessions only. The dashboard totals completed sessions started in the current Monday-based week; the live session has its own estimate. Archived clients retain all history and documents and cannot be clocked into until restored. Keep the currency fixed once real work has been recorded; changing the setting does not convert existing amounts.

Calendar DST gaps and ambiguous repeated local times are rejected explicitly; choose an unambiguous time. Timer durations use UTC elapsed time and continue correctly across DST changes. The calendar is local to this app, without Google/Outlook sync, recurrence, invitations, or reminders. Existing work logs can be edited with stale-tab protection; no invoice workflow or manual time adjustment is included in this first version.

## Native server setup (existing Cloudflare host tunnel)

Install into `~/services/ia-time`, keeping runtime state outside the Git checkout:

```sh
mkdir -p ~/services/ia-time
rsync -a --exclude=.env --exclude=.venv --exclude=data --exclude=backups --exclude=__pycache__ timekeeper/ ~/services/ia-time/
cd ~/services/ia-time
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python configure.py
mkdir -p ~/.config/systemd/user
cp systemd/ia-time* ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now ia-time.service ia-time-backup.timer
```

The helper privately asks for your owner login and password and generates a unique session secret. To use your existing login without choosing a second password, copy only `ADMIN_USERNAME` and `ADMIN_PASSWORD_HASH` from the feedback service's private `.env` into this service's `.env` locally. Use a separate `TIME_SECRET_KEY`. Password changes are independent between services; change both hashes to keep them in sync. Hashes must be single-quoted to preserve dollar signs. Restart the service after changes and rotate `TIME_SECRET_KEY` to invalidate existing time-workspace sessions. Never commit `.env`, database files, or credentials.

The included user service listens on **127.0.0.1:8094** and loads `.env`. Enable user lingering if not already enabled (`loginctl show-user "$USER" -p Linger`) so the service starts at boot and stays running after logout.

Add a published application route to the existing Cloudflare Tunnel:

| Hostname | Service | HTTP Host Header override |
| --- | --- | --- |
| `time.inflectionarchitectures.com` | `http://localhost:8094` | Leave unset |

Keep existing hostname routes intact. Public HTTPS is terminated by Cloudflare. No inbound router ports are needed. The app enforces the `time` hostname and owner login; it does not trust client forwarding headers. Exclude this hostname from custom cache-everything rules. Do not serve its database or document files through a static web server.

Verify `curl http://127.0.0.1:8094/health`, sign in over public HTTPS, and test a session and document upload/download. Check the daily backup with `systemctl --user list-timers ia-time-backup.timer`.

## Docker alternative

Run `configure.py`, answer yes to Docker, then:

```sh
docker compose up -d --build
```

The service binds only to `127.0.0.1:8094`, and data persists in the named `time-data` volume. The same host tunnel route works. If the connector runs in Docker, attach it to this Compose network and use `http://timekeeper:8000`. Do not run `docker compose down -v` unless intentionally deleting all data. Use either native or Docker deployment, not both on the same port.

## Backups and recovery

`backup.py` uses SQLite's online backup API and integrity verification, retaining the latest 14 snapshots in the data directory's `backups` subdirectory. Native deployment includes a daily systemd timer. Docker deployments should schedule `docker compose exec -T timekeeper python backup.py` through the host scheduler. Copy snapshots to encrypted off-server storage; local backups alone do not cover server loss.

To restore: stop the app, preserve the current data directory, restore the chosen SQLite snapshot as the configured `TIME_DATABASE_PATH`, remove stale WAL/SHM sidecars from the stopped instance after preserving them, set private ownership/permissions, and restart. Test restoration to a separate instance before relying on it. One database includes clients, documents, events, session histories, and drafts.

## Development and checks

```sh
PYTHONPATH=timekeeper /path/to/venv/bin/python -m unittest discover -s timekeeper/tests -v
```

CI runs the workspace tests, builds its container, and checks startup under a read-only root filesystem. Tests cover authentication, host isolation, CSRF, login throttling, simultaneous clock-ins, timer persistence, idempotent clock-out, captured rates, draft journals, private reports, formula-safe CSV, private uploads, calendar edits, and DST boundaries. Browser verification uses a temporary database and fictional clients; production has no demo records.

Styles use the website's actual logo, Helvetica/Arial typography, black surfaces, and #81f268 primary accent, with teal/lilac/pink/blue calendar categories. Color is accompanied by text labels. Controls support keyboard focus, reduced motion, mobile layouts, and print reports.
