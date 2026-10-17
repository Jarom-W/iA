// Use the same artwork throughout the reveal so the initial [i never jumps.
export default function Brand({ className = "" }: { className?: string }) {
  return (
    <a href="/" className={`brand ${className}`} aria-label="Inflection Architectures home">
      <span className="brand-reveal" aria-hidden="true">
        <svg className="brand-banner" viewBox="76 220 2030 225" focusable="false">
          <image href="/banner.png?v=25b8b0" width="2172" height="724" />
          <circle cx="1341" cy="269" r="18" fill="#25b8b0" />
        </svg>
      </span>
      <svg className="brand-bracket" viewBox="2030 220 76 225" aria-hidden="true" focusable="false">
        <image href="/banner.png?v=25b8b0" width="2172" height="724" />
      </svg>
    </a>
  );
}
