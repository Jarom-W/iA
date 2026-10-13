import { ArrowUpRight } from "lucide-react";
import Hero from "../components/Hero";
import NextStepCurves from "../components/NextStepCurves";

const paths = [
  { name: "Services", href: "/services/", label: "Find the right help", copy: "Business advice, a better website, or a practical improvement to the systems behind your work." },
  { name: "Approach", href: "/approach/", label: "Understand the process", copy: "Understand the problem, compare sensible options, and put an agreed improvement into practice." },
  { name: "Pricing", href: "/pricing/", label: "Know where to start", copy: "Clear project starting points and optional support, with written scope and agreed boundaries." },
];

export default function HomePage() {
  return <><Hero /><section className="section home-paths" aria-labelledby="home-paths-title"><NextStepCurves /><div className="container">
    <div className="section-heading"><p className="section-kicker">Don't let a subtle leak sink a strong business.</p><h2 id="home-paths-title">A clearer next step.</h2></div>
    <div className="home-path-links">{paths.map(path => <a className="home-path-link" key={path.href} href={path.href}><span className="small-label">{path.label}</span><h3><span className="path-name">{path.name}</span><span className={`path-marker${path.name === "Approach" ? " approach-marker" : ""}`}><ArrowUpRight size={20} aria-hidden="true" /></span></h3><p>{path.copy}</p></a>)}</div>
  </div></section></>;
}
