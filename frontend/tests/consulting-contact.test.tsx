import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import Contact from "../src/components/Contact";
const fetchMock = vi.fn();
beforeEach(() => { fetchMock.mockReset(); vi.stubGlobal("fetch", fetchMock); });
afterEach(() => vi.unstubAllGlobals());
function fillInquiry() {
  render(<Contact />);
  for (const [label, value] of [["Your name", " Test Owner "], ["Email address", "owner@example.com"], ["Business name", "Example Services"], ["What would you like to improve?", "Understand our quoting workflow."]]) {
    fireEvent.change(screen.getByLabelText(label), { target: { value } });
  }
}
function send() { fireEvent.click(screen.getByRole("button", { name: "Send inquiry" })); }
describe("business inquiry", () => {
  it("validates fields without making a request and focuses the first error", () => {
    render(<Contact />); send();
    expect(fetchMock).not.toHaveBeenCalled();
    expect(screen.getByLabelText("Your name")).toHaveFocus();
    expect(screen.getByText("Describe what you would like to improve.")).toBeVisible();
  });
  it("rejects an invalid optional website without sending", () => {
    fillInquiry();
    fireEvent.change(screen.getByLabelText(/Website/), { target: { value: "javascript:alert(1)" } }); send();
    expect(fetchMock).not.toHaveBeenCalled();
    expect(screen.getByLabelText(/Website/)).toHaveFocus();
  });
  it.each([false, undefined])("does not treat HTTP 200 with success=%s as acceptance", async success => {
    fetchMock.mockResolvedValue({ ok: true, json: async () => ({ success }) });
    fillInquiry(); send();
    expect(await screen.findByRole("alert")).toHaveTextContent("not confirmed");
    expect(screen.getByLabelText("Business name")).toHaveValue("Example Services");
    expect(screen.queryByRole("heading", { name: "Thanks for reaching out." })).not.toBeInTheDocument();
  });
  it.each([true, "true"])("accepts a confirmed response with success=%s", async success => {
    fetchMock.mockResolvedValue({ ok: true, json: async () => ({ success }) });
    fillInquiry(); send();
    expect(await screen.findByRole("heading", { name: "Thanks for reaching out." })).toBeVisible();
    const [endpoint, options] = fetchMock.mock.calls[0];
    expect(endpoint).toBe("https://formsubmit.co/ajax/jarom@inflectionarchitectures.com");
    expect(options.body.get("name")).toBe("Test Owner");
    expect(options.body.get("company")).toBe("Example Services");
    fireEvent.click(screen.getByRole("button", { name: "Send another message" }));
    expect(screen.getByLabelText("Your name")).toHaveValue("");
  });
  it("prevents duplicate submission while loading and recovers from network failure", async () => {
    let rejectRequest!: (reason: Error) => void;
    fetchMock.mockReturnValue(new Promise((_, reject) => { rejectRequest = reject; }));
    fillInquiry(); send();
    expect(screen.getByRole("button", { name: "Sending…" })).toBeDisabled();
    expect(screen.getByLabelText("Your name")).toBeDisabled();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    rejectRequest(new Error("offline"));
    await waitFor(() => expect(screen.getByRole("alert")).toBeVisible());
    expect(screen.getByRole("button", { name: "Send inquiry" })).toBeEnabled();
    expect(screen.getByRole("link", { name: "email jarom@inflectionarchitectures.com" })).toHaveAttribute("href", "mailto:jarom@inflectionarchitectures.com");
  });
});
