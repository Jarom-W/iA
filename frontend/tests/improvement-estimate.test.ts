import { describe, expect, it } from "vitest";
import { estimateImprovement } from "../src/utils/estimateImprovement";
const sample = { hoursSavedPerMonth: 8, valuePerHour: 50, addedMonthlyCost: 75, setupCost: 1500 };
describe("improvement decision estimate", () => {
  it("calculates the hypothetical example", () => {
    const result = estimateImprovement(sample);
    expect(result.monthlyTimeValue).toBe(400);
    expect(result.netMonthlyValue).toBe(325);
    expect(result.paybackMonths).toBeCloseTo(4.61538, 4);
  });
  it("has immediate payback with zero setup and positive value", () => {
    expect(estimateImprovement({ ...sample, setupCost: 0 }).paybackMonths).toBe(0);
  });
  it.each([400, 450])("has no payback when recurring cost is %s", addedMonthlyCost => {
    expect(estimateImprovement({ ...sample, addedMonthlyCost }).paybackMonths).toBeNull();
  });
  it("handles all zero inputs without infinity or NaN", () => {
    expect(estimateImprovement({ hoursSavedPerMonth: 0, valuePerHour: 0, addedMonthlyCost: 0, setupCost: 0 }))
      .toEqual({ monthlyTimeValue: 0, netMonthlyValue: 0, paybackMonths: null });
  });
  it.each([-1, NaN, Infinity, -Infinity])("rejects invalid input %s", value => {
    for (const key of Object.keys(sample)) expect(() => estimateImprovement({ ...sample, [key]: value })).toThrow("finite, non-negative");
  });
  it("rejects overflow rather than displaying an infinite result", () => {
    expect(() => estimateImprovement({ ...sample, hoursSavedPerMonth: Number.MAX_VALUE, valuePerHour: 2 })).toThrow("too large");
  });
});
