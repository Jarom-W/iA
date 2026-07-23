import { Menu, X } from "lucide-react";
import { useState } from "react";

const links = [
  { name: "How I help", href: "#services" },
  { name: "What to expect", href: "#process" },
  { name: "About", href: "#about" },
];

function BrandMark() {
  return (
    <span className="brand-mark" aria-hidden="true">
      <span />
      <span />
    </span>
  );
}

export default function Navbar() {
  const [open, setOpen] = useState(false);

  return (
    <header className="site-header">
      <nav className="container nav-shell" aria-label="Main navigation">
        <a href="#top" className="brand" aria-label="Inflection Architectures home">
          <BrandMark />
          <span className="brand-name">
            Inflection <span>Architectures</span>
          </span>
        </a>

        <div className="desktop-nav">
          {links.map((link) => (
            <a key={link.name} href={link.href}>
              {link.name}
            </a>
          ))}
          <a href="#contact" className="button button-small button-dark">
            Start a conversation
          </a>
        </div>

        <button
          type="button"
          onClick={() => setOpen((value) => !value)}
          className="menu-button"
          aria-label={open ? "Close navigation" : "Open navigation"}
          aria-expanded={open}
        >
          {open ? <X size={22} /> : <Menu size={22} />}
        </button>
      </nav>

      {open && (
        <div className="mobile-nav">
          <div className="container">
            {links.map((link) => (
              <a key={link.name} href={link.href} onClick={() => setOpen(false)}>
                {link.name}
              </a>
            ))}
            <a href="#contact" onClick={() => setOpen(false)} className="button button-dark">
              Start a conversation
            </a>
          </div>
        </div>
      )}
    </header>
  );
}
