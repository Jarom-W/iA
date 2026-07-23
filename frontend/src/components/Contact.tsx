import { useState } from "react";
import type { FormEvent } from "react";
import { ArrowRight, CheckCircle2, Mail, MessageCircle } from "lucide-react";

type FormStatus = "idle" | "sending" | "sent" | "error";

export default function Contact() {
  const [status, setStatus] = useState<FormStatus>("idle");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    setStatus("sending");

    try {
      const response = await fetch(
        "https://formsubmit.co/ajax/jaromwardwell@gmail.com",
        {
          method: "POST",
          headers: { Accept: "application/json" },
          body: new FormData(form),
        },
      );

      if (!response.ok) throw new Error("The form could not be submitted.");
      form.reset();
      setStatus("sent");
    } catch {
      setStatus("error");
    }
  }

  return (
    <>
      <section id="about" className="about-section">
        <div className="container about-layout">
          <div className="founder-card" aria-hidden="true">
            <div className="founder-initials">JW</div>
            <div>
              <strong>Jarom Wardwell</strong>
              <span>Founder &amp; engineer</span>
            </div>
          </div>
          <div className="about-copy">
            <p className="section-kicker">A partner who speaks human</p>
            <h2>Thoughtful technology starts with understanding people.</h2>
            <p>
              I’m Jarom, founder of Inflection Architectures. I’m a software and platform
              engineer who helps businesses turn powerful technology into simple, useful
              tools. You’ll work directly with me—from our first conversation through launch.
            </p>
            <div className="about-values">
              <span><CheckCircle2 size={18} /> Direct, honest advice</span>
              <span><CheckCircle2 size={18} /> Clear communication</span>
              <span><CheckCircle2 size={18} /> Solutions built to last</span>
            </div>
          </div>
        </div>
      </section>

      <section id="contact" className="section contact-section">
        <div className="container contact-layout">
          <div className="contact-copy">
            <div className="eyebrow dark-eyebrow"><MessageCircle size={15} /> Let’s talk</div>
            <h2>What would make your workday easier?</h2>
            <p>
              You do not need a polished plan. Tell me what feels slow, repetitive, or
              frustrating, and I’ll help you think through a practical next step.
            </p>
            <a href="mailto:jaromwardwell@gmail.com" className="email-link">
              <span><Mail size={20} /></span>
              <div><small>Prefer email?</small><strong>jaromwardwell@gmail.com</strong></div>
            </a>
          </div>

          <div className="form-card">
            {status === "sent" ? (
              <div className="success-message" role="status">
                <CheckCircle2 size={48} />
                <h3>Thanks for reaching out.</h3>
                <p>Your message is on its way. I’ll get back to you soon.</p>
                <button type="button" className="text-link" onClick={() => setStatus("idle")}>
                  Send another message
                </button>
              </div>
            ) : (
              <form onSubmit={handleSubmit}>
                <input type="hidden" name="_subject" value="New Inflection Architectures inquiry" />
                <input type="hidden" name="_template" value="table" />
                <input type="text" name="_honey" className="honeypot" tabIndex={-1} autoComplete="off" />

                <div className="field-row">
                  <label>
                    Your name <span aria-hidden="true">*</span>
                    <input name="name" type="text" autoComplete="name" placeholder="Jane Smith" required />
                  </label>
                  <label>
                    Email address <span aria-hidden="true">*</span>
                    <input name="email" type="email" autoComplete="email" placeholder="jane@company.com" required />
                  </label>
                </div>
                <label>
                  Company or organization <span className="optional">Optional</span>
                  <input name="company" type="text" autoComplete="organization" placeholder="Your company" />
                </label>
                <label>
                  What would you like help with? <span aria-hidden="true">*</span>
                  <textarea
                    name="message"
                    rows={5}
                    placeholder="A few sentences is plenty. What takes too much time today?"
                    required
                  />
                </label>

                {status === "error" && (
                  <p className="form-error" role="alert">
                    Something went wrong. Please email me directly at jaromwardwell@gmail.com.
                  </p>
                )}

                <button className="button button-primary submit-button" type="submit" disabled={status === "sending"}>
                  {status === "sending" ? "Sending…" : "Send my message"}
                  {status !== "sending" && <ArrowRight size={18} />}
                </button>
                <p className="form-note">
                  I’ll use these details to respond. Please don’t include passwords or sensitive information.
                </p>
              </form>
            )}
          </div>
        </div>
      </section>
    </>
  );
}
