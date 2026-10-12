import { useState } from "react";
import type { FormEvent } from "react";
import {
  ArrowRight,
  CheckCircle2,
  Mail,
} from "lucide-react";
import { GitHubIcon, LinkedInIcon } from "./SocialIcons";

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
      <section id="about" className="section about-section" aria-labelledby="about-title">
        <div className="container about-layout">
          <div className="founder-card">
            <img
              className="founder-portrait"
              src="/portrait.JPEG"
              alt="Jarom Wardwell with his wife"
              loading="lazy"
            />
            <div className="founder-details">
              <div>
                <strong>Jarom Wardwell</strong>
                <span>Founder &amp; software engineer</span>
              </div>
              <div className="founder-socials" aria-label="Jarom Wardwell on social media">
                <a
                  href="https://www.linkedin.com/in/jarom-wardwell-9b8121214"
                  target="_blank"
                  rel="noreferrer"
                  aria-label="Connect with Jarom Wardwell on LinkedIn"
                  title="LinkedIn"
                >
                  <LinkedInIcon size={19} />
                </a>
                <a
                  href="https://github.com/Jarom-W"
                  target="_blank"
                  rel="noreferrer"
                  aria-label="View Jarom Wardwell on GitHub"
                  title="GitHub"
                >
                  <GitHubIcon size={19} />
                </a>
              </div>
            </div>
          </div>
          <div className="about-copy">
            <p className="section-kicker">04 / The person behind the code</p>
            <h2 id="about-title">Hi, I’m Jarom.<br /><span>I build things that work.</span></h2>
            <p>
              I run Inflection Architectures, an independent software contracting company.
              I work directly with people and businesses to turn a problem, a workflow,
              or an idea into useful software.
            </p>
            <p>From custom applications and AI integrations to the infrastructure behind them,
              I care about the details that make a system useful long after it ships.</p>
            <div className="about-values">
              <span><CheckCircle2 size={16} aria-hidden="true" /> You work directly with me</span>
              <span><CheckCircle2 size={16} aria-hidden="true" /> Clear scope and honest communication</span>
              <span><CheckCircle2 size={16} aria-hidden="true" /> A partner beyond the first release</span>
            </div>
          </div>
        </div>
      </section>

      <section id="contact" className="section contact-section" aria-labelledby="contact-title">
        <div className="container contact-layout">
          <div className="contact-copy">
            <p className="section-kicker">05 / Start a conversation</p>
            <h2 id="contact-title">Something in mind?<br /><span>Let’s build it.</span></h2>
            <p>
              An idea, a bottleneck, or a system that needs a better foundation.
              Tell me what you’re working on. We’ll figure out the next step together.
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
                <input type="text" name="_honey" className="honeypot" tabIndex={-1} autoComplete="off" aria-hidden="true" />

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
                    placeholder="What would you like to build, improve, or get off your plate?"
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
