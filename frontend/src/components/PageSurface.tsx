import { useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";

// A static, page-relative reveal. The edges break apart first; the center follows.
function tilePath(width: number, height: number) {
  if (!width || !height) return "";
  const start = height * 0.5;
  const end = height * 0.75;
  const tile = width < 600 ? 20 : 32;
  const commands = [`M0 ${end}H${width}V${height}H0Z`];
  for (let y = start, row = 0; y < end; y += tile, row++) {
    const progress = (y + tile / 2 - start) / (end - start);
    for (let x = 0, column = 0; x < width; x += tile, column++) {
      const edge = Math.abs((x + tile / 2) / width * 2 - 1);
      let seed = Math.imul(column + 1, 73856093) ^ Math.imul(row + 1, 19349663);
      seed = Math.imul(seed ^ (seed >>> 16), 0x7feb352d);
      const noise = ((seed ^ (seed >>> 15)) >>> 0) / 4294967295;
      const threshold = 0.8 - 0.6 * edge ** 1.2 + (noise - 0.5) * (0.4 + edge * 0.35);
      if (progress >= Math.max(0.015, Math.min(0.98, threshold))) {
        commands.push(`M${x} ${y}h${Math.min(tile, width - x)}v${Math.min(tile, end - y)}H${x}Z`);
      }
    }
  }
  return commands.join("");
}

export default function PageSurface({ children }: { children: ReactNode }) {
  const element = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 0, height: 0 });
  const path = useMemo(() => tilePath(size.width, size.height), [size]);

  useEffect(() => {
    const canvas = element.current;
    if (!canvas) return;
    let frame = 0;
    let height = canvas.offsetHeight;
    const updateHeader = () => {
      frame = 0;
      // The fixed navigation follows the central, readable part of the reveal.
      const tone = window.scrollY + 40 >= height * 0.725 ? "light" : "dark";
      if (document.documentElement.dataset.pageTone !== tone) document.documentElement.dataset.pageTone = tone;
    };
    const onScroll = () => { if (!frame) frame = requestAnimationFrame(updateHeader); };
    const observer = new ResizeObserver(() => {
      height = canvas.offsetHeight;
      const width = canvas.offsetWidth;
      setSize(previous => previous.width === width && previous.height === height ? previous : { width, height });
      onScroll();
    });
    observer.observe(canvas);
    window.addEventListener("scroll", onScroll, { passive: true });
    updateHeader();
    return () => {
      observer.disconnect();
      window.removeEventListener("scroll", onScroll);
      cancelAnimationFrame(frame);
      delete document.documentElement.dataset.pageTone;
    };
  }, []);

  return <div className="page-canvas" ref={element}>
    {children}
    <svg className="tile-inversion" viewBox={`0 0 ${size.width || 1} ${size.height || 1}`} preserveAspectRatio="none" aria-hidden="true" focusable="false">
      <path d={path} fill="white" />
    </svg>
  </div>;
}
