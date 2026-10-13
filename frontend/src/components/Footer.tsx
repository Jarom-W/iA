import { ArrowUpRight } from "lucide-react";
import Brand from "./Brand";
import { business } from "../content/site";
import { GitHubIcon, LinkedInIcon } from "./SocialIcons";

export default function Footer() {
  return (
    <footer className="site-footer">
      <div className="container footer-main">
        <div><Brand className="footer-brand" /><p>Business clarity. Practical technology.</p></div>
        <nav aria-label="Footer navigation">
          <a href="/contact/">Contact <ArrowUpRight size={13} aria-hidden="true" /></a>
        </nav>
        <div className="footer-socials" aria-label="Connect with Jarom Wardwell">
          <a href={business.github} target="_blank" rel="noreferrer" aria-label="Jarom Wardwell on GitHub"><GitHubIcon size={19} /></a>
          <a href={business.linkedin} target="_blank" rel="noreferrer" aria-label="Jarom Wardwell on LinkedIn"><LinkedInIcon size={19} /></a>
        </div>
      </div>
      <div className="container footer-bottom"><span>© {new Date().getFullYear()} {business.legalName}</span><a href="#main-content">BACK TO TOP ↑</a></div>
    </footer>
  );
}
