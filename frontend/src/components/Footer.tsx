import { ArrowUpRight } from "lucide-react";
import Brand from "./Brand";
import { GitHubIcon, LinkedInIcon } from "./SocialIcons";

export default function Footer() {
  return (
    <footer className="site-footer">
      <div className="container footer-main">
        <div><Brand className="footer-brand" /><p>Thoughtfully built. Continuously improved.</p></div>
        <nav aria-label="Footer navigation">
          <a href="/#services">Capabilities</a><a href="/#process">Approach</a>
          <a href="/#about">About</a>
          <a href="/#contact">Contact <ArrowUpRight size={13} aria-hidden="true" /></a>
        </nav>
        <div className="footer-socials" aria-label="Connect with Jarom Wardwell">
          <a href="https://github.com/Jarom-W" target="_blank" rel="noreferrer" aria-label="Jarom Wardwell on GitHub"><GitHubIcon size={19} /></a>
          <a href="https://www.linkedin.com/in/jarom-wardwell-9b8121214" target="_blank" rel="noreferrer" aria-label="Jarom Wardwell on LinkedIn"><LinkedInIcon size={19} /></a>
        </div>
      </div>
      <div className="container footer-bottom"><span>© {new Date().getFullYear()} Inflection Architectures LLC</span><a href="/#top">BACK TO TOP ↑</a></div>
    </footer>
  );
}
