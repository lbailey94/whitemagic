import { cn } from "@/lib/utils";

/**
 * Animated triquetra mark.
 * - Three interlocking circles at equilateral-triangle vertices.
 * - Each ring passes through the centers of the other two (r = side length),
 *   which is the canonical trefoil geometry.
 * - On mount: strokes "draw" in with staggered delays.
 * - Continuous: entire group rotates once per 80 seconds (subtle).
 * - Respects prefers-reduced-motion via CSS in globals.css.
 */
export function AnimatedTriquetra({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 200 200"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      className={cn("h-full w-full text-lavender", className)}
    >
      <g className="triquetra-spin">
        <circle
          cx="100"
          cy="76.9"
          r="40"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          className="triquetra-arc"
          style={{ animationDelay: "0ms" }}
        />
        <circle
          cx="80"
          cy="111.55"
          r="40"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          className="triquetra-arc"
          style={{ animationDelay: "300ms" }}
        />
        <circle
          cx="120"
          cy="111.55"
          r="40"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          className="triquetra-arc"
          style={{ animationDelay: "600ms" }}
        />
        {/* Center dot — the still point at the intersection */}
        <circle
          cx="100"
          cy="100"
          r="2"
          fill="currentColor"
          opacity="0.6"
          className="triquetra-arc"
          style={{ animationDelay: "1100ms", strokeDasharray: "none" }}
        />
      </g>
    </svg>
  );
}
