import { mkdtemp, mkdir, readFile, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import { rm } from "node:fs/promises";
import {
  buildEncryptedRelease,
  validatePassphrase,
} from "../../scripts/encrypt-stasis-release.mjs";
import { checkPagesArtifact } from "../../scripts/check-pages-artifact.mjs";
import {
  decryptEnvelopeJson,
  validateManifest,
} from "../src/downloads/crypto";

const passphrase = "alpine museum velvet transit candle river";
const temporaryDirectories: string[] = [];

async function temporaryDirectory() {
  const directory = await mkdtemp(path.join(os.tmpdir(), "stasis-download-test-"));
  temporaryDirectories.push(directory);
  return directory;
}

async function createSource(directory: string, filenames: string[]) {
  const source = path.join(directory, "source");
  await mkdir(source);
  await writeFile(
    path.join(source, ".stasis-release.json"),
    JSON.stringify({ version: "v1.4.2", publishedAt: "2026-08-12T12:00:00Z" }),
  );
  for (const filename of filenames) {
    await writeFile(
      path.join(source, filename),
      `STASIS_PLAINTEXT_FIXTURE:${filename}`,
    );
  }
  return source;
}

afterEach(async () => {
  await Promise.all(
    temporaryDirectories.splice(0).map((directory) =>
      rm(directory, { recursive: true, force: true }),
    ),
  );
});

describe("Stasis release encryption tool", () => {
  it("encrypts the release manifest and assets without plaintext output", async () => {
    const root = await temporaryDirectory();
    const source = await createSource(root, [
      "stasis-windows-x64.mcpb",
      "stasis-darwin-arm64.mcpb",
      "stasis-darwin-x64.mcpb",
      "stasis-linux-amd64.mcpb",
    ]);
    const downloadsDirectory = path.join(root, "pages", "downloads");
    await mkdir(downloadsDirectory, { recursive: true });
    await writeFile(path.join(downloadsDirectory, "index.html"), "<p>download page</p>");
    const output = path.join(downloadsDirectory, "releases");

    await buildEncryptedRelease({
      sourceDirectory: source,
      outputDirectory: output,
      passphrase,
      iterations: 100_000,
    });

    const publicManifest = await readFile(
      path.join(output, "stasis-manifest.json"),
      "utf8",
    );
    expect(publicManifest).not.toContain("v1.4.2");
    expect(publicManifest).not.toContain("windows");
    expect(publicManifest).not.toContain(".mcpb");

    const manifest = validateManifest(
      await decryptEnvelopeJson(JSON.parse(publicManifest), passphrase),
    );
    expect(manifest.release).toEqual({ version: "v1.4.2", releaseDate: "2026-08-12" });
    expect(manifest.assets.map((asset) => asset.label)).toEqual([
      "Windows x64",
      "macOS Apple silicon",
      "macOS Intel",
      "Linux x64",
    ]);
    expect(manifest.assets[0].sha256).toMatch(/^[a-f0-9]{64}$/);
    await expect(checkPagesArtifact(path.join(root, "pages"))).resolves.toEqual({
      fileCount: 6,
    });

    const outputText = await Promise.all(
      ["stasis-manifest.json", ...manifest.assets.map((asset) => asset.payload)].map(
        (filename) => readFile(path.join(output, filename), "utf8"),
      ),
    );
    expect(outputText.join("\n")).not.toContain("STASIS_PLAINTEXT_FIXTURE");
  });

  it("rejects missing and obviously weak passphrases", () => {
    expect(() => validatePassphrase("")).toThrow();
    expect(() => validatePassphrase("InflectionArchitectures2026!")).toThrow();
    expect(() => validatePassphrase("password-password-password-123")).toThrow();
  });

  it("fails closed for an empty release", async () => {
    const root = await temporaryDirectory();
    const source = await createSource(root, []);
    await expect(
      buildEncryptedRelease({
        sourceDirectory: source,
        outputDirectory: path.join(root, "output"),
        passphrase,
        iterations: 100_000,
      }),
    ).rejects.toThrow(/No supported/);
  });

  it("rejects an empty MCPB asset", async () => {
    const root = await temporaryDirectory();
    const source = await createSource(root, []);
    await writeFile(path.join(source, "stasis-windows-x64.mcpb"), "");
    await expect(
      buildEncryptedRelease({
        sourceDirectory: source,
        outputDirectory: path.join(root, "output"),
        passphrase,
        iterations: 100_000,
      }),
    ).rejects.toThrow(/empty/);
  });

  it("rejects duplicate platform assets and unexpected paths", async () => {
    const duplicateRoot = await temporaryDirectory();
    const duplicateSource = await createSource(duplicateRoot, [
      "stasis-windows-x64.mcpb",
      "stasis-win32-amd64.mcpb",
    ]);
    await expect(
      buildEncryptedRelease({
        sourceDirectory: duplicateSource,
        outputDirectory: path.join(duplicateRoot, "output"),
        passphrase,
        iterations: 100_000,
      }),
    ).rejects.toThrow(/Duplicate/);

    const nestedRoot = await temporaryDirectory();
    const nestedSource = await createSource(nestedRoot, ["stasis-windows-x64.mcpb"]);
    await mkdir(path.join(nestedSource, "nested"));
    await expect(
      buildEncryptedRelease({
        sourceDirectory: nestedSource,
        outputDirectory: path.join(nestedRoot, "output"),
        passphrase,
        iterations: 100_000,
      }),
    ).rejects.toThrow(/Unexpected path/);
  });

  it("detects configured secrets and raw MCPB files in an artifact", async () => {
    const root = await temporaryDirectory();
    await writeFile(path.join(root, "bundle.js"), "client-secret-value");
    await expect(
      checkPagesArtifact(root, { STASIS_RELEASES_TOKEN: "client-secret-value" }),
    ).rejects.toThrow(/configured secret/);

    const secondRoot = await temporaryDirectory();
    await writeFile(path.join(secondRoot, "stasis.mcpb"), "fixture");
    await expect(checkPagesArtifact(secondRoot, {})).rejects.toThrow(/plaintext/);
  });
});
