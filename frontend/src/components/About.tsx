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
          <p className="section-kicker">About / A person, not a platform</p>
          <h1 id="about-title">Hi, I’m Jarom.<br /><span>I look at the whole business.</span></h1>
          <p>My background brings together finance and economics, software development, and startup operations. I started Inflection Architectures to help owners understand a problem, choose a sensible response, and put it into practice.</p>
          <p>I look at cost, expected benefit, maintainability, and operational fit before choosing technology. Sometimes the useful answer is a better website. Sometimes it is a clearer forecast, fewer tools, or a workflow that no longer depends on memory.</p>
          <h2 className="small-label">What you can expect from me</h2>
          <ul className="working-practices">{workingPractices.map(practice => <li key={practice}>{practice}</li>)}</ul>
        </div>
      </div>
    </section>
  );
}
