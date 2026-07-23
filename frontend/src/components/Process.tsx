import { ArrowRight } from "lucide-react";

const steps = [
  {
    number: "1",
    title: "We talk",
    description: "You tell me what is taking too much time or getting in the way. I listen and ask questions.",
  },
  {
    number: "2",
    title: "I map a practical next step",
    description: "You get a clear recommendation, including what it will take and what a useful result looks like.",
  },
  {
    number: "3",
    title: "We build and improve",
    description: "I create the solution, help your team use it, and refine it as we learn what works best.",
  },
];

export default function Process() {
  return (
    <section id="process" className="section process-section">
      <div className="container">
        <div className="section-heading centered-heading">
          <p className="section-kicker">What to expect</p>
          <h2>A clear path, without the jargon.</h2>
          <p>You’ll always know what we’re doing, why it matters, and what comes next.</p>
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
            <strong>My promise: people stay at the center.</strong>
            <p>
              The goal is not to replace the knowledge and judgment your team brings. It is
              to remove the drag that keeps them from using those strengths.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
