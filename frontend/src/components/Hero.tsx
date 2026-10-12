import { ArrowDown, ArrowUpRight } from "lucide-react";

export default function Hero() {
  return (
    <section id="top" className="hero-section" aria-labelledby="hero-title">
      <div className="container hero-layout">
        <div className="hero-copy reveal">
          <p className="eyebrow"><span className="status-dot" /> Independent software engineering</p>
          <h1 id="hero-title">Built for you.<br /><span>Built to run.</span></h1>
          <p className="hero-lede">
            Custom software for the way your business works.<br className="desktop-break" />{" "}
            From the first idea to the systems you rely on every day,
            I build it, connect it, and keep it running.
          </p>
          <div className="hero-actions">
            <a href="#contact" className="button button-primary">Start a project <ArrowUpRight size={18} aria-hidden="true" /></a>
            <a href="#services" className="text-link">Explore capabilities <ArrowDown size={16} aria-hidden="true" /></a>
          </div>
        </div>
        <div className="hero-visual reveal reveal-delay" aria-hidden="true">
          <div className="blueprint-grid" />
          <span className="blueprint-label blueprint-label-top">FIG. 01 / THE ARCHITECTURE</span>
          <span className="blueprint-cross cross-top">+</span>
          <img className="hero-mark" src="/logo.png" alt="" width="1254" height="1254" fetchPriority="high" />
          <span className="blueprint-cross cross-bottom">+</span>
          <div className="blueprint-caption"><span>FROM POSSIBILITY</span><span>TO PRODUCTION ↗</span></div>
        </div>
      </div>
      <div className="container capability-strip">
        <span><b>01 /</b> Applications &amp; platforms</span>
        <span><b>02 /</b> Automation &amp; AI</span>
        <span><b>03 /</b> Infrastructure &amp; operations</span>
        <a href="#services" aria-label="Scroll to capabilities"><ArrowDown size={18} /></a>
      </div>
    </section>
  );
}
