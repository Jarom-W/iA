import { ArrowUpRight, Menu, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import Brand from "./Brand";

import { navigation as links } from "../content/site";

export default function Navbar() {
  const currentPath = window.location.pathname.replace(/\/index\.html$/, "/").replace(/\/?$/, "/");
  const [open, setOpen] = useState(false);
  const [compact, setCompact] = useState(() => window.scrollY > 64);
  const menuButton = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const onScroll = () => setCompact(window.scrollY > 64);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
        menuButton.current?.focus();
      }
    };
    const desktop = window.matchMedia("(min-width: 1081px)");
    const onResize = () => { if (desktop.matches) setOpen(false); };
    window.addEventListener("keydown", onKeyDown);
    desktop.addEventListener("change", onResize);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      desktop.removeEventListener("change", onResize);
    };
  }, [open]);

  return (
    <header className={`site-header${compact ? " is-compact" : ""}`}>
      <nav className="container nav-shell" aria-label="Main navigation">
        <Brand className="nav-brand" />
        <div className="desktop-nav">
          {links.map((link) => <a key={link.name} href={link.href} aria-current={currentPath === link.href ? "page" : undefined}>{link.name}</a>)}
          <a href="/contact/" aria-current={currentPath === "/contact/" ? "page" : undefined} className="button button-small button-outline">
            Contact <ArrowUpRight size={16} aria-hidden="true" />
          </a>
        </div>
        <button ref={menuButton} type="button" onClick={() => setOpen((value) => !value)}
          className="menu-button" aria-label={open ? "Close navigation" : "Open navigation"}
          aria-expanded={open} aria-controls="mobile-navigation">
          {open ? <X size={22} /> : <Menu size={22} />}
        </button>
      </nav>
      <div id="mobile-navigation" className="mobile-nav" hidden={!open}>
        <div className="container">
          {links.map((link) => (
            <a key={link.name} href={link.href} aria-current={currentPath === link.href ? "page" : undefined} onClick={() => setOpen(false)}>{link.name}</a>
          ))}
          <a href="/contact/" aria-current={currentPath === "/contact/" ? "page" : undefined} onClick={() => setOpen(false)} className="button button-primary">
            Contact <ArrowUpRight size={17} aria-hidden="true" />
          </a>
        </div>
      </div>
    </header>
  );
}
