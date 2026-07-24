import { GitHubIcon, LinkedInIcon } from "./SocialIcons";

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
        <div className="footer-socials" aria-label="Connect with Jarom Wardwell">
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
      <div className="container footer-bottom">
        <span>© {new Date().getFullYear()} Inflection Architectures LLC</span>
        <span>People-first technology</span>
      </div>
    </footer>
  );
}
