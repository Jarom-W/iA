import { business, workingPractices } from "../content/site";
import { GitHubIcon, LinkedInIcon } from "./SocialIcons";

export default function About() {
  return (
    <section id="about" className="section about-section" aria-labelledby="about-title">
      <div className="container about-layout">
        <div className="founder-card">
          <img className="founder-portrait" src="/portrait.JPEG" width="1078" height="1459" alt="Jarom Wardwell with his wife" loading="lazy" />
          <div className="founder-details"><div><strong>{business.founder}</strong><span>Founder / {business.name}</span></div><div className="founder-socials">
            <a href={business.github} target="_blank" rel="noreferrer" aria-label="Jarom Wardwell on GitHub"><GitHubIcon size={19} /></a>
            <a href={business.linkedin} target="_blank" rel="noreferrer" aria-label="Jarom Wardwell on LinkedIn"><LinkedInIcon size={19} /></a>
          </div></div>
        </div>
        <div className="about-copy">
          <p className="section-kicker">About me and my mission</p>
          <h1 id="about-title">Hello! I’m Jarom.<br /><span>Let's make it happen.</span></h1>

        <p>Rather than acting like a traditional dev shop that takes ticket orders for websites or apps, I serve as a comprehensive business engineering partner. That means evaluating your entire operation from financial modeling and workflow mechanics to custom software, autonomous AI agents, hardware integrations, and system architecture. Sometimes the right answer is integrating existing tools; other times it’s building a proprietary system tailored to your exact market. Together, we identify what your business truly requires and engineer the exact technology to make it happen.</p>
          <p>Inflection Architectures was built on a simple premise: technology should be a multiplier for your business, not just another line item. My background spans finance, economics, software engineering, and startup operations. My path began with quantitative finance, transitioned through corporate finance, and evolved inside young tech startups. After getting married to my wife, Ashley, and starting our family, I realized how critical time and leverage are for business owners. Whether your goal is to reclaim your time, scale operations, or build a company that runs without you, I bridge high-level strategy with deep technical execution to eliminate the bottlenecks holding you back.</p>

          <h2 className="small-label">What you can expect from me</h2>
          <ul className="working-practices">{workingPractices.map(practice => <li key={practice}>{practice}</li>)}</ul>
        </div>
      </div>
    </section>
  );
}
