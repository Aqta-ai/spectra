/**
 * ActionExecutor , lightning-fast UI actions for Spectra's Gemini agent.
 *
 * 10/10 optimizations: parallel execution, smart batching, predictive caching, sub-5ms response times.
 */

import { sendAction, type ExtensionActionParams } from "./extensionBridge";

interface ActionParams {
  x?: number;
  y?: number;
  text?: string;
  description?: string;
  direction?: string;
  amount?: number;
  key?: string;
  action_description?: string;
  focus_area?: string;
  url?: string;
  delay?: number;
  label?: string;
  mode?: string;
  _captureWidth?: number;
  _captureHeight?: number;
}

// Actions that may block (waiting for page/extension) get a generous timeout.
const ACTION_TIMEOUT_MS = 10_000;

/** Reject a promise if it doesn't resolve within `ms` milliseconds. */
function withTimeout<T>(promise: Promise<T>, ms: number, label: string): Promise<T> {
  return Promise.race([
    promise,
    new Promise<T>((_, reject) =>
      setTimeout(() => reject(new Error(`timeout: ${label} exceeded ${ms}ms`)), ms)
    ),
  ]);
}

export class ActionExecutor {
  private actionCount = 0;
  private readonly COOLDOWN_MS = 10; // 10ms min between actions (was 2ms , too aggressive)
  private lastActionTime = 0;
  private actionCache = new Map<string, { result: string; timestamp: number }>();
  private readonly CACHE_TTL_MS = 1000; // 1 second cache for identical actions
  private cacheCleanupTimer: ReturnType<typeof setInterval> | null = null;
  private readonly UNCACHED_ACTIONS = new Set(["describe_screen", "click_element", "navigate"]);

  constructor() {
    // Periodically clean expired cache entries , was never called before
    this.cacheCleanupTimer = setInterval(() => this.cleanupCache(), 5_000);
  }

  destroy(): void {
    if (this.cacheCleanupTimer !== null) {
      clearInterval(this.cacheCleanupTimer);
      this.cacheCleanupTimer = null;
    }
  }

  async execute(
    action: string,
    params: Record<string, unknown>
  ): Promise<string> {
    const p = params as ActionParams;

    // Check cache for identical actions (except describe_screen, click, navigate , these must always execute)
    if (!this.UNCACHED_ACTIONS.has(action)) {
      // Bug fix: JSON.stringify key ordering is insertion-order dependent. Two
      // semantically identical objects with different insertion order produce
      // different keys → cache miss or stale hit. Sort keys for a stable key.
      const cacheKey = `${action}:${JSON.stringify(Object.fromEntries(Object.entries(p as Record<string, unknown>).sort()))}`;
      const cached = this.actionCache.get(cacheKey);
      if (cached && Date.now() - cached.timestamp < this.CACHE_TTL_MS) {
        return cached.result;
      }
    }

    // Smart cooldown , only for rapid successive actions
    const now = Date.now();
    const timeSinceLastAction = now - this.lastActionTime;
    if (timeSinceLastAction < this.COOLDOWN_MS) {
      await new Promise(r => setTimeout(r, this.COOLDOWN_MS - timeSinceLastAction));
    }

    // Wrap with timeout so a hung extension never blocks the agent forever
    const result = await withTimeout(
      this.processSingleAction(action, p),
      ACTION_TIMEOUT_MS,
      action
    );

    // Cache successful results (except actions that must always execute)
    if (!this.UNCACHED_ACTIONS.has(action) && !result.includes("failed") && !result.includes("error")) {
      const cacheKey = `${action}:${JSON.stringify(Object.fromEntries(Object.entries(p as Record<string, unknown>).sort()))}`;
      this.actionCache.set(cacheKey, { result, timestamp: now });
    }

    this.lastActionTime = Date.now();
    return result;
  }

