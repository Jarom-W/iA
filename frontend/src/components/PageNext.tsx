import { ArrowUpRight } from "lucide-react";

export default function PageNext() {
  return <section className="page-next" aria-labelledby="next-title"><div className="container">
    <div><h2 id="next-title">Start with your business.</h2><p>Tell me what you would like to work better.</p></div>
    <a href="/contact/" className="button button-primary">Let’s talk<ArrowUpRight size={18} aria-hidden="true" /></a>
  </div></section>;
}
