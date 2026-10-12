import { problems } from "../content/site";

export default function Problems() {
  return (
    <section className="section problems-section" aria-labelledby="problems-title">
      <div className="container problems-layout">
        <div className="section-heading">
          <p className="section-kicker">Start with the business</p>
          <h2 id="problems-title">Where is the business<br /><span>getting stuck?</span></h2>
          <p className="section-intro">Before choosing another tool, understand the current process and what it costs—in money, time, and attention.</p>
          <p className="audience-note">Built for established, owner-led service businesses. Especially teams of roughly 3–20 people quoting jobs, doing the work, and keeping customers moving.</p>
        </div>
        <div className="problem-list">
          {problems.map((problem, index) => (
            <article className="problem-row" key={problem.title}>
              <span className="item-index">0{index + 1}</span>
              <div><h3>{problem.title}</h3><p>{problem.description}</p></div>
            </article>
          ))}
        </div>
      </div>
      <p className="container audience-line">Landscaping. Painting. Fencing. Remodeling. Professional and B2B services.<span>Different businesses. Practical questions worth examining.</span></p>
    </section>
  );
}
