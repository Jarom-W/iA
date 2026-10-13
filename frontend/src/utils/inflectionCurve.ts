type Point = readonly [number, number];
type Cubic = readonly [Point, Point, Point, Point];

/** Two cubic segments with a shared tangent and zero curvature at the marker.
 * Screen-space curvature is positive before the join and negative after it.
 */
export function inflectionCurve(x: number, y: number, width: number, height: number) {
  const left = x + 30, right = width + 50 - x;
  const rise = height * .38, fall = Math.min(height * .55, y - 20);
  const slope = Math.min(rise / left, fall / right) * .2;
  const incoming: Cubic = [
    [-30, y + rise], [x - left * 2 / 3, y + slope * left * 2 / 3],
    [x - left / 3, y + slope * left / 3], [x, y],
  ];
  const outgoing: Cubic = [
    [x, y], [x + right / 3, y - slope * right / 3],
    [x + right * 2 / 3, y - slope * right * 2 / 3], [width + 50, y - fall],
  ];
  return { incoming, outgoing };
}

export function cubicPath([start, first, second, end]: Cubic) {
  return `M ${start.join(" ")} C ${first.join(" ")} ${second.join(" ")} ${end.join(" ")}`;
}
