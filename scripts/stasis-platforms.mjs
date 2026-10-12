const PLATFORM_DEFINITIONS = [
  {
    id: "windows-x64",
    label: "Windows x64",
    operatingSystem: /(?:^|[._-])(?:windows|win32|win)(?:[._-]|$)/i,
    architecture: /(?:^|[._-])(?:x64|x86_64|amd64)(?:[._-]|$)/i,
  },
  {
    id: "macos-arm64",
    label: "macOS Apple silicon",
    operatingSystem: /(?:^|[._-])(?:macos|mac|darwin|osx)(?:[._-]|$)/i,
    architecture: /(?:^|[._-])(?:arm64|aarch64|apple[._-]?silicon)(?:[._-]|$)/i,
  },
  {
    id: "macos-x64",
    label: "macOS Intel",
    operatingSystem: /(?:^|[._-])(?:macos|mac|darwin|osx)(?:[._-]|$)/i,
    architecture: /(?:^|[._-])(?:x64|x86_64|amd64|intel)(?:[._-]|$)/i,
  },
  {
    id: "linux-x64",
    label: "Linux x64",
    operatingSystem: /(?:^|[._-])linux(?:[._-]|$)/i,
    architecture: /(?:^|[._-])(?:x64|x86_64|amd64)(?:[._-]|$)/i,
  },
];

export function classifyMcpbFilename(filename) {
  if (
    typeof filename !== "string" ||
    filename.length === 0 ||
    filename !== filename.split(/[\\/]/).at(-1) ||
    !/^[A-Za-z0-9][A-Za-z0-9._-]*\.mcpb$/i.test(filename) ||
    !filename.toLowerCase().endsWith(".mcpb")
  ) {
    throw new Error("Release assets must be top-level .mcpb files.");
  }

  const stem = filename.slice(0, -".mcpb".length);
  const matches = PLATFORM_DEFINITIONS.filter(
    ({ operatingSystem, architecture }) =>
      operatingSystem.test(stem) && architecture.test(stem),
  );

  if (matches.length !== 1) {
    throw new Error(`Unsupported or ambiguous MCPB platform filename: ${filename}`);
  }

  const [{ id, label }] = matches;
  return { id, label };
}

export const supportedPlatforms = PLATFORM_DEFINITIONS.map(({ id, label }) => ({
  id,
  label,
}));
