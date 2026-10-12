import { useState } from "react";
import type { KeyboardEvent } from "react";
import { processSteps, workflow } from "../content/site";

export default function Process() {
  const [active, setActive] = useState(0);
  function handleKey(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    const next = event.key === "ArrowRight" ? (index + 1) % workflow.length
      : event.key === "ArrowLeft" ? (index + workflow.length - 1) % workflow.length
      : event.key === "Home" ? 0 : event.key === "End" ? workflow.length - 1 : null;
    if (next === null) return;
    event.preventDefault();
    setActive(next);
    document.getElementById(`workflow-tab-${next}`)?.focus();
  }
  return (
    <section id="process" className="section process-section" aria-labelledby="process-title">
      <div className="container">
        <div className="section-heading split-heading">
          <div><p className="section-kicker">Approach / How we work</p><h1 id="process-title">Understand it.<br /><span>Then improve it.</span></h1></div>
          <p>The answer might be a clearer process, a setting in software you already pay for, or something custom. We make that decision before committing to the build.</p>
        </div>
        <ol className="process-grid">
          {processSteps.map((step, index) => <li className="process-step" key={step.title}><span className="step-number">0{index + 1} /</span><h2>{step.title}</h2><p>{step.description}</p></li>)}
        </ol>
        <div className="workflow-example">
          <div className="workflow-heading"><div><p className="small-label">Illustrative workflow / A service business</p><h2>Look between the steps.</h2></div><p>Select a stage to explore a possible issue and intervention.</p></div>
          <div className="workflow-tabs" role="tablist" aria-label="Example service business workflow">
            {workflow.map((stage, index) => <button type="button" role="tab" key={stage.name} id={`workflow-tab-${index}`} aria-selected={active === index} aria-controls="workflow-panel" tabIndex={active === index ? 0 : -1} onClick={() => setActive(index)} onKeyDown={event => handleKey(event, index)}><span aria-hidden="true">0{index + 1}</span>{stage.name}</button>)}
          </div>
          <div className="workflow-panel" id="workflow-panel" role="tabpanel" aria-labelledby={`workflow-tab-${active}`} tabIndex={0}>
            <div><p className="small-label">What can get stuck</p><p>{workflow[active].issue}</p></div>
            <div><p className="small-label">A possible improvement</p><p>{workflow[active].intervention}</p></div>
          </div>
          <p className="example-footnote">An example to think with, not a report of client performance. The right intervention depends on the actual business.</p>
        </div>
      </div>
    </section>
  );
}
