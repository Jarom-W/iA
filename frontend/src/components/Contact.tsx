import { useRef, useState } from "react";
import type { FormEvent } from "react";
import { ArrowUpRight, CheckCircle2, Mail } from "lucide-react";
import { business } from "../content/site";

type FormStatus = "idle" | "sending" | "sent" | "error";
const fieldNames = ["name", "email", "company", "website", "message"] as const;
type FieldName = typeof fieldNames[number];
type Errors = Partial<Record<FieldName, string>>;

export default function Contact() {
  const [status, setStatus] = useState<FormStatus>("idle");
  const [errors, setErrors] = useState<Errors>({});
  const formRef = useRef<HTMLFormElement>(null);
  const successRef = useRef<HTMLHeadingElement>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (status === "sending") return;
    const form = event.currentTarget;
    const data = new FormData(form);
    const nextErrors: Errors = {};
    for (const name of fieldNames) {
      const value = String(data.get(name) ?? "").trim();
      data.set(name, value);
      if (name !== "website" && !value) nextErrors[name] = name === "message" ? "Describe what you would like to improve." : `Enter your ${name === "company" ? "business name" : name}.`;
    }
    if (data.get("email") && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(data.get("email")))) nextErrors.email = "Enter a valid email address.";
    if (data.get("website")) {
      try {
        const url = new URL(String(data.get("website")));
        if (!["http:", "https:"].includes(url.protocol)) throw new Error();
      } catch { nextErrors.website = "Enter a website address beginning with https:// or http://."; }
    }
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length) {
      const name = fieldNames.find(field => nextErrors[field]);
      (form.elements.namedItem(name!) as HTMLElement)?.focus();
      return;
    }
    setStatus("sending");
    try {
      const response = await fetch(business.contactEndpoint, {
        method: "POST", headers: { Accept: "application/json" }, body: data,
        signal: AbortSignal.timeout(15_000),
      });
      const result: unknown = await response.json();
      if (!response.ok || typeof result !== "object" || result === null || !("success" in result) || (result.success !== true && result.success !== "true")) {
        throw new Error("The submission was not accepted.");
      }
      form.reset();
      setStatus("sent");
      window.requestAnimationFrame(() => successRef.current?.focus());
    } catch { setStatus("error"); }
  }
  function clearError(name: FieldName) {
    if (errors[name]) setErrors(previous => ({ ...previous, [name]: undefined }));
  }
  function errorMessage(name: FieldName) {
    return errors[name] ? <span className="field-error" id={`contact-${name}-error`}>{errors[name]}</span> : null;
  }
  const fieldProps = (name: FieldName) => ({
    id: `contact-${name}`, name, "aria-invalid": Boolean(errors[name]),
    "aria-describedby": errors[name] ? `contact-${name}-error` : undefined,
    onChange: () => clearError(name),
  });

  return (
    <section id="contact" className="section contact-section" aria-labelledby="contact-title">
      <div className="container contact-layout">
        <div className="contact-copy">
          <p className="section-kicker">08 / Start with a conversation</p>
          <h2 id="contact-title">What would you like<br /><span>to work better?</span></h2>
          <p>Tell me about your business and the problem on your mind. A website, a recurring bottleneck, a cost you want to understand, or a decision you need to make.</p>
          <p>We’ll start with a short fit conversation. Any assessment or project work is scoped and priced before it begins.</p>
          <a href={`mailto:${business.email}`} className="email-link"><span><Mail size={20} aria-hidden="true" /></span><span><small>Prefer email?</small><strong>{business.email}</strong></span></a>
        </div>
        <div className="form-card">
          {status === "sent" ? <div className="success-message" role="status"><CheckCircle2 size={38} aria-hidden="true" /><h3 ref={successRef} tabIndex={-1}>Thanks for reaching out.</h3><p>Your inquiry was accepted. I’ll reply using the email you provided.</p><button type="button" className="text-link" onClick={() => { setStatus("idle"); window.requestAnimationFrame(() => formRef.current?.querySelector<HTMLInputElement>("#contact-name")?.focus()); }}>Send another message</button></div> : (
            <form ref={formRef} onSubmit={handleSubmit} noValidate aria-busy={status === "sending"}>
              <input type="hidden" name="_subject" value="New Inflection Architectures business inquiry" />
              <input type="hidden" name="_template" value="table" />
              <input type="text" name="_honey" className="honeypot" tabIndex={-1} autoComplete="off" aria-hidden="true" />
              <p className="form-intro">A few sentences is plenty. All fields except website are required.</p>
              <fieldset disabled={status === "sending"}><legend className="sr-only">Your business inquiry</legend>
                <div className="field-row">
                  <div className="contact-field"><label htmlFor="contact-name" id="contact-name-label">Your name<input {...fieldProps("name")} type="text" autoComplete="name" maxLength={100} required /></label>{errorMessage("name")}</div>
                  <div className="contact-field"><label htmlFor="contact-email" id="contact-email-label">Email address<input {...fieldProps("email")} type="email" autoComplete="email" maxLength={254} required /></label>{errorMessage("email")}</div>
                </div>
                <div className="contact-field"><label htmlFor="contact-company" id="contact-company-label">Business name<input {...fieldProps("company")} type="text" autoComplete="organization" maxLength={150} required /></label>{errorMessage("company")}</div>
                <div className="contact-field"><label htmlFor="contact-website" id="contact-website-label">Website <span className="optional">Optional</span><input {...fieldProps("website")} type="url" autoComplete="url" placeholder="https://yourbusiness.com" maxLength={2048} /></label>{errorMessage("website")}</div>
                <div className="contact-field"><label htmlFor="contact-message" id="contact-message-label">What would you like to improve?<textarea {...fieldProps("message")} rows={4} maxLength={4000} placeholder="A little about your business and what feels harder than it should." required /></label>{errorMessage("message")}</div>
              </fieldset>
              {status === "error" && <p className="form-error" role="alert">Your message was not confirmed. Please try again or <a href={`mailto:${business.email}`}>email {business.email}</a>. Your entries are still here.</p>}
              <button className="button button-primary submit-button" type="submit" disabled={status === "sending"}>{status === "sending" ? "Sending…" : "Send inquiry"}<ArrowUpRight size={18} aria-hidden="true" /></button>
              <p className="form-note">This form uses FormSubmit to forward your inquiry. I’ll use your details to respond. Please do not include passwords or sensitive business records.</p>
            </form>
          )}
        </div>
      </div>
    </section>
  );
}
