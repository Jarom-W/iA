import { faqs } from "../content/site";

export default function Faq() {
  return (
    <section className="section faq-section" aria-labelledby="faq-title">
      <div className="container faq-layout">
        <div className="section-heading"><p className="section-kicker">07 / A few practical questions</p><h2 id="faq-title">Before we<br /><span>get started.</span></h2></div>
        <div className="faq-list">{faqs.map(item => <details key={item.question}><summary>{item.question}<span aria-hidden="true">+</span></summary><p>{item.answer}</p></details>)}</div>
      </div>
    </section>
  );
}
