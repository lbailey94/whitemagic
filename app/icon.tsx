import { ImageResponse } from "next/og";

export const runtime = "edge";
export const size = { width: 32, height: 32 };
export const contentType = "image/png";

export default function Icon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#1a1410",
          borderRadius: "6px",
        }}
      >
        <svg
          width="26"
          height="26"
          viewBox="0 0 24 24"
          xmlns="http://www.w3.org/2000/svg"
        >
          <circle
            cx="12"
            cy="9"
            r="5"
            fill="none"
            stroke="#b8a9d4"
            strokeWidth="1.6"
            opacity="1"
          />
          <circle
            cx="8"
            cy="15"
            r="5"
            fill="none"
            stroke="#b8a9d4"
            strokeWidth="1.6"
            opacity="0.8"
          />
          <circle
            cx="16"
            cy="15"
            r="5"
            fill="none"
            stroke="#b8a9d4"
            strokeWidth="1.6"
            opacity="0.8"
          />
        </svg>
      </div>
    ),
    { ...size },
  );
}
