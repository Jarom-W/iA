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
      <svg className="brand-icon" viewBox="198 123 858 936" aria-hidden="true" focusable="false">
        <defs><filter id={weightFilter} x="0" y="0" width="1254" height="1254" filterUnits="userSpaceOnUse" colorInterpolationFilters="sRGB">
          <feMorphology in="SourceGraphic" operator="dilate" radius="10" />
        </filter></defs>
        <image href="/logo.png" width="1254" height="1254" filter={`url(#${weightFilter})`} />
      </svg>
      <span className="brand-wordmark" aria-hidden="true">
        <Wordmark className="brand-name-wide" viewBox="509 282 1584 125" />
        <span className="brand-name-stacked">
          <Wordmark className="brand-name-first" viewBox="509 282 620 125" />
          <Wordmark className="brand-name-second" viewBox="1171 282 922 125" />
        </span>
      </span>
    </a>
  );
}
