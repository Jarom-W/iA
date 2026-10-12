import { describe, expect, it } from "vitest";
import { classifyMcpbFilename } from "../../scripts/stasis-platforms.mjs";

describe("MCPB platform filenames", () => {
  it.each([
    ["stasis-windows-x64.mcpb", "windows-x64", "Windows x64"],
    ["Stasis_win32_amd64.mcpb", "windows-x64", "Windows x64"],
    ["stasis-darwin-arm64.mcpb", "macos-arm64", "macOS Apple silicon"],
    ["stasis-macos-apple-silicon.mcpb", "macos-arm64", "macOS Apple silicon"],
    ["stasis-mac-intel.mcpb", "macos-x64", "macOS Intel"],
    ["stasis-darwin-x86_64.mcpb", "macos-x64", "macOS Intel"],
    ["stasis-linux-amd64.mcpb", "linux-x64", "Linux x64"],
  ])("maps %s to its friendly platform", (filename, id, label) => {
    expect(classifyMcpbFilename(filename)).toEqual({ id, label });
  });

  it.each([
    "stasis.mcpb",
    "stasis-linux-arm64.mcpb",
    "stasis-macos-universal.mcpb",
    "../stasis-windows-x64.mcpb",
    "stasis-windows-x64.zip",
  ])("rejects unsupported or unsafe filename %s", (filename) => {
    expect(() => classifyMcpbFilename(filename)).toThrow();
  });
});
