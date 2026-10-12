# Protected Stasis downloads administration

The `/downloads/` page is a static password-gated download experience. The deployment workflow reads the newest published Stasis release from its private repository, encrypts its manifest and MCPB assets on the GitHub Actions runner, and publishes only encrypted envelopes to GitHub Pages.

## One-time GitHub configuration

Open this website repository on GitHub, then go to **Settings → Secrets and variables → Actions**.

Create these repository secrets:

- `STASIS_RELEASES_TOKEN`: a fine-grained personal access token whose repository access is restricted to only the private Stasis repository and whose repository permissions grant **Contents: Read-only**. Do not use a broadly scoped classic PAT. The account that creates the token must be able to read that repository. A GitHub App installation token with short-lived credentials is the recommended future improvement.
- `STASIS_DOWNLOAD_PASSPHRASE`: the shared customer passphrase. Use a genuinely random value—at least 20 random characters with mixed character types, or five or six randomly generated words. A business name plus a year is not adequate. `openssl rand -base64 32` is one suitable way to generate a character-based value; paste the output directly into the GitHub secret and do not put it in a file in this repository.

Create this repository variable:

- `STASIS_RELEASE_REPOSITORY`: the private source repository in exact `OWNER/REPO` form, for example `Jarom-W/Stasis`. Do not include a URL, `.git`, credentials, or whitespace.

Finally, open **Settings → Pages** and set **Build and deployment → Source** to **GitHub Actions**. The workflow uses GitHub's Pages artifact deployment and preserves automatic deployment for every push to `main`.

## Release asset naming

The latest GitHub release must be published, non-draft, and non-prerelease. It must contain at least one non-empty, top-level `.mcpb` asset. Filenames must include one recognized operating-system token and architecture token:

| Download label | Recognized filename tokens |
| --- | --- |
| Windows x64 | `windows`, `win32`, or `win`; and `x64`, `x86_64`, or `amd64` |
| macOS Apple silicon | `macos`, `mac`, `darwin`, or `osx`; and `arm64`, `aarch64`, or `apple-silicon` |
| macOS Intel | `macos`, `mac`, `darwin`, or `osx`; and `x64`, `x86_64`, `amd64`, or `intel` |
| Linux x64 | `linux`; and `x64`, `x86_64`, or `amd64` |

Tokens must be separated by a period, underscore, or hyphen. Examples include `stasis-windows-x64.mcpb` and `stasis-darwin-arm64.mcpb`. There may be no more than one asset for any platform. Linux appears on the page only when a matching Linux asset exists.

## First protected deployment

1. Publish a Stasis GitHub release with the expected MCPB assets. Do not mark it as a draft or prerelease.
2. Add the two repository secrets and one repository variable above.
3. Select **GitHub Actions** as this repository's Pages source.
4. Open **Actions → Deploy protected Stasis downloads → Run workflow**, select `main`, and choose **Run workflow**.
5. Wait for both the `build` and `deploy` jobs to succeed. A missing secret, failed private-repository authentication, missing release, bad asset, failed encryption, test failure, or artifact leak check will stop deployment.
6. Visit `https://inflectionarchitectures.com/downloads/` in a private browser window. Confirm that an incorrect passphrase produces only the generic error, the correct passphrase reveals the expected version/date/platforms, and a downloaded file matches the displayed SHA-256 checksum.

The workflow also runs after every push to `main` and daily at 08:17 UTC. Its concurrency setting queues overlapping runs instead of allowing conflicting deployments.

## Rotation and routine operation

To rotate access, replace `STASIS_DOWNLOAD_PASSPHRASE` under **Settings → Secrets and variables → Actions**, then manually run the deployment workflow. All manifest and asset envelopes receive new random salts and IVs on every run, even if the release is unchanged. Verify the old passphrase fails and the new passphrase succeeds after deployment.

The production packager uses AES-256-GCM authenticated encryption and derives a separate key for every envelope with PBKDF2-SHA-256, a fresh 16-byte salt, and 600,000 iterations. The encrypted format is explicitly versioned as `stasis-encrypted-download` version 1. The browser uses the native Web Crypto API; authenticated-decryption failure is the only passphrase check.

For local verification without private credentials, run:

```bash
cd frontend
npm ci
npm run lint
npm test
npm run build
npm run check:artifact
```

Tests generate small temporary MCPB fixtures and do not contain a real Stasis build or production passphrase.

## Troubleshooting release synchronization

- **401 or 403 from the private release request:** verify `STASIS_RELEASES_TOKEN` has not expired or been revoked, belongs to an account with repository access, is restricted to the correct repository, and grants Contents: Read-only. If the organization uses SSO, authorize the token as required.
- **404 from the latest release request:** verify `STASIS_RELEASE_REPOSITORY` uses the correct case and `OWNER/REPO` format, token access includes that repository, and at least one published non-prerelease release exists. GitHub can intentionally return 404 for an unauthorized private repository.
- **No MCPB assets:** publish at least one `.mcpb` asset on the latest eligible release. Assets attached only to a draft or prerelease are intentionally ignored.
- **Unsupported or duplicate platform:** rename assets to the token conventions above and ensure there is only one asset for each platform.
- **Encryption rejects the passphrase:** use at least five words of three or more characters each, or a random 20+ character value containing at least three of lowercase, uppercase, digits, and symbols. The packager also rejects common password terms, repeated patterns, sequences, and the company name.
- **Pages deploy fails after the artifact upload:** confirm the Pages source is GitHub Actions and that the `github-pages` environment does not have an incompatible protection rule.

As an optional future optimization, the private Stasis release workflow can send a `repository_dispatch` event to this website whenever it publishes a release. That can reduce synchronization delay, but it requires another narrowly scoped credential and is not needed: manual runs and the daily schedule work independently today.

## Security limitations

- GitHub Pages itself is public.
- The deployed files are encrypted; access is not authenticated by a server.
- A shared passphrase can be shared with other people.
- Anyone who decrypts an MCPB can redistribute it.
- A weak passphrase is vulnerable to offline guessing because attackers can download the encrypted payloads.
- Rotating the passphrase requires rebuilding and redeploying all encrypted assets.
- Paid access or individually revocable access should eventually move to authenticated server-side authorization with short-lived signed download URLs.

Neither the passphrase nor a passphrase hash is deployed. The page keeps the entered passphrase only in page memory for subsequent asset decryption, clears the input after each attempt, and drops its in-memory reference when the page is hidden or unmounted. It does not write passphrases to storage, cookies, analytics, URLs, logs, or error reports.
