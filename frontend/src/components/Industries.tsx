import { FileText, Headphones, Search, Send } from "lucide-react";

const examples = [
  {
    icon: FileText,
    title: "Paperwork that piles up",
    description: "Summarize documents, organize details, and prepare routine reports.",
  },
  {
    icon: Search,
    title: "Answers that are hard to find",
    description: "Give your team a faster way to find policies, procedures, and company knowledge.",
  },
  {
    icon: Send,
    title: "Follow-up that takes too long",
    description: "Prepare thoughtful emails, meeting notes, and next steps for a person to review.",
  },
  {
    icon: Headphones,
    title: "Questions your team repeats",
    description: "Create helpful assistants for common customer or employee questions.",
  },
];

export default function Industries() {
  return (
    <section className="section examples-section" aria-labelledby="examples-title">
      <div className="container examples-layout">
        <div className="examples-intro">
          <p className="section-kicker light">Where AI can help</p>
          <h2 id="examples-title">Does any of this sound familiar?</h2>
          <p>
            Good AI projects usually begin with an ordinary annoyance. These are a few of
            the places where small changes can give time back to your team.
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
