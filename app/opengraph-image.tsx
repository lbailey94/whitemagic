import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt = "WhiteMagic Labs — Private AI deployed on your infrastructure";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default async function Image() {
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
        {/* Accent mark */}
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
            stroke="#b8a9d4"
            strokeWidth="1"
            opacity="0.9"
          />
          <circle
            cx="8"
            cy="15"
            r="5"
            fill="none"
            stroke="#b8a9d4"
            strokeWidth="1"
            opacity="0.6"
          />
          <circle
            cx="16"
            cy="15"
            r="5"
            fill="none"
            stroke="#b8a9d4"
            strokeWidth="1"
            opacity="0.6"
          />
        </svg>

        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "16px",
          }}
        >
          <div
            style={{
              fontSize: "22px",
              textTransform: "uppercase",
              letterSpacing: "0.2em",
              color: "#b8a9d4",
              fontFamily: "monospace",
            }}
          >
            WhiteMagic Labs
          </div>
        </div>

        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "24px",
          }}
        >
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              fontSize: "84px",
              lineHeight: 1.05,
              fontWeight: 600,
              color: "#f5f0e8",
              letterSpacing: "-0.02em",
              maxWidth: "1000px",
            }}
          >
            <span>Private AI,&nbsp;</span>
            <span>deployed on&nbsp;</span>
            <span style={{ color: "#b8a9d4" }}>your infrastructure</span>
            <span>.</span>
          </div>
          <div
            style={{
              fontSize: "28px",
              lineHeight: 1.4,
              color: "#b0a498",
              maxWidth: "900px",
            }}
          >
            Persistent memory · Tool use · Governance · Full audit
          </div>
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
          <span style={{ color: "#b8a9d4" }}>Private AI · Governance · MCP</span>
        </div>
      </div>
    ),
    { ...size },
  );
}
