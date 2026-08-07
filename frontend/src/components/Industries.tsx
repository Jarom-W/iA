import { BarChart3, Inbox, Search, Send } from "lucide-react";

const examples = [
  {
    icon: Search,
    title: "Questions that take an hour to answer",
    description: "Ask what sold, what is stuck, or what needs attention without digging through three different apps.",
  },
  {
    icon: Inbox,
    title: "An inbox that runs your day",
    description: "Summarize conversations, surface important requests, and prepare thoughtful replies for your review.",
  },
  {
    icon: Send,
    title: "Follow-up that keeps slipping",
    description: "Turn meetings, orders, and customer conversations into clear next steps while they are still fresh.",
  },
  {
    icon: BarChart3,
    title: "Numbers without a clear story",
    description: "Explore sales, costs, and operations in plain English so you can spot patterns and make better calls.",
  },
];

export default function Industries() {
  return (
    <section className="section examples-section" aria-labelledby="examples-title">
      <div className="container examples-layout">
        <div className="examples-intro">
          <p className="section-kicker light">A better daily companion</p>
          <h2 id="examples-title">What could you stop carrying alone?</h2>
          <p>
            Once your AI can see the right parts of your business, it can do far more than
            write generic copy. It can help you understand what is happening and move the
            routine work forward.
          </p>
          <a href="#contact" className="button button-light">Talk through your challenge</a>
        </div>

        <div className="example-list">
          {examples.map((example) => {
            const Icon = example.icon;
            return (
              <article key={example.title} className="example-row">
                <div className="example-icon"><Icon size={22} strokeWidth={1.8} /></div>
                <div>
                  <h3>{example.title}</h3>
                  <p>{example.description}</p>
                </div>
              </article>
            );
          })}
        </div>
      </div>
    </section>
  );
}
