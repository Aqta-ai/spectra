import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt = "Spectra , Your screen, your voice, your way";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OGImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "1200px",
          height: "630px",
          background: "#0d0d0f",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: "72px 80px",
          fontFamily: "system-ui, -apple-system, sans-serif",
          position: "relative",
          overflow: "hidden",
        }}
      >
        {/* Background glow top-right */}
        <div
          style={{
            position: "absolute",
            top: "-120px",
            right: "-80px",
            width: "600px",
            height: "600px",
            borderRadius: "50%",
            background:
              "radial-gradient(circle, rgba(108,92,231,0.25) 0%, rgba(108,92,231,0) 70%)",
            display: "flex",
          }}
        />
        {/* Background glow bottom-left */}
        <div
          style={{
            position: "absolute",
            bottom: "-100px",
            left: "60px",
            width: "400px",
            height: "400px",
            borderRadius: "50%",
            background:
              "radial-gradient(circle, rgba(108,92,231,0.12) 0%, rgba(108,92,231,0) 70%)",
            display: "flex",
          }}
        />

        {/* Top: logo + badge */}
        <div style={{ display: "flex", alignItems: "center", gap: "20px" }}>
          <div
            style={{
              width: "52px",
              height: "52px",
              borderRadius: "14px",
              background: "#6C5CE7",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "26px",
              color: "#ffffff",
              fontWeight: 700,
            }}
          >
            S
          </div>
          <span
            style={{
              color: "#ffffff",
              fontSize: "28px",
              fontWeight: 700,
              letterSpacing: "-0.5px",
            }}
          >
            Spectra
          </span>
          <div
            style={{
              marginLeft: "8px",
              background: "rgba(108,92,231,0.2)",
              border: "1px solid rgba(108,92,231,0.5)",
              borderRadius: "20px",
              padding: "4px 16px",
              color: "#a89cf7",
              fontSize: "15px",
              fontWeight: 500,
              display: "flex",
            }}
          >
            AI Accessibility Agent
          </div>
        </div>

        {/* Main headline */}
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          <div
            style={{
              color: "#ffffff",
              fontSize: "72px",
              fontWeight: 800,
              lineHeight: 1.05,
              letterSpacing: "-2px",
              display: "flex",
              flexDirection: "column",
            }}
          >
            <span>Your screen,</span>
            <span>
              <span style={{ color: "#6C5CE7" }}>your voice</span>
              <span>, your way.</span>
            </span>
          </div>
          <div
            style={{
              color: "#8a8a9a",
              fontSize: "24px",
              fontWeight: 400,
              lineHeight: 1.5,
              maxWidth: "700px",
              display: "flex",
            }}
          >
            Real-time AI that sees your screen, speaks what matters, and acts on your voice , on any website.
          </div>
        </div>

        {/* Bottom: pills + URL */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-end",
          }}
        >
          <div style={{ display: "flex", gap: "12px" }}>
            {["Voice Control", "Screen Vision", "Browser Actions", "30+ Languages"].map((tag) => (
              <div
                key={tag}
                style={{
                  background: "rgba(255,255,255,0.06)",
                  border: "1px solid rgba(255,255,255,0.1)",
                  borderRadius: "8px",
                  padding: "8px 16px",
                  color: "#c0c0d0",
                  fontSize: "15px",
                  fontWeight: 500,
                  display: "flex",
                }}
              >
                {tag}
              </div>
            ))}
          </div>
          <div
            style={{
              color: "#4a4a5a",
              fontSize: "18px",
              fontWeight: 500,
              display: "flex",
            }}
          >
            spectra.aqta.ai
          </div>
        </div>
      </div>
    ),
    { ...size }
  );
}
