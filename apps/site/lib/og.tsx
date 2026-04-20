/**
 * Shared OG-image renderer. Per-route `opengraph-image.tsx` files call
 * `renderOg({ eyebrow, title, tagline, footerRight })` to get a
 * consistent 1200x630 PNG via `next/og`.
 *
 * Edge-runtime. Fonts are system serif/mono — no external font fetches.
 */
import { ImageResponse } from "next/og";

export const OG_SIZE = { width: 1200, height: 630 };
export const OG_CONTENT_TYPE = "image/png";

export interface OgCopy {
  eyebrow?: string;
  title: string;
  tagline?: string;
  /** Right-hand footer label, e.g. "Pricing" or "Agent Governance". */
  footerRight?: string;
  /** Override accent color (defaults to lavender). */
  accent?: string;
}

export function renderOg(copy: OgCopy): ImageResponse {
  const accent = copy.accent ?? "#b8a9d4";
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: "72px",
          background:
            "linear-gradient(135deg, #1a1410 0%, #252019 50%, #2d2720 100%)",
          color: "#e0d8ce",
          fontFamily: "serif",
          position: "relative",
        }}
      >
        <svg
          width="120"
          height="120"
          viewBox="0 0 24 24"
          style={{ position: "absolute", top: 60, right: 60 }}
        >
          <circle
            cx="12"
            cy="9"
            r="5"
            fill="none"
            stroke={accent}
            strokeWidth="1"
            opacity="0.9"
          />
          <circle
            cx="8"
            cy="15"
            r="5"
            fill="none"
            stroke={accent}
            strokeWidth="1"
            opacity="0.6"
          />
          <circle
            cx="16"
            cy="15"
            r="5"
            fill="none"
            stroke={accent}
            strokeWidth="1"
            opacity="0.6"
          />
        </svg>

        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          <div
            style={{
              fontSize: "22px",
              textTransform: "uppercase",
              letterSpacing: "0.2em",
              color: accent,
              fontFamily: "monospace",
            }}
          >
            WhiteMagic Labs
          </div>
          {copy.eyebrow ? (
            <div
              style={{
                fontSize: "20px",
                color: "#9a9088",
                fontFamily: "monospace",
                letterSpacing: "0.12em",
                textTransform: "uppercase",
              }}
            >
              {copy.eyebrow}
            </div>
          ) : null}
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
          <div
            style={{
              display: "flex",
              fontSize: "76px",
              lineHeight: 1.05,
              fontWeight: 600,
              color: "#f5f0e8",
              letterSpacing: "-0.02em",
              maxWidth: "1040px",
            }}
          >
            {copy.title}
          </div>
          {copy.tagline ? (
            <div
              style={{
                display: "flex",
                fontSize: "28px",
                lineHeight: 1.4,
                color: "#b0a498",
                maxWidth: "960px",
              }}
            >
              {copy.tagline}
            </div>
          ) : null}
        </div>

        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            borderTop: "1px solid #3d3630",
            paddingTop: "20px",
            fontSize: "22px",
            color: "#9a9088",
            fontFamily: "monospace",
            textTransform: "uppercase",
            letterSpacing: "0.15em",
          }}
        >
          <span>whitemagic.dev</span>
          {copy.footerRight ? (
            <span style={{ color: accent }}>{copy.footerRight}</span>
          ) : null}
        </div>
      </div>
    ),
    { ...OG_SIZE },
  );
}
