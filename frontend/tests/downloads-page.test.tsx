import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import DownloadsPage from "../src/components/downloads/DownloadsPage";
import { unlockRelease } from "../src/downloads/crypto";

vi.mock("../src/downloads/crypto", async (importOriginal) => {
  const original = await importOriginal<typeof import("../src/downloads/crypto")>();
  return {
    ...original,
    unlockRelease: vi.fn(),
    decryptDownload: vi.fn(),
  };
});

const manifest = {
  schemaVersion: 1 as const,
  release: { version: "v1.5.0", releaseDate: "2026-08-13" },
  assets: [
    {
      platform: "windows-x64" as const,
      label: "Windows x64",
      filename: "stasis-windows-x64.mcpb",
      size: 2_097_152,
      sha256: "a".repeat(64),
      payload: "assets/0123456789abcdef0123456789abcdef.json",
    },
  ],
};

beforeEach(() => {
  vi.mocked(unlockRelease).mockReset();
});

describe("Stasis downloads page", () => {
  it("renders the locked state with accessible privacy guidance", () => {
    render(<DownloadsPage />);
    expect(screen.getByRole("heading", { name: /private early access/i })).toBeVisible();
    expect(screen.getByLabelText("Passphrase")).toHaveAttribute("type", "password");
    expect(screen.getByRole("button", { name: "Unlock Downloads" })).toBeEnabled();
    expect(screen.getByText(/processed locally/i)).toBeVisible();
  });

  it("renders a loading state while decrypting", async () => {
    vi.mocked(unlockRelease).mockReturnValue(new Promise(() => {}));
    const user = userEvent.setup();
    render(<DownloadsPage />);
    await user.type(screen.getByLabelText("Passphrase"), "temporary-passphrase");
    await user.click(screen.getByRole("button", { name: "Unlock Downloads" }));
    expect(screen.getByRole("button", { name: /Unlocking/ })).toBeDisabled();
    expect(screen.getByText(/Decrypting release information locally/)).toBeVisible();
  });

  it("renders a generic error, clears the input, and restores focus", async () => {
    vi.mocked(unlockRelease).mockRejectedValue(new Error("authentication failed"));
    const user = userEvent.setup();
    render(<DownloadsPage />);
    const input = screen.getByLabelText("Passphrase");
    await user.type(input, "incorrect secret value");
    await user.click(screen.getByRole("button", { name: "Unlock Downloads" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/couldn’t unlock/i);
    await waitFor(() => expect(input).toHaveFocus());
    expect(input).toHaveValue("");
    expect(screen.queryByText("authentication failed")).not.toBeInTheDocument();
  });

  it("renders release metadata and derived download choices after unlock", async () => {
    vi.mocked(unlockRelease).mockResolvedValue(manifest);
    const user = userEvent.setup();
    render(<DownloadsPage />);
    await user.type(screen.getByLabelText("Passphrase"), "correct temporary passphrase");
    await user.click(screen.getByRole("button", { name: "Unlock Downloads" }));
    expect(await screen.findByRole("heading", { name: "Stasis v1.5.0" })).toHaveFocus();
    expect(screen.getByText("Released August 13, 2026")).toBeVisible();
    expect(screen.getByRole("heading", { name: "Windows x64" })).toBeVisible();
    expect(screen.getByText("2.0 MB")).toBeVisible();
    expect(screen.getByText("a".repeat(64))).toBeVisible();
    expect(screen.getByText(/Settings → Extensions/)).toBeVisible();
  });
});
