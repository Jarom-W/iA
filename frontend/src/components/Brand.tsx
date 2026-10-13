import { useId } from "react";

// Viewports isolate the supplied artwork; the lettering is not recreated as text.
function Wordmark({ className, viewBox }: { className: string; viewBox: string }) {
  return <svg className={className} viewBox={viewBox} aria-hidden="true" focusable="false">
    <image href="/banner.png" width="2172" height="724" />
  </svg>;
}

export default function Brand({ className = "" }: { className?: string }) {
  const weightFilter = useId();
  return (
    <a href="/" className={`brand ${className}`} aria-label="Inflection Architectures home">
      <svg className="brand-icon" viewBox="149 216 954 800" aria-hidden="true" focusable="false">
        <defs>
          <filter id={weightFilter} x="-2%" y="-2%" width="104%" height="104%" colorInterpolationFilters="sRGB">
            <feMorphology operator="dilate" radius="7" />
            <feComponentTransfer>
              <feFuncR type="linear" slope="3" intercept="-0.03" />
              <feFuncG type="linear" slope="3" intercept="-0.03" />
              <feFuncB type="linear" slope="3" intercept="-0.03" />
            </feComponentTransfer>
            {/* Keep the small-size contrast boost orange rather than yellow. */}
            <feColorMatrix type="matrix" values="1 0 0 0 0  .48 0 .52 0 0  0 0 1 0 0  0 0 0 1 0" />
          </filter>
        </defs>
        <image href="/logo.png" width="1254" height="1254" filter={`url(#${weightFilter})`} />
      </svg>
      <span className="brand-wordmark" aria-hidden="true">
        <Wordmark className="brand-name-wide" viewBox="338 270 1802 171" />
        <span className="brand-name-stacked">
          <Wordmark className="brand-name-first" viewBox="338 270 722 171" />
          <Wordmark className="brand-name-second" viewBox="1085 270 1055 171" />
        </span>
      </span>
    </a>
  );
}
