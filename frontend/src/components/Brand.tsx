export default function Brand({ className = "" }: { className?: string }) {
  return (
    <a href="/" className={`brand ${className}`} aria-label="Inflection Architectures home">
      <span className="brand-image" aria-hidden="true">
        <img src="/banner.png" alt="" width="2172" height="724" />
      </span>
    </a>
  );
}