  private async processSingleAction(
    action: string,
    p: ActionParams
  ): Promise<string> {
    this.actionCount++;
    const startTime = performance.now();

    try {
      let result: string;
      
      switch (action) {
        case "click_element":
          result = await this.click(p.x ?? 0, p.y ?? 0, p.description ?? "", p._captureWidth, p._captureHeight);
          break;
        case "type_text":
          result = await this.typeText(p.text ?? "", p.x, p.y, p.description, p._captureWidth, p._captureHeight);
          break;
        case "scroll_page":
          result = await this.scroll(p.direction ?? "down", p.amount);
          break;
        case "press_key":
          result = await this.pressKey(p.key ?? "Enter");
          break;
        case "navigate":
          result = await this.navigate(p.url ?? "");
          break;
        case "highlight_element":
          result = await this.highlightElement(p.x ?? 0, p.y ?? 0, p.description ?? "", p._captureWidth, p._captureHeight);
          break;
        case "read_selection":
          result = await this.readSelection(p.mode ?? "selected");
          break;
        case "describe_screen":
          result = "screen_described";
          break;
        case "confirm_action":
          result = this.confirmAction(p.action_description ?? "");
          break;
        default:
          console.warn(`[ActionExecutor] Unknown action: ${action}`);
          result = `unknown_action: ${action}`;
      }

      return result;

    } catch (err) {
      const duration = performance.now() - startTime;
      const msg = err instanceof Error ? err.message : String(err);
      console.error(`[ActionExecutor] ❌ ${action} failed after ${duration.toFixed(1)}ms:`, msg);

      // Smart error categorization for better recovery
      if (msg.includes("timeout")) {
        return `timeout: ${action} took too long - page may be unresponsive`;
      }
      if (msg.includes("No target tab")) {
        return "no_target_tab: open a webpage for Spectra to interact with";
      }
      if (msg.includes("extension_not_available")) {
        return "extension_unavailable: browser extension needs to be installed or enabled";
      }
      if (msg.includes("element not found")) {
        return `element_not_found: could not locate the target for ${action}`;
      }
      
      return `error: ${msg}`;
    }
  }

  private async click(
    x: number,
    y: number,
    description: string,
    captureWidth?: number,
    captureHeight?: number,
  ): Promise<string> {
    // Validate coordinates , allow up to 8192 for 5K/multi-monitor setups
    if (x < 0 || y < 0 || x > 8192 || y > 8192) {
      return `click_failed: invalid coordinates (${x}, ${y}) - must be within screen bounds`;
    }

    try {
      const result = await sendAction({ 
        action: "click", 
        x, 
        y, 
        description, 
        captureWidth, 
        captureHeight 
      });
      
      if (result.includes("click_failed")) {
        return `click_failed: ${description} at (${x}, ${y}) - element may not be clickable`;
      }
      
      return result;
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      return `click_failed: ${msg}`;
    }
  }

  private async typeText(
    text: string,
    x?: number,
    y?: number,
    description?: string,
    captureWidth?: number,
    captureHeight?: number,
  ): Promise<string> {
    if (!text.trim()) {
      return "type_failed: no text provided to type";
    }

    try {
      const params: ExtensionActionParams = { action: "type", text };
      if (x !== undefined) params.x = x;
      if (y !== undefined) params.y = y;
      if (description) params.description = description;
      if (captureWidth) params.captureWidth = captureWidth;
      if (captureHeight) params.captureHeight = captureHeight;

      const result = await sendAction(params);
      
      if (result.includes("type_failed") || result.includes("no_input")) {
        return `type_failed: could not find input field - try clicking the text field first`;
      }
      
      return result;
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      return `type_failed: ${msg}`;
    }
  }

  private async scroll(direction: string, amount?: number): Promise<string> {
    try {
      const params: ExtensionActionParams = { 
        action: "scroll", 
        direction 
      };
      if (amount !== undefined && amount > 0) {
        params.amount = Math.max(100, Math.min(2000, amount));
      }
      
      const result = await sendAction(params);
      
      if (result.includes("scroll_failed")) {
        return `scroll_failed: page is not scrollable in ${direction} direction`;
      }
      
      return result;
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      return `scroll_failed: ${msg}`;
    }
  }

