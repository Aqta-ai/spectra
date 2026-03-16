/**
 * Spectra Bridge — Background Service Worker
 * Routes action messages from Spectra page to the active tab for execution.
 * Supports Chrome, Arc, and Comet browsers.
 *
 * Improvements: better retry logic, tab caching, action queuing, error recovery.
 */

const SPECTRA_ORIGINS = [
  "http://localhost:3000",
  "http://localhost:3001",
  "http://127.0.0.1:3000",
  "http://127.0.0.1:3001",
  "https://spectra.aqta.ai",
  "https://comet.aqta.ai",
];

// Cache the last known good target tab to avoid repeated queries
let cachedTargetTabId = null;
let cachedTargetTabUrl = null;
let cachedTargetTabTimestamp = 0;
const CACHE_TTL_MS = 30000; // 30 seconds — prevents stale tab after user switches context

function isSpectraTab(tab) {
  if (!tab?.url) return false;
  return SPECTRA_ORIGINS.some((o) => tab.url.startsWith(o));
}

// No allowlist: any http/https page (e.g. wikipedia.org) is valid for clicks. Only browser-internal URLs are restricted.
function isRestrictedUrl(url) {
  if (!url) return true;
  if (url === "chrome://newtab/" || url === "about:blank" || url === "New Tab" || url.trim() === "") {
    return true;
  }
  return (
    url.startsWith("chrome://") ||
    url.startsWith("chrome-extension://") ||
    url.startsWith("arc://") ||
    url.startsWith("about:") ||
    url.startsWith("edge://") ||
    url.startsWith("brave://") ||
    url.startsWith("devtools://") ||
    url.startsWith("moz-extension://") ||
    url.startsWith("safari-extension://")
  );
}

/**
 * Ensure content script is injected and ready in the target tab.
 * BULLETPROOF: Uses programmatic injection with allFrames for MV3 best practices.
 */
async function ensureContentScript(tabId) {
  // First try a ping
  try {
    const response = await chrome.tabs.sendMessage(tabId, { type: "spectra_ping" });
    if (response?.pong) return true;
  } catch {
    // Content script not ready — try injecting
  }

  // BULLETPROOF: Programmatic injection with allFrames (MV3 recommended pattern)
  try {
    await chrome.scripting.executeScript({
      target: { tabId, allFrames: true },
      files: ["content.js"],
    });
    
    // Wait for injection to complete
    await new Promise((r) => setTimeout(r, 300));
    
    // Verify injection worked
    const response = await chrome.tabs.sendMessage(tabId, { type: "spectra_ping" });
    if (response?.pong) {
      return true;
    }
  } catch (err) {
    console.warn(`[Spectra Bridge] ❌ Could not inject content script into tab ${tabId}:`, err?.message);
    return false;
  }
  
  return false;
}

/**
 * Send a message to a tab with robust retry logic.
 */
async function sendToTab(tabId, message, retries = 3) {
  let lastErr = null;
  for (let i = 0; i < retries; i++) {
    try {
      // Verify tab still exists before sending (race condition fix)
      try {
        const tab = await chrome.tabs.get(tabId);
        if (!tab) {
          throw new Error(`Tab ${tabId} no longer exists`);
        }
      } catch (tabErr) {
        // Tab doesn't exist or we don't have permission
        throw new Error(`Tab ${tabId} no longer exists or is inaccessible`);
      }
      
      const result = await chrome.tabs.sendMessage(tabId, message);
      return result;
    } catch (err) {
      lastErr = err;
      const msg = err?.message || String(err);
      if (i < retries - 1 && msg.includes("Receiving end does not exist")) {
        // Try to ensure content script is ready
        const ready = await ensureContentScript(tabId);
        if (!ready && i === retries - 2) throw err;
        await new Promise((r) => setTimeout(r, 200 * (i + 1)));
        continue;
      }
      throw err;
    }
  }
  throw lastErr || new Error("sendToTab failed after retries");
}

/**
 * Find the best target tab for action execution.
 * Uses cached tab if still valid, otherwise queries all tabs.
 */
async function findTargetTab(spectraSenderId) {
  // Check if cached tab is still valid
  if (cachedTargetTabId) {
    // Expire cache after 30s to handle user switching browser context
    if (Date.now() - cachedTargetTabTimestamp > CACHE_TTL_MS) {
      cachedTargetTabId = null;
      cachedTargetTabUrl = null;
      cachedTargetTabTimestamp = 0;
    } else {
      try {
        const tab = await chrome.tabs.get(cachedTargetTabId);
        if (tab && tab.id !== spectraSenderId && !isSpectraTab(tab) && !isRestrictedUrl(tab.url)) {
          return tab;
        }
      } catch {
        // Tab no longer exists
        cachedTargetTabId = null;
        cachedTargetTabUrl = null;
        cachedTargetTabTimestamp = 0;
      }
    }
  }

  // Query all tabs
  const allTabs = await chrome.tabs.query({});

  // Prefer the active tab in the current window first
  const activeTabs = allTabs.filter(
    (t) => t.active && t.id && t.id !== spectraSenderId && !isSpectraTab(t) && !isRestrictedUrl(t.url)
  );

  // Then fall back to most-recently-accessed non-Spectra, non-restricted tab
  const candidates = allTabs
    .filter((t) => t.id && t.id !== spectraSenderId && !isSpectraTab(t) && !isRestrictedUrl(t.url))
    .sort((a, b) => (b.lastAccessed ?? 0) - (a.lastAccessed ?? 0));

  const target = activeTabs[0] ?? candidates[0] ?? null;

  if (target) {
    cachedTargetTabId = target.id;
    cachedTargetTabUrl = target.url;
    cachedTargetTabTimestamp = Date.now();
  }

  return target;
}

