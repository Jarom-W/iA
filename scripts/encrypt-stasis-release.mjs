#!/usr/bin/env node

import { createHash, randomBytes } from "node:crypto";
import {
  access,
  lstat,
  mkdir,
  readFile,
  readdir,
  rename,
  rm,
  writeFile,
} from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  PBKDF2_ITERATIONS,
  encryptBytes,
  encryptJson,
} from "./stasis-envelope.mjs";
import { classifyMcpbFilename } from "./stasis-platforms.mjs";

const METADATA_FILENAME = ".stasis-release.json";
const MANIFEST_FILENAME = "stasis-manifest.json";
const MANIFEST_SCHEMA_VERSION = 1;
const PLATFORM_ORDER = [
  "windows-x64",
  "macos-arm64",
  "macos-x64",
  "linux-x64",
];

export function validatePassphrase(passphrase) {
  if (typeof passphrase !== "string" || passphrase.length < 20) {
    throw new Error("The download passphrase must contain at least 20 characters.");
  }
  if (passphrase.length > 512) {
    throw new Error("The download passphrase is unexpectedly long.");
  }

  const words = passphrase.trim().split(/\s+/).filter(Boolean);
  const isWordPassphrase =
    words.length >= 5 &&
    words.every((word) => word.length >= 3) &&
    new Set(words.map((word) => word.toLowerCase())).size === words.length;
  const characterClasses = [
    /[a-z]/.test(passphrase),
    /[A-Z]/.test(passphrase),
    /[0-9]/.test(passphrase),
    /[^A-Za-z0-9\s]/.test(passphrase),
  ].filter(Boolean).length;
  const isRandomCharacterPassphrase =
    characterClasses >= 3 && new Set(passphrase).size >= 10;

  if (!isWordPassphrase && !isRandomCharacterPassphrase) {
    throw new Error(
      "Use at least five words or a random 20+ character value spanning at least three character classes.",
    );
  }

  const normalized = passphrase.toLowerCase().replace(/[^a-z0-9]/g, "");
  if (
    /(password|passphrase|letmein|qwerty|inflectionarchitectures)/.test(normalized) ||
    /(.{1,4})\1{3,}/.test(normalized) ||
    /(?:012345|123456|abcdef|qwerty)/.test(normalized)
  ) {
    throw new Error("The download passphrase is obviously weak.");
  }
}

function parseArguments(argv) {
  const values = new Map();
  for (let index = 0; index < argv.length; index += 2) {
    const name = argv[index];
    const value = argv[index + 1];
    if (!name?.startsWith("--") || !value) {
      throw new Error(
        "Usage: encrypt-stasis-release.mjs --source <directory> --output <directory>",
      );
    }
    values.set(name, value);
  }
  const sourceDirectory = values.get("--source");
  const outputDirectory = values.get("--output");
  if (!sourceDirectory || !outputDirectory || values.size !== 2) {
    throw new Error(
      "Usage: encrypt-stasis-release.mjs --source <directory> --output <directory>",
    );
  }
  return { sourceDirectory, outputDirectory };
}

function validateReleaseMetadata(value) {
  if (!value || typeof value !== "object") {
    throw new Error("Release metadata is missing or invalid.");
  }
  const { version, publishedAt } = value;
  if (
    typeof version !== "string" ||
    version.length < 1 ||
    version.length > 100 ||
    /[\u0000-\u001f]/.test(version)
  ) {
    throw new Error("Release metadata has an invalid version.");
  }
  if (
    typeof publishedAt !== "string" ||
    !/^\d{4}-\d{2}-\d{2}T/.test(publishedAt) ||
    Number.isNaN(Date.parse(publishedAt))
  ) {
    throw new Error("Release metadata has an invalid publication date.");
  }
  return { version, releaseDate: publishedAt.slice(0, 10) };
}

async function pathExists(target) {
  try {
    await access(target);
    return true;
  } catch {
    return false;
  }
}

