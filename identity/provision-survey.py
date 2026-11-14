"""Add the Survey client to an existing realm without reimporting or resetting accounts.
Run with the platform virtualenv. Reads private bootstrap credentials; never prints them.
"""

import argparse
import os
from pathlib import Path
import secrets
import shlex
import requests


def read_env(path):
    return {
        k: shlex.split(v)[0]
        for line in path.read_text().splitlines()
        if "=" in line and not line.startswith("#")
        for k, _, v in [line.partition("=")]
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    admin = read_env(root / "secrets/admin-oidc.env")
    bootstrap = read_env(root / ".env")
    base = "http://127.0.0.1:8098"
    response = requests.post(
        base + "/realms/master/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": bootstrap["KC_BOOTSTRAP_ADMIN_USERNAME"],
            "password": bootstrap["KC_BOOTSTRAP_ADMIN_PASSWORD"],
        },
        timeout=15,
    )
    if not response.ok:
        raise SystemExit(
            "Bootstrap administration is unavailable. Use a local Keycloak administrator to create the ia-survey client as documented. No credentials were displayed."
        )
    headers = {"Authorization": "Bearer " + response.json()["access_token"]}

    def api(method, path, data=None, params=None):
        r = requests.request(
            method,
            base + "/admin/realms/inflection" + path,
            json=data,
            params=params,
            headers=headers,
            timeout=15,
        )
        if not r.ok:
            raise RuntimeError(
                f"Identity setup failed: {method} {path} HTTP {r.status_code}. Safe to retry; existing accounts were not reset."
            )
        return r.json() if r.content else None

    roles = []
    existing = {r["name"]: r for r in api("GET", "/roles")}
    for name in ("survey:read", "survey:write"):
        if name not in existing:
            api("POST", "/roles", {"name": name})
        roles.append(api("GET", "/roles/" + name))
    clients = api("GET", "/clients", params={"clientId": "ia-survey"})
    origin = "https://survey.inflectionarchitectures.com"
    if not clients:
        api(
            "POST",
            "/clients",
            {
                "clientId": "ia-survey",
                "enabled": True,
                "protocol": "openid-connect",
                "publicClient": False,
                "secret": secrets.token_urlsafe(48),
                "standardFlowEnabled": True,
                "implicitFlowEnabled": False,
                "directAccessGrantsEnabled": False,
                "serviceAccountsEnabled": False,
                "fullScopeAllowed": False,
                "redirectUris": [origin + "/auth/callback"],
                "webOrigins": [],
                "attributes": {
                    "pkce.code.challenge.method": "S256",
                    "post.logout.redirect.uris": origin + "/login",
                },
                "protocolMappers": [
                    {
                        "name": "application-audience",
                        "protocol": "openid-connect",
                        "protocolMapper": "oidc-audience-mapper",
                        "config": {
                            "included.client.audience": "ia-survey",
                            "access.token.claim": "true",
                            "introspection.token.claim": "true",
                            "id.token.claim": "false",
                        },
                    }
                ],
            },
        )
        clients = api("GET", "/clients", params={"clientId": "ia-survey"})
    client = clients[0]
    if (
        client.get("redirectUris") != [origin + "/auth/callback"]
        or not client.get("standardFlowEnabled")
        or client.get("implicitFlowEnabled")
        or client.get("serviceAccountsEnabled")
        or client.get("publicClient")
        or client.get("directAccessGrantsEnabled")
        or client.get("fullScopeAllowed")
        or client.get("attributes", {}).get("pkce.code.challenge.method") != "S256"
    ):
        raise SystemExit(
            "Existing ia-survey client differs from the expected secure configuration. Review it before activation."
        )
    scope = next(
        s for s in api("GET", "/client-scopes") if s["name"] == "platform-permissions"
    )
    api("PUT", "/clients/" + client["id"] + "/default-client-scopes/" + scope["id"])
    cid = client["id"]
    api("POST", "/clients/" + cid + "/scope-mappings/realm", roles)
    api("POST", "/users/" + admin["OIDC_OWNER_SUB"] + "/role-mappings/realm", roles)
    secret = api("GET", "/clients/" + cid + "/client-secret")["value"]
    values = {
        "AUTH_MODE": "oidc",
        "OIDC_ISSUER": origin.replace("survey.", "auth.") + "/realms/inflection",
        "OIDC_CLIENT_ID": "ia-survey",
        "OIDC_CLIENT_SECRET": secret,
    }
    output = args.output.expanduser().resolve()
    os.umask(0o077)
    output.parent.mkdir(parents=True, exist_ok=True)
    old = read_env(output) if output.exists() else {}
    old.update(values)
    old.setdefault("SURVEY_SECRET_KEY", secrets.token_urlsafe(48))
    old.setdefault("SURVEY_ORIGIN", origin)
    old.setdefault("SURVEY_DATABASE_PATH", str(output.parent / "data/survey.sqlite3"))
    temp = output.with_suffix(".env.new")
    temp.write_text("".join(k + "=" + shlex.quote(v) + "\n" for k, v in old.items()))
    temp.chmod(0o600)
    temp.replace(output)
    print(
        "Survey client configured, owner permissions granted, and private environment saved. No existing credentials were reset."
    )


if __name__ == "__main__":
    try:
        main()
    except requests.RequestException:
        raise SystemExit(
            "Cannot reach local identity administration on port 8098. Start the existing identity stack, then retry. No credentials were displayed."
        ) from None
