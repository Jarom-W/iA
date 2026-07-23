import { ArrowRight, Check, Sparkles } from "lucide-react";

export default function Hero() {
  return (
    <section id="top" className="hero-section">
      <div className="hero-orb hero-orb-one" />
      <div className="hero-orb hero-orb-two" />

      <div className="container hero-layout">
        <div className="hero-copy reveal">
          <div className="eyebrow">
            <Sparkles size={15} aria-hidden="true" />
            Practical AI for real businesses
          </div>
          <h1>
            AI should make work feel <em>lighter.</em>
          </h1>
          <p className="hero-lede">
            I help small businesses use AI to cut busywork, find information faster, and
            give their people more time for the work that matters.
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
            No technical background needed. No pressure. Just a useful first conversation.
          </p>
        </div>

        <div className="hero-visual reveal reveal-delay" aria-label="Example of a simplified workday">
          <div className="visual-topline">
            <span>A calmer workday</span>
            <span className="live-dot">Built for your team</span>
          </div>
          <div className="workflow-card workflow-main">
            <div className="workflow-icon"><Sparkles size={20} /></div>
            <div>
              <span className="workflow-label">AI handles the repeatable part</span>
              <strong>Customer follow-up prepared</strong>
            </div>
            <span className="complete-check"><Check size={15} /></span>
          </div>
          <div className="workflow-line" />
          <div className="workflow-grid">
            <div className="workflow-card">
              <span className="mini-number">01</span>
              <strong>Information gathered</strong>
              <small>From the tools you already use</small>
            </div>
            <div className="workflow-card">
              <span className="mini-number">02</span>
              <strong>Your team reviews</strong>
              <small>People stay in control</small>
            </div>
          </div>
          <div className="time-saved">
            <span>Time returned to your week</span>
            <div><i /><i /><i /><i /></div>
          </div>
        </div>
      </div>

      <div className="container trust-strip">
        <span>Plain-English guidance</span>
        <span>Built around your people</span>
        <span>Useful results—not AI hype</span>
      </div>
    </section>
  );
}
