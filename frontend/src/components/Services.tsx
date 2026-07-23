import { Compass, MessagesSquare, Workflow } from "lucide-react";

const services = [
  {
    number: "01",
    icon: Compass,
    title: "Find the right opportunity",
    description:
      "Not every problem needs AI. I look at how work moves through your business and identify where a practical change will make the biggest difference.",
    outcome: "A clear, prioritized plan",
  },
  {
    number: "02",
    icon: Workflow,
    title: "Build tools that save time",
    description:
      "I create simple systems that can organize information, prepare routine work, and connect the software your team already uses.",
    outcome: "Less repetitive work",
  },
  {
    number: "03",
    icon: MessagesSquare,
    title: "Help your people feel confident",
    description:
      "A useful tool only matters if people can use it. I explain everything clearly, train your team, and improve the system based on real feedback.",
    outcome: "Support beyond launch day",
  },
];

export default function Services() {
  return (
    <section id="services" className="section services-section">
      <div className="container">
        <div className="section-heading split-heading">
          <div>
            <p className="section-kicker">How I help</p>
            <h2>Start with the work—not the technology.</h2>
          </div>
          <p>
            You do not need to know which AI tool to choose. Bring me the slow, frustrating,
            or repetitive part of your day, and we’ll work forward from there.
          </p>
        </div>

        <div className="service-grid">
          {services.map((service) => {
            const Icon = service.icon;
            return (
              <article className="service-card" key={service.title}>
                <div className="card-topline">
                  <span>{service.number}</span>
                  <div className="service-icon"><Icon size={23} strokeWidth={1.8} /></div>
                </div>
                <h3>{service.title}</h3>
                <p>{service.description}</p>
                <div className="card-outcome"><span /><strong>{service.outcome}</strong></div>
              </article>
            );
          })}
        </div>
      </div>
    </section>
  );
}
