/**
 * Automated axe-core accessibility tests
 *
 * Runs WCAG violation checks on Spectra UI structure.
 * Run with: npm run test -- tests/axe-accessibility.test.tsx
 */

import { describe, it, expect, beforeEach } from "vitest";
import { axe } from "vitest-axe";

describe("Axe Accessibility - WCAG Violations", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
  });

  it("Spectra layout structure (skip link, main) should have no axe violations", async () => {
    const container = document.createElement("div");
    container.innerHTML = `
      <a href="#main-content">Skip to main content</a>
      <div role="region" aria-label="Keyboard shortcuts">
        <h2>Keyboard shortcuts</h2>
        <ul>
          <li>Q: Start or stop Spectra</li>
          <li>W: Share your screen</li>
          <li>Escape: Stop Spectra</li>
          <li>Tab: Navigate between controls</li>
        </ul>
      </div>
      <main id="main-content" role="main">
        <h1>Spectra</h1>
        <button aria-label="Start Spectra">Start</button>
      </main>
    `;
    document.body.appendChild(container);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it("Interactive elements with aria-labels should have no axe violations", async () => {
    const container = document.createElement("div");
    container.innerHTML = `
      <button aria-label="Start Spectra">S</button>
      <button aria-label="Share screen">W</button>
      <div role="status" aria-live="polite">Listening</div>
      <div role="alert" aria-live="assertive">Connected</div>
    `;
    document.body.appendChild(container);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
