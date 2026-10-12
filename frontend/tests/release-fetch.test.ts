import { readFile } from "node:fs/promises";
import { mkdtemp, rm } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  fetchLatestStasisRelease,
  readConfiguration,
} from "../../scripts/fetch-stasis-release.mjs";

const temporaryDirectories: string[] = [];

async function outputPath() {
  const root = await mkdtemp(path.join(os.tmpdir(), "stasis-fetch-test-"));
  temporaryDirectories.push(root);
  return path.join(root, "release");
}

afterEach(async () => {
  await Promise.all(
    temporaryDirectories.splice(0).map((directory) =>
      rm(directory, { recursive: true, force: true }),
    ),
  );
});

describe("private GitHub release synchronization", () => {
  it("requires the private repository token and repository variable", () => {
    expect(() => readConfiguration({})).toThrow(/TOKEN/);
    expect(() => readConfiguration({ STASIS_RELEASES_TOKEN: "token" })).toThrow(
      /REPOSITORY/,
    );
    expect(() =>
      readConfiguration({
        STASIS_RELEASES_TOKEN: "token",
        STASIS_RELEASE_REPOSITORY: "not-a-repository",
      }),
    ).toThrow(/OWNER\/REPO/);
  });

  it("streams expected assets and asks Fetch to follow redirects", async () => {
    const outputDirectory = await outputPath();
    const fetchImplementation = vi
      .fn()
      .mockResolvedValueOnce(
        Response.json({
          draft: false,
          prerelease: false,
          tag_name: "v2.0.0",
          published_at: "2026-08-13T01:02:03Z",
          assets: [
            {
              id: 42,
              name: "stasis-windows-x64.mcpb",
              size: 22,
              state: "uploaded",
            },
            { id: 99, name: "checksums.txt" },
          ],
        }),
      )
      .mockResolvedValueOnce(new Response("generated-mcpb-fixture"));

    await expect(
      fetchLatestStasisRelease({
        outputDirectory,
        token: "test-token",
        repository: "owner/private-stasis",
        fetchImplementation,
      }),
    ).resolves.toEqual({ assetCount: 1 });

    expect(fetchImplementation).toHaveBeenNthCalledWith(
      2,
      "https://api.github.com/repos/owner/private-stasis/releases/assets/42",
      expect.objectContaining({
        redirect: "follow",
        headers: expect.objectContaining({ Accept: "application/octet-stream" }),
      }),
    );
    expect(fetchImplementation).toHaveBeenCalledTimes(2);
    expect(
      await readFile(path.join(outputDirectory, "stasis-windows-x64.mcpb"), "utf8"),
    ).toBe("generated-mcpb-fixture");
  });

  it("fails closed when authentication fails or the release has no MCPB assets", async () => {
    await expect(
      fetchLatestStasisRelease({
        outputDirectory: await outputPath(),
        token: "test-token",
        repository: "owner/private-stasis",
        fetchImplementation: vi.fn().mockResolvedValue(new Response(null, { status: 401 })),
      }),
    ).rejects.toThrow(/401/);

    await expect(
      fetchLatestStasisRelease({
        outputDirectory: await outputPath(),
        token: "test-token",
        repository: "owner/private-stasis",
        fetchImplementation: vi.fn().mockResolvedValue(
          Response.json({
            draft: false,
            prerelease: false,
            tag_name: "v2.0.0",
            published_at: "2026-08-13T01:02:03Z",
            assets: [{ id: 1, name: "checksums.txt", size: 10, state: "uploaded" }],
          }),
        ),
      }),
    ).rejects.toThrow(/no .mcpb assets/i);
  });
});
