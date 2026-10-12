import { ArrowUpRight, Code2 } from "lucide-react";
import { useState } from "react";
import type { KeyboardEvent } from "react";

const examples = [
  {
    file: "workflow.ts",
    label: "Automate a workflow",
    detail: "Turn a customer request into a clear next step. Connect the systems you already use, and let the repetitive work take care of itself.",
    code: `// Less busywork. More forward motion.
type Request = {
  customer: string;
  project: string;
};

export async function startProject(request: Request) {
  const response = await fetch("/api/projects", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!response.ok) throw new Error("Please retry");
  return response.json();
}`,
    summary: "INPUT → WORKFLOW → ACTION",
  },
  {
    file: "integration.ts",
    label: "Make your data useful",
    detail: "Give scattered information a single place to land. Custom APIs and integrations connect your tools to a clearer view of your business.",
    code: `// Your tools, working together.
type Order = { total: number; status: string };

export async function getOverview() {
  const response = await fetch("/api/orders");
  if (!response.ok) throw new Error("Try again");

  const orders: Order[] = await response.json();
  const completed = orders.filter(
    order => order.status === "complete"
  );

  return {
    count: completed.length,
    revenue: completed.reduce((sum, o) => sum + o.total, 0),
  };
}`,
    summary: "DATA → CONTEXT → CLARITY",
  },
  {
    file: "health.ts",
    label: "Build for the long run",
    detail: "A launch is a beginning. Visibility into your software, thoughtful maintenance, and ongoing improvements keep it useful as your business changes.",
    code: `// Know how your systems are doing.
export async function checkHealth(url: string) {
  const started = performance.now();

  try {
    const response = await fetch(url, {
      signal: AbortSignal.timeout(5000),
    });

    return {
      healthy: response.ok,
      latency: Math.round(performance.now() - started),
    };
  } catch {
    return { healthy: false, latency: null };
  }
}`,
    summary: "DEPLOY → OBSERVE → IMPROVE",
  },
];

function highlight(line: string) {
  const tokens = line.split(/(\/\/.*$|"[^"]*"|\b(?:export|async|function|const|await|return|if|throw|new|try|catch|type|true|false|null|number|string)\b|\b\d+\b)/g);
  return tokens.map((token, index) => {
    const kind = token.startsWith("//") ? "comment" : token.startsWith('"') ? "string" : /^(export|async|function|const|await|return|if|throw|new|try|catch|type)$/.test(token) ? "keyword" : /^(true|false|null|number|string|\d+)$/.test(token) ? "value" : "plain";
    return <span className={`syntax-${kind}`} key={index}>{token}</span>;
  });
}

export default function Industries() {
  const [active, setActive] = useState(0);
  const example = examples[active];

  function handleTabKey(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    const next = event.key === "ArrowRight" ? (index + 1) % examples.length
      : event.key === "ArrowLeft" ? (index + examples.length - 1) % examples.length
      : event.key === "Home" ? 0 : event.key === "End" ? examples.length - 1 : null;
    if (next === null) return;
    event.preventDefault();
    setActive(next);
    document.getElementById(`example-tab-${next}`)?.focus();
  }

  return (
    <section className="section examples-section" aria-labelledby="examples-title">
      <div className="container examples-layout">
        <div className="examples-intro">
          <p className="section-kicker">02 / Under the hood</p>
          <h2 id="examples-title">Real problems.<br /><span>Working code.</span></h2>
          <p>The interesting part is what the software makes possible. Here’s a small look at how I think about building it.</p>
          <div className="example-description" aria-live="polite">
            <span className="example-number">0{active + 1} /</span>
            <h3>{example.label}</h3><p>{example.detail}</p>
          </div>
          <a href="#contact" className="text-link">What could we build for you? <ArrowUpRight size={17} aria-hidden="true" /></a>
        </div>
        <div className="code-window">
          <div className="code-topbar"><span><Code2 size={15} aria-hidden="true" /> A LITTLE IMPLEMENTATION</span><span>TS</span></div>
          <div className="code-tabs" role="tablist" aria-label="Software examples">
            {examples.map((item, index) => (
              <button key={item.file} id={`example-tab-${index}`} role="tab" type="button"
                aria-selected={active === index} aria-controls="example-panel" tabIndex={active === index ? 0 : -1}
                onClick={() => setActive(index)} onKeyDown={(event) => handleTabKey(event, index)}>
                {item.file}
              </button>
            ))}
          </div>
          <div id="example-panel" role="tabpanel" aria-labelledby={`example-tab-${active}`} tabIndex={0} className="code-panel">
            <pre><code>{example.code.split("\n").map((line, index) => (
              <span className="code-line" key={index}><span className="line-number" aria-hidden="true">{String(index + 1).padStart(2, "0")}</span><span>{highlight(line)}{"\n"}</span></span>
            ))}</code></pre>
          </div>
          <div className="code-status"><span>{example.summary}</span><span>ILLUSTRATIVE TYPESCRIPT</span></div>
        </div>
      </div>
    </section>
  );
}
