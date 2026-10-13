import { useEffect, useRef } from "react";
import { cubicPath, inflectionCurve } from "../utils/inflectionCurve";

/** One finite, visibility-aware sequence, anchored to the actual link position. */
export default function NextStepCurves() {
  const svg = useRef<SVGSVGElement>(null);
  useEffect(() => {
    const element = svg.current;
    const section = element?.closest<HTMLElement>(".home-paths");
    const anchor = section?.querySelector<HTMLElement>(".approach-marker");
    if (!element || !section || !anchor) return;
    const motion = window.matchMedia("(prefers-reduced-motion: reduce)");
    let frame = 0, elapsed = 0, previous = 0, visible = false, started = false;
    let incomingLength = 0, outgoingLength = 0;
    const incoming = element.querySelector<SVGPathElement>(".arrival-curve")!;
    const outgoing = element.querySelector<SVGPathElement>(".departure-curve")!;
    const gray = [...element.querySelectorAll<SVGPathElement>(".background-arc")];
    const traveler = element.querySelector<SVGCircleElement>(".curve-traveler")!;
    const lengths: number[] = [];
    const draw = (path: SVGPathElement, length: number, progress: number) => {
      path.style.strokeDasharray = `${length}`;
      path.style.strokeDashoffset = `${length * (1 - Math.max(0, Math.min(1, progress)))}`;
    };
    const render = () => {
      const t = motion.matches ? 4800 : elapsed;
      gray.forEach((path, i) => draw(path, lengths[i], (t - i * 75) / (1300 + i * 180)));
      draw(incoming, incomingLength, (t - 500) / 1900);
      const arrived = t >= 2400;
      section.dataset.arrived = String(arrived);
      section.style.setProperty("--impact-scale", `${1 + Math.min(1, Math.max(0, (t - 2400) / 750)) * 1.7}`);
      section.style.setProperty("--impact-opacity", `${arrived ? Math.max(0, 1 - (t - 2400) / 750) : 0}`);
      incoming.style.stroke = arrived ? "var(--accent)" : "#81817b";
      draw(outgoing, outgoingLength, (t - 2400) / 2200);
      const path = arrived ? outgoing : incoming;
      const progress = Math.max(0, Math.min(1, arrived ? (t - 2400) / 2200 : (t - 500) / 1900));
      const point = path.getPointAtLength(progress * (arrived ? outgoingLength : incomingLength));
      traveler.setAttribute("cx", `${point.x}`); traveler.setAttribute("cy", `${point.y}`);
      traveler.style.fill = arrived ? "var(--accent)" : "#b5b5ad";
      traveler.style.opacity = t > 500 && t < 4600 ? "1" : "0";
    };
    const measure = () => {
      const bounds = section.getBoundingClientRect(), target = anchor.getBoundingClientRect();
      const w = bounds.width, h = bounds.height;
      const x = target.left + target.width / 2 - bounds.left, y = target.top + target.height / 2 - bounds.top;
      element.setAttribute("viewBox", `0 0 ${w} ${h}`);
      // Positive curvature in screen coordinates produces concave-down business curves.
      gray.forEach((path, i) => {
        const start = -w * .2 + i * w * .085;
        const span = w * (.48 + (i % 4) * .24);
        const base = h * (w < 800 ? .35 + i * .075 : .72 + (i % 3) * .1);
        const rise = Math.min(h * (.66 + (i % 4) * .1), w * (.36 + (i % 4) * .12));
        path.setAttribute("d", `M ${start} ${base} Q ${start + span / 2} ${base - rise * 2} ${start + span} ${base}`);
        lengths[i] = path.getTotalLength();
      });
      const curves = inflectionCurve(x, y, w, h);
      incoming.setAttribute("d", cubicPath(curves.incoming));
      outgoing.setAttribute("d", cubicPath(curves.outgoing));
      incomingLength = incoming.getTotalLength(); outgoingLength = outgoing.getTotalLength();
      render();
    };
    const tick = (now: number) => {
      if (previous) elapsed = Math.min(4800, elapsed + now - previous);
      previous = now; render();
      if (elapsed < 4800) frame = requestAnimationFrame(tick);
    };
    const update = () => {
      cancelAnimationFrame(frame); previous = 0;
      if (motion.matches) { render(); return; }
      if (visible && document.visibilityState === "visible" && elapsed < 4800) {
        started = true; frame = requestAnimationFrame(tick);
      }
    };
    const observer = new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting;
      if (visible || started) update();
    }, { rootMargin: "0px 0px -40px 0px" });
    observer.observe(anchor);
    const resize = new ResizeObserver(measure); resize.observe(section);
    document.addEventListener("visibilitychange", update);
    motion.addEventListener("change", update);
    measure(); update();
    return () => {
      cancelAnimationFrame(frame); observer.disconnect(); resize.disconnect();
      document.removeEventListener("visibilitychange", update); motion.removeEventListener("change", update);
      delete section.dataset.arrived;
    };
  }, []);
  return <svg ref={svg} className="next-step-curves" fill="none" aria-hidden="true" focusable="false">
    {Array.from({ length: 8 }, (_, index) => <path key={index} className="background-arc" />)}
    <path className="arrival-curve" /><path className="departure-curve" />
    <circle className="curve-traveler" r="3.5" />
  </svg>;
}
