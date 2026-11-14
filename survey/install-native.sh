#!/usr/bin/env bash
# Run as the normal service owner, from any directory. Does not require sudo.
set -euo pipefail
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
survey_dir="$HOME/services/ia-survey"
umask 077
mkdir -p "$survey_dir"
python3 -m venv "$survey_dir/.venv"
"$survey_dir/.venv/bin/pip" install "$repo_dir/platform_auth" -r "$repo_dir/survey/requirements.txt"
# Stop here if identity is unavailable; do not activate an app with fake credentials.
"$survey_dir/.venv/bin/python" "$repo_dir/identity/provision-survey.py" --output "$survey_dir/.env"
cp "$repo_dir/survey/app.py" "$repo_dir/survey/schema.sql" "$repo_dir/survey/backup.py" "$survey_dir/"
cp -R "$repo_dir/survey/templates" "$repo_dir/survey/static" "$survey_dir/"
mkdir -p "$HOME/.config/systemd/user"
cp "$repo_dir"/survey/systemd/* "$HOME/.config/systemd/user/"
# Update the existing access manager's permission catalog.
if [[ -x "$HOME/services/ia-feedback/.venv/bin/pip" ]]; then
  "$HOME/services/ia-feedback/.venv/bin/pip" install "$repo_dir/platform_auth"
  systemctl --user restart ia-feedback.service
fi
systemctl --user daemon-reload
systemctl --user enable --now ia-survey.service ia-survey-backup.timer
systemctl --user restart ia-survey.service
for attempt in $(seq 1 20); do
  if curl --fail --silent http://127.0.0.1:8096/health; then
    printf '\nSurvey service is ready on loopback port 8096. Add the Cloudflare Tunnel route to publish it.\n'
    exit 0
  fi
  sleep 1
done
printf 'Survey health check failed. Inspect: journalctl --user -u ia-survey -n 50\n' >&2
exit 1
