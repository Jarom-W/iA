import { ArrowRight } from "lucide-react";

const steps = [
  {
    number: "1",
    title: "Show me how work gets done",
    description: "We talk through the tools you use, the questions you keep asking, and the tasks that drain your time. No preparation or technical vocabulary needed.",
  },
  {
    number: "2",
    title: "I configure the useful pieces",
    description: "I set up the right AI tools and available integrations around your workflow. When it helps, I layer in off-market tools I have already built to make the experience more capable and easier to use.",
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
          <h2>From “AI can write” to “AI can help me run this.”</h2>
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
              I am not here to pitch a software build. I bring proven tools I have already
              developed when they make your AI more useful. The goal is a better workflow,
              not another technology project to manage.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
