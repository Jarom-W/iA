import { ArrowRight, Check, Sparkles } from "lucide-react";

export default function Hero() {
  return (
    <section id="top" className="hero-section">
      <div className="hero-orb hero-orb-one" />
      <div className="hero-orb hero-orb-two" />

      <div className="container hero-layout">
        <div className="hero-copy reveal">
          <h1>
            You don’t need to understand AI, you just need it to do the work you <em>hate.</em>
          </h1>
          <p className="hero-lede">
            I help small-business owners turn tools like Claude into a useful business
            companion—connected to the apps, information, and day-to-day work that already
            run their business.
          </p>
          <div className="hero-actions">
            <a href="#contact" className="button button-primary">
              Tell me what feels stuck <ArrowRight size={18} aria-hidden="true" />
            </a>
            <a href="#services" className="text-link">
              See how I can help
            </a>
          </div>
          <p className="reassurance">
            Bring the bottleneck, not a technical plan. I’ll handle the setup.
          </p>
        </div>

        <div className="hero-visual reveal reveal-delay" aria-label="Example of a simplified workday">
          <div className="visual-topline">
            <span>Your business, connected</span>
            <span className="live-dot">Set up for you</span>
          </div>
          <div className="workflow-card workflow-main">
            <div className="workflow-icon"><Sparkles size={20} /></div>
            <div>
              <span className="workflow-label">Ask in plain English</span>
              <strong>Which orders need my attention today?</strong>
            </div>
            <span className="complete-check"><Check size={15} /></span>
          </div>
          <div className="workflow-line" />
          <div className="workflow-grid">
            <div className="workflow-card">
              <span className="mini-number">01</span>
              <strong>Business context gathered</strong>
              <small>From the apps you already rely on</small>
            </div>
            <div className="workflow-card">
              <span className="mini-number">02</span>
              <strong>A useful answer returned</strong>
              <small>Ready for your judgment and action</small>
            </div>
          </div>
          <div className="time-saved">
            <span>Less digging. More deciding.</span>
            <div><i /><i /><i /><i /></div>
          </div>
        </div>
      </div>

      <div className="container trust-strip">
        <span>No new platform to learn</span>
        <span>Connected to your real business</span>
        <span>Custom setup without the technical headache</span>
      </div>
    </section>
  );
}
