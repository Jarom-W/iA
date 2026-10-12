#!/usr/bin/env node

import { lstat, readFile, readdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const PLAINTEXT_SENTINELS = [
  "STASIS_PLAINTEXT_FIXTURE",
  "github_pat_",
  "ghp_",
  "STASIS_RELEASES_TOKEN",
  "STASIS_DOWNLOAD_PASSPHRASE",
];

async function collectFiles(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    const target = path.join(directory, entry.name);
    if (entry.isSymbolicLink()) {
      throw new Error("The Pages artifact must not contain symbolic links.");
    }
    if (entry.isDirectory()) {
      files.push(...(await collectFiles(target)));
    } else if (entry.isFile()) {
      files.push(target);
    } else {
      throw new Error("The Pages artifact contains an unsupported filesystem entry.");
    }
  }
  return files;
}

export async function checkPagesArtifact(
  directory,
  environment = process.env,
) {
  const artifactDirectory = path.resolve(directory);
  const stat = await lstat(artifactDirectory);
  if (!stat.isDirectory() || stat.isSymbolicLink()) {
    throw new Error("The Pages artifact path must be a real directory.");
  }

  const secretValues = [
    environment.STASIS_RELEASES_TOKEN,
    environment.STASIS_DOWNLOAD_PASSPHRASE,
  ].filter((value) => typeof value === "string" && value.length > 0);
  const files = await collectFiles(artifactDirectory);
  for (const file of files) {
    if (file.toLowerCase().endsWith(".mcpb")) {
      throw new Error("A plaintext .mcpb file is present in the Pages artifact.");
    }
    const contents = await readFile(file);
    const text = contents.toString("utf8");
    if (PLAINTEXT_SENTINELS.some((sentinel) => text.includes(sentinel))) {
      throw new Error("Potential plaintext release data or token material is present.");
    }
    if (secretValues.some((secret) => contents.includes(Buffer.from(secret)))) {
      throw new Error("A configured secret is present in the Pages artifact.");
    }
    if (/https?:\/\/[^\s/:@]+:[^\s/@]+@[^\s/]*github/i.test(text)) {
      throw new Error("A credential-bearing GitHub URL is present in the Pages artifact.");
    }
  }

  return { fileCount: files.length };
}

function parseArguments(argv) {
  if (argv.length !== 2 || argv[0] !== "--directory" || !argv[1]) {
    throw new Error("Usage: check-pages-artifact.mjs --directory <directory>");
  }
  return argv[1];
}

async function main() {
  const directory = parseArguments(process.argv.slice(2));
  const result = await checkPagesArtifact(directory);
  console.log(`Pages artifact security check passed (${result.fileCount} files).`);
}

if (process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1])) {
  main().catch((error) => {
    console.error(`Pages artifact security check failed: ${error.message}`);
    process.exitCode = 1;
  });
}
