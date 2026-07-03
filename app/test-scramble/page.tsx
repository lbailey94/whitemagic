import { WIP_MODE, WIP_SCRAMBLE } from "@/lib/wip";

export const metadata = {
  title: "Test Scramble — WhiteMagic",
  description: "Diagnostic page for WIP scramble",
};

export default function TestScramblePage() {
  const now = new Date().toISOString();

  return (
    <div
      style={{
        padding: "40px",
        background: "#1a0505",
        color: "#fff",
        fontFamily: "monospace",
        minHeight: "100vh",
      }}
    >
      <h1 style={{ color: "#ff6b6b", fontSize: "32px", marginBottom: "20px" }}>
        WIP SCRAMBLE TEST
      </h1>
      <div style={{ fontSize: "18px", lineHeight: "1.8" }}>
        <p>
          <strong>WIP_MODE:</strong>{" "}
          <span style={{ color: WIP_MODE ? "#4ade80" : "#f87171" }}>
            {String(WIP_MODE)}
          </span>
        </p>
        <p>
          <strong>WIP_SCRAMBLE:</strong>{" "}
          <span style={{ color: WIP_SCRAMBLE ? "#4ade80" : "#f87171" }}>
            {String(WIP_SCRAMBLE)}
          </span>
        </p>
        <p>
          <strong>Build time:</strong> {now}
        </p>
        <p>
          <strong>Status:</strong>{" "}
          {WIP_SCRAMBLE ? (
            <span style={{ color: "#4ade80" }}>
              ✓ WIP scramble should be active
            </span>
          ) : (
            <span style={{ color: "#f87171" }}>
              ✗ WIP scramble is OFF
            </span>
          )}
        </p>
      </div>
      <div
        style={{
          marginTop: "40px",
          padding: "20px",
          background: "#2a1515",
          borderRadius: "8px",
        }}
      >
        <h2 style={{ color: "#fbbf24", marginBottom: "10px" }}>
          If you see this page:
        </h2>
        <ul style={{ lineHeight: "2" }}>
          <li>
            The build is using the correct code (this page exists in the
            latest deploy)
          </li>
          <li>
            WIP_MODE and WIP_SCRAMBLE values are shown above
          </li>
          <li>
            If WIP_SCRAMBLE is true but you don't see scrambled text on the
            home page, the issue is with the WipScrambleAll component
          </li>
          <li>
            If WIP_SCRAMBLE is false, the build env is wrong
          </li>
        </ul>
      </div>
    </div>
  );
}
