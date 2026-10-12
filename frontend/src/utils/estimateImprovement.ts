export type ImprovementEstimate = {
  hoursSavedPerMonth: number;
  valuePerHour: number;
  addedMonthlyCost: number;
  setupCost: number;
};

export function estimateImprovement(input: ImprovementEstimate) {
  if (Object.values(input).some(value => !Number.isFinite(value) || value < 0)) {
    throw new Error("Use finite, non-negative inputs.");
  }

  const monthlyTimeValue = input.hoursSavedPerMonth * input.valuePerHour;
  const netMonthlyValue = monthlyTimeValue - input.addedMonthlyCost;
  const paybackMonths = netMonthlyValue > 0
    ? input.setupCost / netMonthlyValue
    : null;

  if (![monthlyTimeValue, netMonthlyValue, paybackMonths ?? 0].every(Number.isFinite)) {
    throw new Error("These values are too large to calculate reliably.");
  }

  return { monthlyTimeValue, netMonthlyValue, paybackMonths };
}
