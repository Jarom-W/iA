const steps = [
  { number: "01", title: "Understand.", detail: "Start with the problem, the people, and the tools you use. Define what success looks like and agree on a clear scope." },
  { number: "02", title: "Build.", detail: "Turn the plan into working software. Review real progress together, test assumptions, and refine the details as we go." },
  { number: "03", title: "Operate.", detail: "Get it into your hands and keep it running. Plan for deployment, maintenance, and the improvements that come next." },
];

export default function Process() {
  return (
    <section id="process" className="section process-section" aria-labelledby="process-title">
      <div className="container">
        <div className="section-heading split-heading">
          <div><p className="section-kicker">03 / The approach</p><h2 id="process-title">An idea is the start.<br /><span>Let’s see it through.</span></h2></div>
          <p>A direct relationship with the person writing the code. Clear communication, deliberate decisions, and software you can put to work.</p>
        </div>
        <div className="process-grid">
          {steps.map((step) => (
            <article className="process-step" key={step.number}>
              <span className="step-number">{step.number}<span aria-hidden="true"> /</span></span>
              <h3>{step.title}</h3><p>{step.detail}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
