const services = [
  { number: "01", title: "Build what’s missing.", description: "Web apps, desktop tools, and internal platforms built around your workflow. Thoughtful interfaces with solid engineering underneath.", tags: "APPLICATIONS / INTERNAL TOOLS / APIS" },
  { number: "02", title: "Connect the pieces.", description: "Bring your tools and data together. Automate repetitive work and put AI to use where it solves a real problem.", tags: "INTEGRATIONS / AUTOMATION / AI" },
  { number: "03", title: "Keep it moving.", description: "Software needs care after launch. Deployment, monitoring, maintenance, and ongoing improvements from the person who built it.", tags: "DEPLOYMENT / SUPPORT / ITERATION" },
];

function ServiceGeometry({ variant }: { variant: number }) {
  return (
    <svg className="service-geometry" viewBox="0 0 160 120" fill="none" aria-hidden="true">
      {variant === 0 ? (
        <g>
          <path d="m80 12 52 30v58l-52-30-52 30V42Z" />
          <path d="m28 42 52 30 52-30M80 12v60m0 0v44M28 100l52 16 52-16" />
          <path className="geometry-dim" d="m54 27 52 30v51M106 27 54 57v51M28 71l52 30 52-30" />
        </g>
      ) : variant === 1 ? (
        <g>
          <path d="m48 20 28 16v32L48 84 20 68V36Zm64 16 28 16v32l-28 16-28-16V52Z" />
          <path d="m20 36 28 16 28-16M48 52v32m36-32 28 16 28-16m-28 16v32M76 36l36-16 28 16v16M76 68l8 4" />
          <path className="geometry-dim" d="M48 20v32l36 20m28-52v48M20 68l28-16 36 20 28-4 28 16" />
        </g>
      ) : (
        <g>
          <path d="m80 12 55 28-55 28-55-28Zm-55 48 55 28 55-28M25 80l55 28 55-28" />
          <path className="geometry-dim" d="M25 40v40M80 68v40m55-68v40M52 26l55 28M52 54l55-28M80 12v28m-55 0h110" />
        </g>
      )}
    </svg>
  );
}

export default function Services() {
  return (
    <section id="services" className="section services-section" aria-labelledby="services-title">
      <div className="container">
        <div className="section-heading split-heading">
          <div><p className="section-kicker">01 / Capabilities</p><h2 id="services-title">The right software.<br /><span>The whole lifecycle.</span></h2></div>
          <p>One engineering partner from architecture to operation. A focused tool or an entire platform, built around what you actually need.</p>
        </div>
        <div className="service-grid">
          {services.map((service, index) => (
            <article className="service-card" key={service.number}>
              <div className="card-topline"><span>[ {service.number} ]</span><span aria-hidden="true">+</span></div>
              <ServiceGeometry variant={index} />
              <h3>{service.title}</h3><p>{service.description}</p>
              <div className="service-tags">{service.tags}</div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
