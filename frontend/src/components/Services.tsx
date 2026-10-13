import { ArrowUpRight } from "lucide-react";
import { services } from "../content/site";

export default function Services() {
  return (
    <section id="services" className="section services-section" aria-labelledby="services-title">
      <div className="container">
        <div className="section-heading split-heading">
          <div><h1 id="services-title">A clearer decision.<br /><span>A useful next step.</span></h1></div>
        </div>
        <div className="service-list">
          {services.map((service, index) => (
            <article className="service-row" key={service.id}>
              <div className="service-title"><span className="item-index">0{index + 1} /</span><h2>{service.title}</h2><span className="service-descriptor">{service.descriptor}</span></div>
              <div className="service-description"><p>{service.description}</p><p className="service-work">{service.work}</p></div>
              <div className="service-deliverable"><span className="small-label">What you leave with</span><p>{service.deliverable}</p><a href="/contact/" className="text-link">{service.next}<ArrowUpRight size={16} aria-hidden="true" /></a></div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