async function inspectSourceDirectory(sourceDirectory) {
  const source = path.resolve(sourceDirectory);
  const sourceStat = await lstat(source);
  if (!sourceStat.isDirectory() || sourceStat.isSymbolicLink()) {
    throw new Error("The release source must be a real directory.");
  }

  const entries = await readdir(source, { withFileTypes: true });
  const assets = [];
  const seenPlatforms = new Set();

  for (const entry of entries) {
    if (!entry.isFile()) {
      throw new Error(`Unexpected path in release source: ${entry.name}`);
    }
    if (!entry.name.toLowerCase().endsWith(".mcpb")) {
      continue;
    }

    const platform = classifyMcpbFilename(entry.name);
    if (seenPlatforms.has(platform.id)) {
      throw new Error(`Duplicate release asset for ${platform.label}.`);
    }
    seenPlatforms.add(platform.id);

    const filePath = path.join(source, entry.name);
    const stat = await lstat(filePath);
    if (!stat.isFile() || stat.isSymbolicLink()) {
      throw new Error(`Release asset is not a regular file: ${entry.name}`);
    }
    if (stat.size === 0) {
      throw new Error(`Release asset is empty: ${entry.name}`);
    }
    assets.push({
      sourcePath: filePath,
      filename: entry.name,
      size: stat.size,
      ...platform,
    });
  }

  if (assets.length === 0) {
    throw new Error("No supported .mcpb release assets were found.");
  }

  assets.sort(
    (left, right) =>
      PLATFORM_ORDER.indexOf(left.id) - PLATFORM_ORDER.indexOf(right.id),
  );
  return { source, assets };
}

function validateOutputPath(source, outputDirectory) {
  const output = path.resolve(outputDirectory);
  const filesystemRoot = path.parse(output).root;
  const relativeToSource = path.relative(source, output);
  if (
    output === filesystemRoot ||
    output === source ||
    (!relativeToSource.startsWith("..") && !path.isAbsolute(relativeToSource))
  ) {
    throw new Error("The encrypted output must be outside the plaintext source.");
  }
  return output;
}

export async function buildEncryptedRelease({
  sourceDirectory,
  outputDirectory,
  passphrase,
  iterations = PBKDF2_ITERATIONS,
}) {
  validatePassphrase(passphrase);
  if (!Number.isInteger(iterations) || iterations < 100_000) {
    throw new Error("PBKDF2 iterations must be an integer of at least 100,000.");
  }

  const { source, assets } = await inspectSourceDirectory(sourceDirectory);
  const output = validateOutputPath(source, outputDirectory);
  if (await pathExists(output)) {
    throw new Error("Encrypted output directory already exists.");
  }

  const metadataPath = path.join(source, METADATA_FILENAME);
  const metadata = validateReleaseMetadata(
    JSON.parse(await readFile(metadataPath, "utf8")),
  );
  const temporaryOutput = path.join(
    path.dirname(output),
    `.stasis-encrypted-${randomBytes(12).toString("hex")}`,
  );

  try {
    await mkdir(path.join(temporaryOutput, "assets"), { recursive: true });
    const manifestAssets = [];

    for (const asset of assets) {
      const plaintext = new Uint8Array(await readFile(asset.sourcePath));
      const checksum = createHash("sha256").update(plaintext).digest("hex");
      const payloadName = `${randomBytes(16).toString("hex")}.json`;
      let envelope;
      try {
        envelope = await encryptBytes(plaintext, passphrase, { iterations });
      } finally {
        plaintext.fill(0);
      }
      await writeFile(
        path.join(temporaryOutput, "assets", payloadName),
        `${JSON.stringify(envelope)}\n`,
        { flag: "wx", mode: 0o644 },
      );
      manifestAssets.push({
        platform: asset.id,
        label: asset.label,
        filename: asset.filename,
        size: asset.size,
        sha256: checksum,
        payload: `assets/${payloadName}`,
      });
    }

    const manifest = {
      schemaVersion: MANIFEST_SCHEMA_VERSION,
      release: metadata,
      assets: manifestAssets,
    };
    const manifestEnvelope = await encryptJson(manifest, passphrase, {
      iterations,
    });
    await writeFile(
      path.join(temporaryOutput, MANIFEST_FILENAME),
      `${JSON.stringify(manifestEnvelope)}\n`,
      { flag: "wx", mode: 0o644 },
    );
    await mkdir(path.dirname(output), { recursive: true });
    await rename(temporaryOutput, output);
  } catch (error) {
    await rm(temporaryOutput, { recursive: true, force: true });
    throw error;
  }

  return { assetCount: assets.length, outputDirectory: output };
}

async function main() {
  const { sourceDirectory, outputDirectory } = parseArguments(process.argv.slice(2));
  const passphrase = process.env.STASIS_DOWNLOAD_PASSPHRASE;
  if (!passphrase) {
    throw new Error("STASIS_DOWNLOAD_PASSPHRASE is required.");
  }
  delete process.env.STASIS_DOWNLOAD_PASSPHRASE;
  const result = await buildEncryptedRelease({
    sourceDirectory,
    outputDirectory,
    passphrase,
  });
  console.log(`Encrypted ${result.assetCount} Stasis release asset(s).`);
}

if (process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1])) {
  main().catch((error) => {
    console.error(`Stasis encryption failed: ${error.message}`);
    process.exitCode = 1;
  });
}
