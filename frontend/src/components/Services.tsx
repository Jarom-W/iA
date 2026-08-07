import { Compass, MessagesSquare, Workflow } from "lucide-react";

const services = [
  {
    number: "01",
    icon: Compass,
    title: "Start with what you hate doing",
    description:
      "Show me the work that eats your time: chasing details, answering the same questions, writing follow-ups, or trying to understand what the numbers are saying.",
    outcome: "A useful first target",
  },
  {
    number: "02",
    icon: Workflow,
    title: "Connect AI to your business",
    description:
      "I configure tools like Claude and connect them to Shopify, email, documents, and other apps you already use, using trusted connectors wherever they fit.",
    outcome: "Answers grounded in your real work",
  },
  {
    number: "03",
    icon: MessagesSquare,
    title: "Fill the gaps and make it yours",
    description:
      "When off-the-shelf connections are not enough, I can add custom connectors, memory, and business-specific instructions—then show you how to use it without the jargon.",
    outcome: "A companion that knows your business",
  },
];

export default function Services() {
  return (
    <section id="services" className="section services-section">
      <div className="container">
        <div className="section-heading split-heading">
          <div>
            <p className="section-kicker">How I help</p>
            <h2>Make the AI you already have genuinely useful.</h2>
          </div>
          <p>
            This is not a software platform or a giant transformation project. It is practical,
            one-on-one help setting up capable tools around the way your business actually works.
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
