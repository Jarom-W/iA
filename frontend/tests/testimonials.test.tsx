import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import Testimonials from "../src/components/testimonials/Testimonials";

afterEach(() => vi.unstubAllGlobals());

describe("published client testimonials", () => {
  it("renders approved public content as text without exposing private response fields", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => ({ testimonials: [
      { id: "one", name: "Test Client", quote: "<script>not executable</script>", company: "Example Company", role: "Owner", service: "Website", rating: 4, email: "private@example.test" },
      { id: "invalid", quote: "Missing name" },
    ] }) }));
    const { container } = render(<Testimonials />);
    expect(await screen.findByText("Test Client")).toBeInTheDocument();
    expect(screen.getByLabelText("4 out of 5 stars")).toBeInTheDocument();
    expect(screen.getByText("Owner · Example Company")).toBeInTheDocument();
    expect(screen.getByText("<script>not executable</script>")).toBeInTheDocument();
    expect(container.querySelector("script")).toBeNull();
    expect(screen.queryByText("private@example.test")).not.toBeInTheDocument();
    expect(screen.queryByText("Missing name")).not.toBeInTheDocument();
  });

  it("supports legacy unrated testimonials and rejects invalid ratings", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => ({ testimonials: [
      { id: "legacy", name: "Earlier Client", quote: "Helpful", rating: null },
      ...[0, 6, 2.5, "5"].map((rating, i) => ({ id: String(i), name: "Invalid Client", quote: "Invalid rating", rating })),
    ] }) }));
    render(<Testimonials />);
    expect(await screen.findByText("Earlier Client")).toBeInTheDocument();
    expect(screen.queryByText("Invalid rating")).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/out of 5 stars/)).not.toBeInTheDocument();
  });

  it.each([[], undefined])("hides an empty or malformed feed", async testimonials => {
    const json = vi.fn().mockResolvedValue({ testimonials });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json }));
    const { container } = render(<Testimonials />);
    await waitFor(() => expect(json).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
  });

  it("does not break the page when the feedback service is unavailable", async () => {
    const fetchMock = vi.fn().mockRejectedValue(new Error("Offline"));
    vi.stubGlobal("fetch", fetchMock);
    const { container } = render(<Testimonials />);
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
  });
});
