import Link from "next/link";

/** Site wordmark with animated triquetra mark. */
export function Wordmark({ href = "/" }: { href?: string }) {
  return (
    <Link
      href={href}
      className="triquetra-hover-pulse flex items-center gap-2.5"
    >
      <TriquetraMini />
      <span className="font-head text-lg font-semibold tracking-tight text-ink">
        WhiteMagic <span className="font-normal text-muted">Labs</span>
      </span>
    </Link>
  );
}

/**
 * 24×24 triquetra — same geometry as the hero version, scaled down.
 * Hover makes the three arcs pulse in opacity.
 */
function TriquetraMini() {
  return (
    <svg
      width="26"
      height="26"
      viewBox="0 0 200 200"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      className="text-lavender"
    >
      <circle
        cx="100"
        cy="76.9"
        r="40"
        stroke="currentColor"
        strokeWidth="8"
        className="triquetra-mini-arc"
      />
      <circle
        cx="80"
        cy="111.55"
        r="40"
        stroke="currentColor"
        strokeWidth="8"
        className="triquetra-mini-arc"
        style={{ animationDelay: "150ms" }}
      />
      <circle
        cx="120"
        cy="111.55"
        r="40"
        stroke="currentColor"
        strokeWidth="8"
        className="triquetra-mini-arc"
        style={{ animationDelay: "300ms" }}
      />
    </svg>
  );
}
