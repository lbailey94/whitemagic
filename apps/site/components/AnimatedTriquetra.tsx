import { cn } from "@/lib/utils";
import { neoStore } from "@/store/neoStore";

/**
 * Animated triquetra mark — spawn sequence edition.
 * 1. Secondary (inner, r=20) appears first with draw-on.
 * 2. Primary (outer, r=40) spawns ~3s later with draw-on.
 * 3. Secondary fades out after primary finishes (~5s).
 * 4. Ripples and center dot appear with the primary.
 */
export function AnimatedTriquetra({
  className,
  rainbow = false,
  rainbowSpeed = 8,
  fixedColor,
}: {
  className?: string;
  rainbow?: boolean;
  rainbowSpeed?: number;
  fixedColor?: string;
}) {
  const svgStyle: React.CSSProperties = {};
  if (fixedColor) {
    svgStyle.color = fixedColor;
  } else if (rainbow) {
    svgStyle.animationDuration = `${rainbowSpeed}s`;
  }

  const dnaColors = neoStore.dnaActive ? neoStore.dnaColors : null;
  const circleStroke = (idx: number) =>
    dnaColors ? `hsl(${dnaColors[idx].hue}, ${dnaColors[idx].sat}%, ${dnaColors[idx].lit}%)` : "currentColor";

  return (
    <svg
      viewBox="0 0 200 200"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      className={cn(
        "h-full w-full",
        !fixedColor && !neoStore.dnaActive && rainbow && "triquetra-rainbow-animated",
        !fixedColor && !neoStore.dnaActive && !rainbow && "text-lavender",
        className,
      )}
      style={svgStyle}
    >
      <g className="triquetra-spin">
        {/* Secondary — small inner triquetra, appears first, fades away */}
        <g className="triquetra-secondary">
          <circle
            cx="100"
            cy="76.9"
            r="20"
            fill="none"
            stroke={circleStroke(0)}
            strokeWidth="1.5"
            className="triquetra-inner"
            style={{ animationDelay: "0ms" }}
          />
          <circle
            cx="80"
            cy="111.55"
            r="20"
            fill="none"
            stroke={circleStroke(1)}
            strokeWidth="1.5"
            className="triquetra-inner"
            style={{ animationDelay: "300ms" }}
          />
          <circle
            cx="120"
            cy="111.55"
            r="20"
            fill="none"
            stroke={circleStroke(2)}
            strokeWidth="1.5"
            className="triquetra-inner"
            style={{ animationDelay: "600ms" }}
          />
          <circle
            cx="100"
            cy="100"
            r="1.25"
            fill={dnaColors ? circleStroke(0) : "currentColor"}
            className="triquetra-inner-dot"
            style={{ animationDelay: "900ms" }}
          />
        </g>

        {/* Primary — large outer triquetra, spawns after 3s */}
        <g className="triquetra-primary">
          <circle
            cx="100"
            cy="76.9"
            r="40"
            fill="none"
            stroke={circleStroke(0)}
            strokeWidth="1.5"
            className="triquetra-outer"
            style={{ animationDelay: "3000ms" }}
          />
          <circle
            cx="80"
            cy="111.55"
            r="40"
            fill="none"
            stroke={circleStroke(1)}
            strokeWidth="1.5"
            className="triquetra-outer"
            style={{ animationDelay: "3300ms" }}
          />
          <circle
            cx="120"
            cy="111.55"
            r="40"
            fill="none"
            stroke={circleStroke(2)}
            strokeWidth="1.5"
            className="triquetra-outer"
            style={{ animationDelay: "3600ms" }}
          />
        </g>

        {/* Ripples — appear with primary */}
        <g className="triquetra-primary">
          <circle
            cx="100"
            cy="100"
            r="3"
            fill="none"
            stroke={dnaColors ? circleStroke(0) : "currentColor"}
            strokeWidth="0.5"
            className="triquetra-ripple"
            style={{ animationDelay: "4.5s" }}
          />
          <circle
            cx="100"
            cy="100"
            r="3"
            fill="none"
            stroke={dnaColors ? circleStroke(1) : "currentColor"}
            strokeWidth="0.5"
            className="triquetra-ripple"
            style={{ animationDelay: "4.81s" }}
          />
          <circle
            cx="100"
            cy="100"
            r="3"
            fill="none"
            stroke={dnaColors ? circleStroke(2) : "currentColor"}
            strokeWidth="0.5"
            className="triquetra-ripple"
            style={{ animationDelay: "5.12s" }}
          />
        </g>

        {/* Center dot — primary */}
        <circle
          cx="100"
          cy="100"
          r="2.5"
          fill={dnaColors ? circleStroke(1) : "currentColor"}
          className="triquetra-outer-dot"
          style={{ animationDelay: "4400ms" }}
        />
      </g>
    </svg>
  );
}
