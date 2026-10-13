import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import Process from "../src/components/Process";

describe("interactive approach curve", () => {
  it("updates the detail panel on hover and tap", async () => {
    const user = userEvent.setup();
    render(<Process />);
    expect(screen.getByRole("tabpanel")).toHaveAccessibleName("Understand");
    await user.hover(screen.getByRole("tab", { name: "Decide" }));
    expect(screen.getByRole("tabpanel")).toHaveAccessibleName("Decide");
    await user.click(screen.getByRole("tab", { name: "Implement" }));
    expect(screen.getByRole("tabpanel")).toHaveAccessibleName("Implement");
    expect(screen.getByText(/The inflection point/)).toBeInTheDocument();
    expect(screen.queryByText("Look between the steps.")).not.toBeInTheDocument();
  });
  it("spreads from Implement on hover or keyboard selection and resets on another step", async () => {
    const user = userEvent.setup();
    const { container } = render(<Process />);
    expect(container.querySelector(".implementation-spread")).toBeNull();
    await user.hover(screen.getByRole("tab", { name: "Implement" }));
    const halves = container.querySelectorAll(".implementation-spread path");
    expect(halves).toHaveLength(2);
    halves.forEach(path => expect(path.getAttribute("d")).toMatch(/^M360 220C/));
    await user.hover(screen.getByRole("tab", { name: "Decide" }));
    expect(container.querySelector(".implementation-spread")).toBeNull();
    await user.click(screen.getByRole("tab", { name: "Decide" }));
    await user.keyboard("{ArrowRight}");
    expect(container.querySelectorAll(".implementation-spread path")).toHaveLength(2);
  });
  it("supports keyboard selection, wrapping, and Home/End", async () => {
    const user = userEvent.setup();
    render(<Process />);
    await user.tab();
    expect(screen.getByRole("tab", { name: "Understand" })).toHaveFocus();
    await user.keyboard("{ArrowRight}");
    expect(screen.getByRole("tab", { name: "Decide" })).toHaveFocus();
    expect(screen.getByRole("tabpanel")).toHaveAccessibleName("Decide");
    await user.keyboard("{End}{ArrowRight}");
    expect(screen.getByRole("tab", { name: "Understand" })).toHaveFocus();
    await user.keyboard("{ArrowLeft}");
    expect(screen.getByRole("tab", { name: "Improve" })).toHaveFocus();
    await user.keyboard("{Home}");
    expect(screen.getByRole("tab", { name: "Understand" })).toHaveAttribute("aria-selected", "true");
  });
});
