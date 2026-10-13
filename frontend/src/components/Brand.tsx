// Viewports isolate the supplied artwork; the lettering is not recreated as text.
function Wordmark({ className, viewBox }: { className: string; viewBox: string }) {
  return <svg className={className} viewBox={viewBox} aria-hidden="true" focusable="false">
    <image href="/banner.png" width="2172" height="724" />
  </svg>;
}

export default function Brand({ className = "" }: { className?: string }) {
  return (
    <a href="/" className={`brand ${className}`} aria-label="Inflection Architectures home">
      <svg className="brand-icon" viewBox="206 131 842 920" aria-hidden="true" focusable="false">
        <image href="/logo.png" width="1254" height="1254" />
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