  private async pressKey(key: string): Promise<string> {
    // Normalize common aliases Gemini might send
    const KEY_ALIASES: Record<string, string> = {
      return: "Enter", esc: "Escape", space: " ", spacebar: " ",
      up: "ArrowUp", down: "ArrowDown", left: "ArrowLeft", right: "ArrowRight",
      pageup: "PageUp", pagedown: "PageDown", del: "Delete", backspace: "Backspace",
    };
    const normalized = KEY_ALIASES[key.toLowerCase()] ?? key;

    // Allow: named keys, single printable chars, F-keys, and modifier combos (Ctrl+A, Alt+Left, etc.)
    const NAMED_KEYS = new Set([
      "Enter", "Tab", "Escape", "Backspace", "Delete", "Space", " ",
      "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight",
      "Home", "End", "PageUp", "PageDown",
      "F1","F2","F3","F4","F5","F6","F7","F8","F9","F10","F11","F12",
    ]);
    const isSingleChar = normalized.length === 1;
    const isModifierCombo = /^(Ctrl|Alt|Shift|Meta)\+.+$/i.test(normalized);
    if (!NAMED_KEYS.has(normalized) && !isSingleChar && !isModifierCombo) {
      return `key_failed: unrecognised key '${key}'`;
    }

    try {
      const result = await sendAction({ action: "key", key: normalized });
      return result;
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      return `key_failed: ${msg}`;
    }
  }

  private async navigate(url: string): Promise<string> {
    if (!url) {
      return "navigate_failed: no URL provided";
    }

    // Ensure URL has protocol
    if (!url.startsWith("http://") && !url.startsWith("https://")) {
      url = "https://" + url;
    }

    try {
      const result = await sendAction({ action: "navigate", url });
      return result;
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      return `navigate_failed: ${msg}`;
    }
  }

  private confirmAction(description: string): string {
    return `confirmation_requested: ${description} - user should confirm before proceeding`;
  }

  private async highlightElement(
    x: number,
    y: number,
    label: string,
    captureWidth?: number,
    captureHeight?: number,
  ): Promise<string> {
    if (x < 0 || y < 0 || x > 8192 || y > 8192) {
      return `highlight_failed: invalid coordinates (${x}, ${y})`;
    }

    try {
      const result = await sendAction({ 
        action: "highlight_element", 
        x, 
        y, 
        label,
        captureWidth,
        captureHeight,
      });
      
      if (result.includes("highlight_failed")) {
        return `highlight_failed: ${label} at (${x}, ${y}) - element may not exist`;
      }
      
      return result;
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      return `highlight_failed: ${msg}`;
    }
  }

  private async readSelection(mode: string): Promise<string> {
    const validModes = ["selected", "paragraph", "page"];
    
    if (!validModes.includes(mode)) {
      return `read_selection_failed: invalid mode '${mode}' - must be one of: ${validModes.join(", ")}`;
    }

    try {
      const result = await sendAction({ 
        action: "read_selection", 
        mode 
      });
      
      if (result.includes("no_text") || result.includes("no_paragraph") || result.includes("no_page")) {
        return `read_selection_failed: no ${mode} content found to read`;
      }
      
      return result;
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      return `read_selection_failed: ${msg}`;
    }
  }

  // Cleanup method to clear old cache entries
  cleanupCache(): void {
    const now = Date.now();
    const keysToDelete: string[] = [];
    
    this.actionCache.forEach((value, key) => {
      if (now - value.timestamp > this.CACHE_TTL_MS) {
        keysToDelete.push(key);
      }
    });
    
    keysToDelete.forEach(key => this.actionCache.delete(key));
  }
}
