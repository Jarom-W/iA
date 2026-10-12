import { ArrowRight, ArrowUpRight } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { business, hero } from "../content/site";

function ConstructionLines() {
  const element = useRef<SVGSVGElement>(null);
  const [active, setActive] = useState(false);
  useEffect(() => {
    let inView = false;
    const update = () => setActive(inView && document.visibilityState === "visible");
    const observer = new IntersectionObserver(([entry]) => { inView = entry.isIntersecting; update(); });
    if (element.current) observer.observe(element.current);
    document.addEventListener("visibilitychange", update);
    return () => { observer.disconnect(); document.removeEventListener("visibilitychange", update); };
  }, []);
  return (
    <svg ref={element} data-active={active} className="hero-lattice" viewBox="0 0 1440 660" fill="none" aria-hidden="true" focusable="false">
      <g className="lattice-frame" stroke="currentColor" strokeWidth=".7">
        <path d="M-90 20 360 205 288 392-90 565M-90 20 80 306-90 565M360 205 80 306 288 392M-90 110 310 224M-90 220 265 242M-90 335 219 260M-90 450 172 278M-90 110 35 336l-125 114M-90 220l-10 147M-90 335l-55 62M360 205 288 392M310 224 260 379M265 242 231 367M219 260 202 354M172 278 174 342" />
        <path d="m1510 25-430 177 64 200 366 178M1510 25l-174 285 174 270M1080 202l256 108-192 92M1510 115l-383 107M1510 215l-335 28M1510 320l-287-57M1510 430l-240-147M1510 115l-127 222 127 93M1510 215l-80 145M1510 320l-32 67M1127 222l45 193M1175 243l24 185M1223 263l3 178M1270 283l-17 171" />
        <path className="construction-rule" d="M0 610h1440M65 0v660M1375 0v660M0 80h1440" strokeDasharray="3 9" />
      </g>
    </svg>
  );
}

export default function Hero() {
  return (
    <section id="top" className="hero-section" aria-labelledby="hero-title">
      <ConstructionLines />
      <div className="container hero-layout">
        <div className="hero-copy">
          <p className="eyebrow">{hero.category}</p>
          <h1 id="hero-title">{hero.headline[0]}<br /><span>{hero.headline[1]}</span></h1>
          <p className="hero-lede">{hero.description}</p>
          <div className="hero-actions">
            <a href="/contact/" className="button button-primary">{hero.primaryAction}<ArrowUpRight size={18} aria-hidden="true" /></a>
            <a href="/services/" className="text-link">{hero.secondaryAction}<ArrowRight size={16} aria-hidden="true" /></a>
          </div>
          <p className="hero-local">{business.localContext}</p>
        </div>
      </div>
      <div className="container capability-strip" aria-label="Areas of focus">
        <span><b>01 /</b> Business clarity</span>
        <span><b>02 /</b> Websites &amp; visibility</span>
        <span><b>03 /</b> Systems &amp; implementation</span>
      </div>
    </section>
  );
}
