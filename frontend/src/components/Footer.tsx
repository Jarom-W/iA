import { ArrowUpRight } from "lucide-react";

export default function Footer() {
  return (
    <footer className="site-footer">
      <div className="container footer-main">
        <div>
          <a href="#top" className="brand footer-brand">
            <span className="brand-mark" aria-hidden="true"><span /><span /></span>
            <span className="brand-name">Inflection <span>Architectures</span></span>
          </a>
          <p>Practical AI. Clear guidance. More time for people.</p>
        </div>
        <nav aria-label="Footer navigation">
          <a href="#services">How I help</a>
          <a href="#process">What to expect</a>
          <a href="#about">About</a>
          <a href="#contact">Contact</a>
        </nav>
        <a
          href="https://www.linkedin.com/in/jarom-wardwell-9b8121214"
          target="_blank"
          rel="noreferrer"
          className="linkedin-link"
        >
          LinkedIn <ArrowUpRight size={16} />
        </a>
      </div>
      <div className="container footer-bottom">
        <span>© {new Date().getFullYear()} Inflection Architectures LLC</span>
        <span>People-first technology</span>
      </div>
    </footer>
  );
}
