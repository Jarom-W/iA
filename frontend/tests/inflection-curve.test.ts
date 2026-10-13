import { describe, expect, it } from "vitest";
import { inflectionCurve } from "../src/utils/inflectionCurve";

describe("landing curve inflection", () => {
  it.each([[333, 430, 375, 800], [650, 330, 768, 900], [893, 270, 1440, 440]])(
    "joins smoothly with opposite concavity at marker %s,%s",
    (x, y, width, height) => {
      const { incoming: a, outgoing: b } = inflectionCurve(x, y, width, height);
      expect(a[3]).toEqual([x, y]);
      expect(b[0]).toEqual(a[3]);
      const leftSlope = (a[3][1] - a[2][1]) / (a[3][0] - a[2][0]);
      const rightSlope = (b[1][1] - b[0][1]) / (b[1][0] - b[0][0]);
      expect(leftSlope).toBeCloseTo(rightSlope, 10);
      expect(leftSlope).toBeLessThan(0);
      // Equal x spacing means these second differences measure curvature.
      expect(a[3][1] - 2 * a[2][1] + a[1][1]).toBeCloseTo(0, 10);
      expect(b[2][1] - 2 * b[1][1] + b[0][1]).toBeCloseTo(0, 10);
      expect(a[2][1] - 2 * a[1][1] + a[0][1]).toBeGreaterThan(0);
      expect(b[3][1] - 2 * b[2][1] + b[1][1]).toBeLessThan(0);
    },
  );
});
