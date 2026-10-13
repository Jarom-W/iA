import { problems } from "../content/site";

export default function Problems() {
  return (
    <section className="section problems-section" aria-labelledby="problems-title">
      <div className="container problems-layout">
        <div className="section-heading">
          <p className="section-kicker">Start with the business</p>
          <h2 id="problems-title">Where is the business<br /><span>getting stuck?</span></h2>
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
    </section>
  );
}