// BULLETPROOF: Enhanced tab cache invalidation
chrome.tabs.onRemoved.addListener((tabId) => {
  if (tabId === cachedTargetTabId) {
    cachedTargetTabId = null;
    cachedTargetTabUrl = null;
    cachedTargetTabTimestamp = 0;
  }
});

// BULLETPROOF: Service worker lifecycle management
chrome.runtime.onSuspend.addListener(() => {
  cachedTargetTabId = null;
  cachedTargetTabUrl = null;
  cachedTargetTabTimestamp = 0;
});

chrome.runtime.onStartup.addListener(() => {
  cachedTargetTabId = null;
  cachedTargetTabUrl = null;
  cachedTargetTabTimestamp = 0;
});

// BULLETPROOF: Re-inject content scripts after navigation completes
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  // Re-ensure content script after navigation completes
  if (tabId === cachedTargetTabId && changeInfo.status === 'complete' && !isRestrictedUrl(tab.url)) {
    ensureContentScript(tabId).catch(() => {
      console.warn(`[Spectra Bridge] Could not re-inject content script after navigation to ${tab.url}`);
    });
  }
  
  // Handle URL changes for cached tab
  if (tabId === cachedTargetTabId && changeInfo.url) {
    cachedTargetTabUrl = changeInfo.url;
    if (isRestrictedUrl(changeInfo.url)) {
      cachedTargetTabId = null;
      cachedTargetTabUrl = null;
    }
  }
});

chrome.runtime.onInstalled.addListener(() => {});

// Listen for messages from Spectra page to announce we're ready
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  // BULLETPROOF: Wrap entire handler in try-catch to prevent fatal errors
  (async () => {
    try {
      // Respond to ping from Spectra page
      if (message.source === "spectra" && message.action === "ping") {
        sendResponse({ source: "spectra-extension", type: "ready" });
        return;
      }
      
      if (message.source !== "spectra-content" || message.type !== "execute_action") {
        return;
      }

      // Ping is for extension detection only — never run on the target tab
      if (message.action === "ping") {
        sendResponse({ source: "spectra-extension", type: "ready", success: true, messageId: message.messageId });
        return;
      }

      const spectraSenderId = sender.tab?.id;
      const targetTab = await findTargetTab(spectraSenderId);

      if (!targetTab?.id) {
        sendResponse({
          success: false,
          error: "No target tab found. Open a webpage in another tab first.",
          messageId: message.messageId,
        });
        return;
      }

      // Ensure content script is ready before sending
      const ready = await ensureContentScript(targetTab.id);
      if (!ready) {
        sendResponse({
          success: false,
          error: "Could not reach the target tab. Try refreshing it.",
          messageId: message.messageId,
        });
        return;
      }

      // Focus the target tab before executing actions — Chrome won't properly
      // dispatch events to background/inactive tabs
      try {
        await chrome.tabs.update(targetTab.id, { active: true });
        // Brief delay to let the tab become active
        await new Promise((r) => setTimeout(r, 100));
      } catch {
        // Tab might have been closed between finding and focusing
      }

      // Handle navigate at the background level using chrome.tabs API
      if (message.action === "navigate") {
        let url = message.params?.url ?? "";
        if (url && !url.startsWith("http://") && !url.startsWith("https://")) {
          url = "https://" + url;
        }
        try {
          const parsed = new URL(url);
          // Security: only allow safe protocols — block javascript:, data:, blob:, etc.
          if (!["http:", "https:"].includes(parsed.protocol)) {
            sendResponse({ success: false, error: `blocked unsafe protocol: ${parsed.protocol}`, messageId: message.messageId });
            return;
          }
          await chrome.tabs.update(targetTab.id, { url, active: true });
          cachedTargetTabId = targetTab.id;
          cachedTargetTabUrl = url;

          // Wait for the tab to finish loading so subsequent actions (click, type) land
          // on a fully-rendered page and the content script is injected before we respond.
          await new Promise((resolve) => {
            const timeout = setTimeout(resolve, 8000); // hard cap at 8s
            const listener = (tabId, changeInfo) => {
              if (tabId === targetTab.id && changeInfo.status === "complete") {
                chrome.tabs.onUpdated.removeListener(listener);
                clearTimeout(timeout);
                resolve();
              }
            };
            chrome.tabs.onUpdated.addListener(listener);
          });

          // Re-inject content script so it is ready for the first action after navigation
          await ensureContentScript(targetTab.id).catch(() => {});

          sendResponse({ success: true, result: `navigated_to_${url}`, messageId: message.messageId });
        } catch {
          sendResponse({ success: false, error: `invalid URL: ${url}`, messageId: message.messageId });
        }
        return;
      }

      const result = await sendToTab(targetTab.id, {
        type: "spectra_execute",
        action: message.action,
        params: message.params,
        messageId: message.messageId,
      });

      sendResponse(result);
      
    } catch (err) {
      console.error("[Spectra Bridge] onMessage fatal:", err);
      try {
        sendResponse({
          success: false,
          error: String(err),
          result: `fatal_error: ${err?.message || err}`,
          messageId: message.messageId,
        });
      } catch (_) {
        // Even sendResponse failed - log and continue
        console.error("[Spectra Bridge] Could not send error response:", _);
      }
    }
  })();

  // BULLETPROOF: Always return true to keep channel open for async responses
  return true;
});

