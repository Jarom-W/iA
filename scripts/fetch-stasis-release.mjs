#!/usr/bin/env node

import { createWriteStream } from "node:fs";
import { access, lstat, mkdir, rename, rm, writeFile } from "node:fs/promises";
import { Readable } from "node:stream";
import { pipeline } from "node:stream/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { classifyMcpbFilename } from "./stasis-platforms.mjs";

const API_VERSION = "2022-11-28";
const METADATA_FILENAME = ".stasis-release.json";

export function readConfiguration(environment = process.env) {
  const token = environment.STASIS_RELEASES_TOKEN;
  const repository = environment.STASIS_RELEASE_REPOSITORY;
  if (!token) {
    throw new Error("STASIS_RELEASES_TOKEN is required.");
  }
  if (!repository) {
    throw new Error("STASIS_RELEASE_REPOSITORY is required.");
  }
  if (!/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(repository)) {
    throw new Error("STASIS_RELEASE_REPOSITORY must use OWNER/REPO format.");
  }
  return { token, repository };
}

function parseArguments(argv) {
  if (argv.length !== 2 || argv[0] !== "--output" || !argv[1]) {
    throw new Error("Usage: fetch-stasis-release.mjs --output <directory>");
  }
  return path.resolve(argv[1]);
}

function requestHeaders(token, accept = "application/vnd.github+json") {
  return {
    Accept: accept,
    Authorization: `Bearer ${token}`,
    "X-GitHub-Api-Version": API_VERSION,
    "User-Agent": "inflection-architectures-stasis-sync",
  };
}

async function ensureOutputDoesNotExist(outputDirectory) {
  const filesystemRoot = path.parse(outputDirectory).root;
  if (outputDirectory === filesystemRoot) {
    throw new Error("Refusing to use the filesystem root as release output.");
  }
  try {
    await access(outputDirectory);
    throw new Error("Release output directory already exists.");
  } catch (error) {
    if (error.code !== "ENOENT") throw error;
  }
}

function validateRelease(value) {
  if (
    !value ||
    typeof value !== "object" ||
    value.draft !== false ||
    value.prerelease !== false ||
    typeof value.tag_name !== "string" ||
    value.tag_name.length === 0 ||
    typeof value.published_at !== "string" ||
    Number.isNaN(Date.parse(value.published_at)) ||
    !Array.isArray(value.assets)
  ) {
    throw new Error("GitHub returned invalid latest-release metadata.");
  }

  const assets = value.assets.filter(
    (asset) =>
      asset &&
      typeof asset.name === "string" &&
      asset.name.toLowerCase().endsWith(".mcpb"),
  );
  if (assets.length === 0) {
    throw new Error("The latest Stasis release has no .mcpb assets.");
  }

  const seenNames = new Set();
  const seenPlatforms = new Set();
  for (const asset of assets) {
    if (
      !Number.isSafeInteger(asset.id) ||
      asset.id <= 0 ||
      !Number.isSafeInteger(asset.size) ||
      asset.size <= 0 ||
      asset.state !== "uploaded" ||
      asset.name !== path.basename(asset.name) ||
      /[\\/]/.test(asset.name)
    ) {
      throw new Error("GitHub returned an invalid release asset path.");
    }
    const platform = classifyMcpbFilename(asset.name);
    const lowerName = asset.name.toLowerCase();
    if (seenNames.has(lowerName) || seenPlatforms.has(platform.id)) {
      throw new Error("The latest Stasis release has duplicate platform assets.");
    }
    seenNames.add(lowerName);
    seenPlatforms.add(platform.id);
  }

  return {
    version: value.tag_name,
    publishedAt: value.published_at,
    assets,
  };
}

async function fetchChecked(url, options, fetchImplementation) {
  let response;
  try {
    response = await fetchImplementation(url, {
      ...options,
      redirect: "follow",
    });
  } catch {
    throw new Error("The private Stasis release request could not be completed.");
  }
  if (!response.ok) {
    throw new Error(`The private Stasis release request failed (${response.status}).`);
  }
  return response;
}

export async function fetchLatestStasisRelease({
  outputDirectory,
  token,
  repository,
  fetchImplementation = globalThis.fetch,
  apiBaseUrl = "https://api.github.com",
}) {
  if (typeof fetchImplementation !== "function") {
    throw new Error("A Fetch API implementation is required.");
  }
  const output = path.resolve(outputDirectory);
  await ensureOutputDoesNotExist(output);

  const releaseResponse = await fetchChecked(
    `${apiBaseUrl}/repos/${repository}/releases/latest`,
    { headers: requestHeaders(token) },
    fetchImplementation,
  );
  let releaseJson;
  try {
    releaseJson = await releaseResponse.json();
  } catch {
    throw new Error("GitHub returned unreadable latest-release metadata.");
  }
  const release = validateRelease(releaseJson);

  try {
    await mkdir(output, { recursive: false, mode: 0o700 });
    for (const asset of release.assets) {
      const response = await fetchChecked(
        `${apiBaseUrl}/repos/${repository}/releases/assets/${asset.id}`,
        { headers: requestHeaders(token, "application/octet-stream") },
        fetchImplementation,
      );
      if (!response.body) {
        throw new Error("GitHub returned an empty release asset response.");
      }
      if (response.headers.get("content-type")?.toLowerCase().includes("application/json")) {
        throw new Error("GitHub returned release metadata instead of an asset stream.");
      }

      const destination = path.join(output, asset.name);
      const partialDestination = `${destination}.partial`;
      await pipeline(
        Readable.fromWeb(response.body),
        createWriteStream(partialDestination, { flags: "wx", mode: 0o600 }),
      );
      const stat = await lstat(partialDestination);
      if (!stat.isFile() || stat.size !== asset.size) {
        throw new Error("A downloaded Stasis release asset was incomplete.");
      }
      await rename(partialDestination, destination);
    }
    await writeFile(
      path.join(output, METADATA_FILENAME),
      `${JSON.stringify({
        version: release.version,
        publishedAt: release.publishedAt,
      })}\n`,
      { flag: "wx", mode: 0o600 },
    );
  } catch (error) {
    await rm(output, { recursive: true, force: true });
    throw error;
  }

  return { assetCount: release.assets.length };
}

async function main() {
  const outputDirectory = parseArguments(process.argv.slice(2));
  const { token, repository } = readConfiguration();
  delete process.env.STASIS_RELEASES_TOKEN;
  const result = await fetchLatestStasisRelease({
    outputDirectory,
    token,
    repository,
  });
  console.log(`Fetched ${result.assetCount} private Stasis release asset(s).`);
}

if (process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1])) {
  main().catch((error) => {
    console.error(`Stasis release synchronization failed: ${error.message}`);
    process.exitCode = 1;
  });
}
