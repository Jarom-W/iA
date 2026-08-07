import { ArrowRight } from "lucide-react";

const steps = [
  {
    number: "1",
    title: "Show me how work gets done",
    description: "We talk through the tools you use, the questions you keep asking, and the tasks that drain your time. No preparation or technical vocabulary needed.",
  },
  {
    number: "2",
    title: "I connect the useful pieces",
    description: "I configure your AI, connect the right apps, and add custom software only where it makes the experience simpler or more capable.",
  },
  {
    number: "3",
    title: "We use it together",
    description: "I walk you through real tasks, tune the setup to your business, and make sure it feels natural before I get out of your way.",
  },
];

export default function Process() {
  return (
    <section id="process" className="section process-section">
      <div className="container">
        <div className="section-heading centered-heading">
          <p className="section-kicker">What to expect</p>
          <h2>From “Claude can write” to “Claude can help me run this.”</h2>
          <p>The technology stays behind the scenes. You get a simple way to ask, understand, and act.</p>
        </div>

        <div className="process-grid">
          {steps.map((step, index) => (
            <article className="process-step" key={step.number}>
              <span className="step-number">{step.number}</span>
              <h3>{step.title}</h3>
              <p>{step.description}</p>
              {index < steps.length - 1 && <ArrowRight className="step-arrow" size={20} aria-hidden="true" />}
            </article>
          ))}
        </div>

        <div className="promise-card">
          <div className="promise-mark">IA</div>
          <div>
            <strong>No platform to buy. No giant rebuild.</strong>
            <p>
              Custom software is sometimes the glue, but it is never the thing I am trying to sell you.
              The goal is to make the tools you already have understand more and ask less of you.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
