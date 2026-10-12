import { ArrowUpRight } from "lucide-react";
import { pricing, usd } from "../content/pricing";

type RecurringPlan = typeof pricing.websiteCare[number] | typeof pricing.businessSupport[number];
function SupportGroup({ title, description, plans }: { title: string; description: string; plans: readonly RecurringPlan[] }) {
  return (
    <div className="support-group">
      <div className="support-heading"><h2>{title}</h2><p>{description}</p></div>
      {plans.map(plan => <article className="support-plan" key={plan.name}>
        <div className="plan-title"><h3>{plan.name}</h3><p>{usd(plan.amount)}<span>/ month</span></p></div>
        <p>{plan.summary}</p><ul>{plan.includes.map(item => <li key={item}>{item}</li>)}</ul><p className="scope-note">{plan.note}</p>
      </article>)}
    </div>
  );
}

export default function Pricing() {
  return (
    <section id="pricing" className="section pricing-section" aria-labelledby="pricing-title">
      <div className="container">
        <div className="section-heading split-heading">
          <div><p className="section-kicker">Pricing &amp; scope</p><h1 id="pricing-title">Clear starting points.<br /><span>Agreed boundaries.</span></h1></div>
          <p>A short fit conversation helps us decide whether working together makes sense. A paid assessment or discovery is separate, with a defined deliverable and fee.</p>
        </div>
        <div className="pricing-group-label"><h2>Projects</h2><span className="small-label">Launch pricing / USD</span></div>
        <div className="project-prices">
          {pricing.projects.map(project => <article className="project-price" key={project.id}>
            <div className="project-price-title"><h3>{project.name}</h3><p className="price-value">{project.amount === null ? <span className="scoped-price">Scoped after discovery</span> : <>{project.starting && <span>from </span>}{usd(project.amount)}</>}</p></div>
            <div className="project-price-content"><p className="project-summary">{project.summary}</p><ul>{project.includes.map(item => <li key={item}>{item}</li>)}</ul><p className="scope-note">{project.note}</p>
              {project.id === "custom" && <p className="discovery-price">{pricing.technicalDiscovery.name} starts at <strong>{usd(pricing.technicalDiscovery.amount)}</strong> where needed.</p>}
              <details className="scope-details"><summary>{project.id === "custom" ? "What technical discovery delivers" : `Scope details: ${project.name}`}</summary><p>{project.detail}</p></details>
            </div>
          </article>)}
        </div>
        <details className="other-projects"><summary>Other project starting points<span aria-hidden="true">+</span></summary><ul>{pricing.otherProjects.map(project => <li key={project.name}><span>{project.name}<small>{project.note}</small></span><span>{project.qualifier} <strong>{usd(project.amount)}</strong></span></li>)}</ul></details>
        <div className="pricing-group-label recurring-label"><h2>Optional ongoing support</h2><span className="small-label">Separate services / Defined scope</span></div>
        <div className="support-grid">
          <SupportGroup title="Website care" description="Keep an agreed website setup maintained." plans={pricing.websiteCare} />
          <SupportGroup title="Business support" description="Keep the business priorities in view." plans={pricing.businessSupport} />
        </div>
        <div className="pricing-terms">{pricing.terms.map(term => <p key={term}>{term}</p>)}</div>
        <div className="pricing-next"><p>Not sure where your problem fits?<span>Start with the situation. We can choose the right scope together.</span></p><a href="/contact/" className="button button-outline">Talk through the fit<ArrowUpRight size={17} aria-hidden="true" /></a></div>
      </div>
    </section>
  );
}
