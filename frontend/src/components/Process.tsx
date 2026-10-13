import { useState } from "react";
import type { KeyboardEvent } from "react";
import { processSteps } from "../content/site";

// y = 75t + 90t³: positive slope throughout, decreasing before t = 0
// and increasing afterward. Implement sits exactly at the inflection point.
const positions = [-0.85, -0.38, 0, 0.85].map(t => ({
  x: (360 + 290 * t) / 720 * 100,
  y: (220 - 75 * t - 90 * t ** 3) / 440 * 100,
}));
const outcomes = [
  "A shared view of the problem and what a useful improvement would look like.",
  "A practical recommendation, with the tradeoffs and next steps made clear.",
  "Something usable, tested against the agreed scope, with a documented handoff.",
  "A review of what changed and a sensible next priority, with optional scoped support.",
];

export default function Process() {
  const [active, setActive] = useState(0);
  function handleKey(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    const next = event.key === "ArrowRight" ? (index + 1) % processSteps.length
      : event.key === "ArrowLeft" ? (index + processSteps.length - 1) % processSteps.length
      : event.key === "Home" ? 0 : event.key === "End" ? processSteps.length - 1 : null;
    if (next === null) return;
    event.preventDefault();
    setActive(next);
    document.getElementById(`approach-step-${next}`)?.focus();
  }
  return (
    <section id="process" className="section process-section" aria-labelledby="process-title">
      <div className="container">
        <div className="section-heading split-heading">
          <div><p className="section-kicker">Approach / How we work</p><h1 id="process-title">Understand it.<br /><span>Then improve it.</span></h1></div>
          <p>The answer might be a clearer process, a setting in software you already pay for, or something custom. We make that decision before committing to the build.</p>
        </div>
        <div className="approach-curve-layout">
          <div className="approach-graph">
            <p className="small-label" id="curve-help">Explore the process / Hover, focus, or tap a step</p>
            <div className="curve-plot" role="tablist" aria-label="Four steps along the improvement curve" aria-describedby="curve-help">
              <svg viewBox="0 0 720 440" fill="none" aria-hidden="true" focusable="false">
                <g className="curve-grid">{[70, 215, 360, 505, 650].map(x => <path key={x} d={`M${x} 25V400`} />)}{[55, 137.5, 220, 302.5, 385].map(y => <path key={y} d={`M45 ${y}H685`} />)}</g>
                <path className="curve-axes" d="M45 25v375h640M39 33l6-8 6 8M677 394l8 6-8 6" />
                <path className="curve-inflection-guide" d="M360 220V400" />
                <path className="improvement-curve" d="M70 385C263.333333 155 456.666667 285 650 55" />
                {active === 2 && <g className="implementation-spread">
                  <path pathLength="1" d="M360 220C263.333333 245 166.666667 270 70 385" />
                  <path pathLength="1" d="M360 220C456.666667 195 553.333333 170 650 55" />
                </g>}
              </svg>
              {processSteps.map((step, index) => <button type="button" role="tab" className={`curve-step curve-step-${index}`} key={step.title} id={`approach-step-${index}`} aria-selected={active === index} aria-controls="approach-detail" tabIndex={active === index ? 0 : -1} style={{ left: `${positions[index].x}%`, top: `${positions[index].y}%` }} onMouseEnter={() => setActive(index)} onFocus={() => setActive(index)} onClick={() => setActive(index)} onKeyDown={event => handleKey(event, index)}>
                <span className="curve-point" aria-hidden="true" /><span className="curve-step-label"><span aria-hidden="true">0{index + 1} / </span>{step.title}</span>
              </button>)}
            </div>
            <div className="curve-caption"><span>From understanding to action</span><span aria-hidden="true">→</span></div>
          </div>
          <div className="approach-detail" id="approach-detail" role="tabpanel" aria-labelledby={`approach-step-${active}`} tabIndex={0}>
            <p className="small-label">Step 0{active + 1} / 04{active === 2 ? " · The inflection point" : ""}</p>
            <h2>{processSteps[active].title}</h2>
            <p className="approach-description">{processSteps[active].description}</p>
            <div className="approach-outcome"><p className="small-label">What this gives you</p><p>{outcomes[active]}</p></div>
            <a href="/contact/" className="text-link">Talk about your next step <span aria-hidden="true">↗</span></a>
          </div>
        </div>
        <p className="curve-note">An illustrative curve, not a forecast of business results. Implementation is the inflection point: the decision becomes something you can use.</p>
      </div>
    </section>
  );
}
