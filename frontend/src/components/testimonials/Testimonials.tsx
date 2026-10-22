import { useEffect, useState } from "react";
import { Quote } from "lucide-react";

type Testimonial = {
  id: string;
  quote: string;
  name: string;
  company?: string;
  role?: string;
  service?: string;
};

const endpoint = import.meta.env.VITE_TESTIMONIALS_URL || "https://feedback.inflectionarchitectures.com/api/testimonials";

function isTestimonial(value: unknown): value is Testimonial {
  if (!value || typeof value !== "object") return false;
  const item = value as Record<string, unknown>;
  return ["id", "quote", "name"].every(key => typeof item[key] === "string" && (item[key] as string).trim().length > 0)
    && ["company", "role", "service"].every(key => item[key] === undefined || typeof item[key] === "string");
}

export default function Testimonials() {
  const [items, setItems] = useState<Testimonial[]>([]);

  useEffect(() => {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 6000);
    fetch(endpoint, { signal: controller.signal, credentials: "omit" })
      .then(response => {
        if (!response.ok) throw new Error("Testimonials unavailable");
        return response.json();
      })
      .then(data => {
        if (!controller.signal.aborted && Array.isArray(data.testimonials)) {
          setItems(data.testimonials.filter(isTestimonial).slice(0, 12));
        }
      })
      .catch(() => { /* Keep the marketing site usable if feedback hosting is unavailable. */ })
      .finally(() => window.clearTimeout(timeout));
    return () => { controller.abort(); window.clearTimeout(timeout); };
  }, []);

  if (items.length === 0) return null;

  return <section className="section testimonials-section" aria-labelledby="testimonials-title">
    <div className="container">
      <div className="section-heading testimonials-heading">
        <div><p className="section-kicker">In their words</p><h2 id="testimonials-title">The work.<br /><span>The difference it made.</span></h2></div>
        <p>Experiences shared by the people I’ve worked with.</p>
      </div>
      <div className="testimonial-grid">
        {items.map(item => <figure className="testimonial-card" key={item.id}>
          <Quote size={24} strokeWidth={1.4} aria-hidden="true" />
          {item.service && <p className="small-label testimonial-service">{item.service}</p>}
          <blockquote><p>{item.quote}</p></blockquote>
          <figcaption>
            <span className="testimonial-initial" aria-hidden="true">{Array.from(item.name.trim())[0]}</span>
            <span><strong>{item.name}</strong>{(item.role || item.company) && <span className="testimonial-attribution">{[item.role, item.company].filter(Boolean).join(" · ")}</span>}</span>
          </figcaption>
        </figure>)}
      </div>
    </div>
  </section>;
}
