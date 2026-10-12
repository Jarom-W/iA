import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ImprovementIllustration from "../src/components/ImprovementIllustration";
describe("illustrative calculator", () => {
  it("presents the sample and calculates immediate and nonpositive payback", () => {
    render(<ImprovementIllustration />);
    expect(screen.getByText("$325")).toBeVisible();
    expect(screen.getByTestId("payback")).toHaveTextContent("4.6 months");
    fireEvent.change(screen.getByLabelText(/One-time setup cost/), { target: { value: "0" } });
    expect(screen.getByTestId("payback")).toHaveTextContent("Immediate");
    fireEvent.change(screen.getByLabelText(/Added monthly cost/), { target: { value: "450" } });
    expect(screen.getByTestId("payback")).toHaveTextContent("No payback under these assumptions");
  });
  it("does not convert an empty field to zero and provides an accessible error", () => {
    render(<ImprovementIllustration />);
    const input = screen.getByLabelText(/Hours saved per month/);
    fireEvent.change(input, { target: { value: "" } });
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(input).toHaveAccessibleDescription("Enter a finite, non-negative amount.");
    expect(screen.queryByTestId("payback")).not.toBeInTheDocument();
    fireEvent.change(input, { target: { value: "8" } });
    expect(screen.getByTestId("payback")).toHaveTextContent("4.6 months");
  });
});
