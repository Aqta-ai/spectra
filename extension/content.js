/**
 * Spectra Bridge Content Script
 * Handles UI actions (click, type, scroll, navigate) on behalf of Spectra AI
 */

const SPECTRA_ORIGINS = [
  'http://localhost:3000', 'http://localhost:3001',
  'http://127.0.0.1:3000', 'http://127.0.0.1:3001',
  'https://spectra.aqta.ai', 'https://comet.aqta.ai',
  'https://spectra-frontend-200635269891.europe-west1.run.app',
];

function isSpectraPage() {
  return SPECTRA_ORIGINS.some(o => window.location.href.startsWith(o));
}

if (isSpectraPage()) {
  window.postMessage({ source: 'spectra-extension', type: 'ready' }, '*');
  
  window.addEventListener('message', (event) => {
    if (!SPECTRA_ORIGINS.includes(event.origin)) return;

    if (event.data?.source === 'spectra' && event.data?.action === 'ping') {
      window.postMessage({
        source: 'spectra-extension',
        type: 'ready',
        messageId: event.data.messageId
      }, '*');
    }

    if (event.data?.source === 'spectra' && event.data?.action && event.data.action !== 'ping') {
      chrome.runtime.sendMessage({
        source: 'spectra-content',
        type: 'execute_action',
        action: event.data.action,
        params: event.data,
        messageId: event.data.messageId
      }, (response) => {
        if (chrome.runtime.lastError) {
          console.warn('[Spectra] Background not reachable:', chrome.runtime.lastError.message);
          try {
            window.postMessage({
              success: false,
              error: 'extension_reloaded: Please refresh the page and try again',
              source: 'spectra-extension',
              messageId: event.data.messageId,
            }, '*');
          } catch (_) {}
          return;
        }
        
        try {
          window.postMessage({
            source: 'spectra-extension',
            messageId: event.data.messageId,
            success: response?.success !== false,
            result: response?.result || response?.error || 'done'
          }, '*');
        } catch (err) {
          console.error('[Spectra] Failed to post response:', err);
        }
      });
    }
  });
  
} else {
  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    (async () => {
      try {
        if (message.type === 'spectra_ping') {
          sendResponse({ pong: true });
          return;
        }
        
        const payload = message.type === 'spectra_execute' && message.params
          ? { action: message.action, ...message.params }
          : message;
        
        const result = await handleAction(payload);
        sendResponse({ success: true, result });
        
      } catch (error) {
        const msg = error instanceof Error ? error.message : String(error);
        console.error('[Spectra Bridge] Action error:', message?.action || 'unknown', msg);
        try {
          sendResponse({ success: false, error: msg });
        } catch (_) {}
      }
    })();
    
    return true;
  });
}

// ────────────────────────────────────────────
// Coordinate scaling: model sees capture resolution, browser uses viewport
// ────────────────────────────────────────────

function scaleCoordinates(x, y, captureWidth, captureHeight) {
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  if (!captureWidth || !captureHeight || captureWidth <= 0 || captureHeight <= 0) {
    return { x: Math.max(0, Math.min(vw - 1, x)), y: Math.max(0, Math.min(vh - 1, y)) };
  }
  // Use Math.floor instead of Math.round for better precision on high-DPI displays
  // elementFromPoint accepts floating-point coordinates, so we can keep decimal precision
  const scaledX = x * (vw / captureWidth);
  const scaledY = y * (vh / captureHeight);
  return {
    x: Math.max(0, Math.min(vw - 1, Math.floor(scaledX))),
    y: Math.max(0, Math.min(vh - 1, Math.floor(scaledY))),
  };
}

// ────────────────────────────────────────────
// Action router
// ────────────────────────────────────────────

async function handleAction(message) {
  // Support both camelCase (from backend) and lowercase param names
  const x = message.x;
  const y = message.y;
  const text = message.text;
  const description = message.description || message.label;
  const direction = message.direction;
  const amount = message.amount;
  const key = message.key;
  const url = message.url;
  const captureWidth = message.captureWidth;
  const captureHeight = message.captureHeight;
  const mode = message.mode;

  switch (message.action) {
    case 'click':
      return await executeClick(x, y, description, captureWidth, captureHeight);
    case 'type':
      return await executeType(text, x, y, description, captureWidth, captureHeight);
    case 'scroll':
      return await executeScroll(direction, amount);
    case 'key':
      return await executeKey(key);
    case 'navigate':
      return await executeNavigate(url);
    case 'highlight_element':
      return await executeHighlight(x, y, description, captureWidth, captureHeight);
    case 'read_selection':
      return await executeReadSelection(mode);
    default:
      throw new Error(`Unknown action: ${message.action}`);
  }
}

// ────────────────────────────────────────────
// Element finders
// ────────────────────────────────────────────

// Role words Gemini appends to descriptions — strip before matching
const ROLE_WORDS = /\b(button|link|icon|image|field|input|element|tab|menu item|checkbox|radio|toggle|dropdown|select|option|label|for the|in the|at the|on the|of the)\b/g;

// Normalise apostrophes and quotes so "What's" matches "What's" (unicode)
function normalizeApostrophes(s) {
  return s.replace(/[\u2018\u2019\u201A\u201B\u2032]/g, "'").replace(/[\u201C\u201D\u201E\u2033]/g, '"');
}

function normalizeDesc(s) {
  return normalizeApostrophes(s.replace(ROLE_WORDS, '').replace(/\s+/g, ' ').trim());
}

function findElementByDescription(description) {
  if (!description || typeof description !== 'string') return null;
  const raw = description.trim();
  if (!raw) return null;
  const want = normalizeApostrophes(raw).toLowerCase();
  const wantNorm = normalizeDesc(want);

  // Include more interactive elements: articles, divs with click handlers, etc.
  const candidates = document.querySelectorAll(
    'a, button, [role="button"], [role="link"], [role="tab"], [role="menuitem"], [role="article"], article, input[type="submit"], input[type="button"], input:not([type="hidden"]), textarea, select, [role="textbox"], [role="searchbox"], [role="combobox"], [onclick], [tabindex]:not([tabindex="-1"]), summary, label, h1, h2, h3, h4, h5, h6, [class*="card"], [class*="item"], [class*="link"]'
  );

  let bestMatch = null;
  let bestScore = 0;

  for (const el of candidates) {
    // Get text content but limit to direct children to avoid matching parent containers
    const directText = Array.from(el.childNodes)
      .filter(n => n.nodeType === Node.TEXT_NODE)
      .map(n => n.textContent.trim())
      .join(' ')
      .toLowerCase();
    
    const texts = [
      (el.textContent || '').trim().toLowerCase(),
      directText,
      (el.getAttribute('aria-label') || '').trim().toLowerCase(),
      (el.getAttribute('title') || '').trim().toLowerCase(),
      (el.getAttribute('placeholder') || '').trim().toLowerCase(),
      (el.value || '').trim().toLowerCase(),
      (el.getAttribute('alt') || '').trim().toLowerCase(),
      (el.getAttribute('href') || '').trim().toLowerCase(),
    ];

    for (const raw of texts) {
      if (!raw) continue;
      const t = normalizeApostrophes(raw);
      const tNorm = normalizeDesc(t);

      // Exact match on either raw or normalised
      if (t === want || tNorm === wantNorm) return el;

      // Score against both raw and normalised descriptions, take the higher
      let score = 0;
      for (const [tv, wv] of [[t, want], [tNorm, wantNorm]]) {
        let s = 0;
        // Substring match
        if (tv.includes(wv)) s = wv.length / tv.length;
        else if (wv.includes(tv) && tv.length > 2) s = tv.length / wv.length * 0.9;
        // Word-based matching for better partial matches
        else {
          const tvWords = tv.split(/\s+/);
          const wvWords = wv.split(/\s+/);
          const matchingWords = wvWords.filter(w => tvWords.some(tw => tw.includes(w) || w.includes(tw)));
          if (matchingWords.length > 0) {
            s = matchingWords.length / wvWords.length * 0.7;
          }
        }
        if (s > score) score = s;
      }
      if (score > bestScore) { bestScore = score; bestMatch = el; }
    }
  }

  if (bestScore > 0.1) return bestMatch;

  // Long descriptions (e.g. full headline): try first N words so "Wired headphone sales are exploding" matches
  if (want.length > 45) {
    const firstWords = want.split(/\s+/).slice(0, 6).join(' ');
    if (firstWords.length >= 10) {
      const shortMatch = findElementByDescription(firstWords);
      if (shortMatch) return shortMatch;
    }
  }
  return null;
}

function findInputByDescription(description) {
  if (!description || typeof description !== 'string') return null;
  const want = description.trim().toLowerCase();
  if (!want) return null;
  
  const inputs = document.querySelectorAll('input:not([type="hidden"]):not([type="submit"]):not([type="button"]), textarea, [contenteditable="true"], [role="textbox"], [role="searchbox"], [role="combobox"]');

  for (const el of inputs) {
    const attrs = [
      (el.getAttribute('placeholder') || '').toLowerCase(),
      (el.getAttribute('aria-label') || '').toLowerCase(),
      (el.getAttribute('name') || '').toLowerCase(),
      (el.getAttribute('id') || '').toLowerCase(),
      (el.getAttribute('title') || '').toLowerCase(),
      (el.getAttribute('type') || '').toLowerCase(),
    ];
    const combined = attrs.join(' ');
    if (combined.includes(want) || (attrs[0] && want.includes(attrs[0])) || (attrs[1] && want.includes(attrs[1]))) return el;
  }
  
  // Fallback: check for common search inputs
  if (want.includes('search')) {
    const searchInput = document.querySelector('input[type="search"], input[name="q"], input[name="query"], input[name="search"], input[aria-label*="earch"], [role="searchbox"]');
    if (searchInput) return searchInput;
  }
  
  return null;
}

// ────────────────────────────────────────────
// Click
// ────────────────────────────────────────────

async function executeClick(x, y, description, captureWidth, captureHeight) {
  try {
    let element = null;
    let usedFallback = false;
    const hasCoords = typeof x === 'number' && typeof y === 'number' && !Number.isNaN(x) && !Number.isNaN(y);

    // Strategy 1: Description-first (preferred — coordinates from Gemini are often approximate)
    if (description) {
      element = findElementByDescription(description);
      if (element) {
        usedFallback = false; // description match is primary, not fallback
        const rect = element.getBoundingClientRect();
        showClickFeedback(rect.left + rect.width / 2, rect.top + rect.height / 2, element, description);
      }
    }

    // Strategy 2: Coordinates (when description didn't match, or no description given)
    if (!element && hasCoords) {
      const scaled = scaleCoordinates(x, y, captureWidth, captureHeight);
      const vw = window.innerWidth;
      const vh = window.innerHeight;
      const clampX = (px) => Math.max(0, Math.min(vw - 1, px));
      const clampY = (py) => Math.max(0, Math.min(vh - 1, py));

      // Try exact point first, then spiral outward up to 30px to handle coordinate drift.
      // Clamp all probe points to viewport so elementFromPoint never gets out-of-scope coords.
      const offsets = [0, 10, 20, 30];
      outer: for (const r of offsets) {
        const probes = r === 0
          ? [[0, 0]]
          : [[-r,0],[r,0],[0,-r],[0,r],[-r,-r],[r,-r],[-r,r],[r,r]];
        for (const [dx, dy] of probes) {
          const px = clampX(scaled.x + dx);
          const py = clampY(scaled.y + dy);
          const el = document.elementFromPoint(px, py);
          if (el && el !== document.body && el !== document.documentElement) {
            element = el;
            usedFallback = true;
            showClickFeedback(px, py, element, description);
            break outer;
          }
        }
      }
    }

    if (!element) {
      const error = description
        ? `no_element_found_for_${description}`
        : hasCoords ? `no_element_at_${x}_${y}` : 'no_element_found';
      console.warn(`[Spectra] Click failed: ${error}`);
      return error;
    }

    const rect = element.getBoundingClientRect();
    const cx = rect.left + rect.width / 2;
    const cy = rect.top + rect.height / 2;
    
    element.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true, cancelable: true, clientX: cx, clientY: cy }));
    await sleep(5);
    element.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true, clientX: cx, clientY: cy }));
    await sleep(5);
    element.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true, clientX: cx, clientY: cy }));
    await sleep(5);
    element.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, clientX: cx, clientY: cy }));
    element.dispatchEvent(new PointerEvent('pointerup', { bubbles: true, cancelable: true, clientX: cx, clientY: cy }));

    // If the element is focusable (input, textarea, etc.), focus it
    if (isInput(element)) element.focus();

    const tag = element.tagName.toLowerCase();
    const label = description || element.textContent?.trim().slice(0, 40) || tag;

    // For anchor tags, synthetic click events do NOT follow href (browser security model).
    // element.click() is the only way to trigger real navigation on <a> links.
    // Return a distinct result so Gemini knows to wait for page load, then read the new page.
    if (tag === 'a' || element.getAttribute('role') === 'link') {
      const dest = element.href || element.getAttribute('href') || label;
      element.click();
      return `clicked_link_navigate_expected:${dest}`;
    }

    return usedFallback
      ? `clicked_by_label_${tag}_${label}`
      : `clicked_${tag}_${label}`;
  } catch (err) {
    console.error(`[Spectra] Click error:`, err);
    return `click_failed: ${err.message}`;
  }
}

// ────────────────────────────────────────────
// Type
// ────────────────────────────────────────────

async function executeType(text, x, y, description, captureWidth, captureHeight) {
  let element = null;
  
  // Strategy 1: Use coordinates (0,0 is valid)
  if (typeof x === 'number' && typeof y === 'number' && !Number.isNaN(x) && !Number.isNaN(y)) {
    const scaled = scaleCoordinates(x, y, captureWidth, captureHeight);
    element = document.elementFromPoint(scaled.x, scaled.y);
    if (element && isInput(element)) {
      element.focus();
      element.click();
    } else {
      element = null;
    }
  }
  
  // Strategy 2: Find by description
  if (!element && description) {
    element = findInputByDescription(description);
    if (element) {
      element.focus();
      element.click();
    }
  }
  
  // Strategy 3: Currently focused element
  if (!element || !isInput(element)) {
    const active = document.activeElement;
    if (active && isInput(active)) element = active;
  }
  
  // Strategy 4: First visible input on page
  if (!element || !isInput(element)) {
    const allInputs = document.querySelectorAll('input:not([type="hidden"]):not([type="submit"]):not([type="button"]), textarea, [contenteditable="true"], [role="textbox"], [role="searchbox"]');
    for (const inp of allInputs) {
      const rect = inp.getBoundingClientRect();
      if (rect.width > 0 && rect.height > 0 && rect.top >= 0 && rect.top < window.innerHeight) {
        element = inp;
        break;
      }
    }
  }
  
  if (!element || !isInput(element)) return 'no_input_found';

  element.focus();
  await sleep(15);
  
  // Clear existing content
  if (element.isContentEditable) {
    element.focus();
    // execCommand('selectAll' + 'insertText') triggers React/Vue onChange bindings
    // and preserves cursor state. Setting textContent directly destroys the DOM
    // structure of rich-text editors (TipTap, Quill, Slate) and invalidates
    // any existing selection range.
    document.execCommand('selectAll', false, undefined);
    const inserted = document.execCommand('insertText', false, text);
    if (!inserted) {
      // execCommand unavailable (sandboxed iframe, Firefox strict mode) — fall back
      element.textContent = text;
      element.dispatchEvent(new InputEvent('input', { data: text, inputType: 'insertText', bubbles: true }));
    }
  } else {
    // Use native input setter to bypass React/Vue controlled components
    const proto = element instanceof HTMLTextAreaElement
      ? window.HTMLTextAreaElement.prototype
      : window.HTMLInputElement.prototype;
    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(proto, 'value')?.set;

    if (nativeInputValueSetter) {
      nativeInputValueSetter.call(element, text);
    } else {
      element.value = text;
    }

    element.dispatchEvent(new InputEvent('input', { data: text, inputType: 'insertText', bubbles: true }));
    element.dispatchEvent(new Event('change', { bubbles: true }));
  }
  
  const tag = element.tagName.toLowerCase();
  const elDesc = element.getAttribute('placeholder') || element.getAttribute('aria-label') || tag;
  return `typed_into_${elDesc}`;
}

// ────────────────────────────────────────────
// Scroll
// ────────────────────────────────────────────

async function executeScroll(direction, amount = null) {
  const dir = (direction || 'down').toString().toLowerCase();
  const viewportH = window.innerHeight || 800;
  const scrollAmount = (amount !== null && amount !== undefined) ? amount : Math.floor(viewportH * 0.75);
  const delta = dir === 'up' ? -scrollAmount : scrollAmount;

  const docEl = document.documentElement;
  const body = document.body;

  const beforeY = window.scrollY;

  // SPA/overflow containers (Google News, SPAs with custom scroll divs) take priority.
  // If a scrollable container exists, scroll it; otherwise scroll the window.
  // Scrolling both causes double-movement on SPAs.
  const container = findScrollableContainer();
  const beforeContainerY = container ? container.scrollTop : 0;
  if (container) {
    container.scrollBy({ top: delta, behavior: 'instant' });
  } else {
    // Use 'instant' so scroll completes synchronously — smooth animation takes
    // 300-500ms and the 50ms sleep below would report zero movement.
    window.scrollBy({ top: delta, left: 0, behavior: 'instant' });
  }

  await sleep(50);

  const afterY = window.scrollY;
  const afterContainerY = container ? container.scrollTop : 0;
  const moved = Math.abs(afterY - beforeY) + Math.abs(afterContainerY - beforeContainerY);

  // Keyboard fallback only if truly nothing moved anywhere
  if (moved < 5) {
    const key = dir === 'up' ? 'PageUp' : 'PageDown';
    const activeEl = document.activeElement || document.body;
    activeEl.dispatchEvent(new KeyboardEvent('keydown', { key, bubbles: true, cancelable: true }));
    activeEl.dispatchEvent(new KeyboardEvent('keyup', { key, bubbles: true, cancelable: true }));
    await sleep(100);
  }

  const scrollHeight = Math.max(docEl.scrollHeight, body.scrollHeight);
  const progress = scrollHeight > viewportH
    ? Math.round((window.scrollY / (scrollHeight - viewportH)) * 100)
    : 100;

  if (dir === 'down' && progress >= 98) return 'scrolled_down_reached_bottom';
  if (dir === 'up' && window.scrollY < 10) return 'scrolled_up_reached_top';

  return `scrolled_${dir}_${scrollAmount}px_at_${progress}pct`;
}

// ────────────────────────────────────────────
// Key press
// ────────────────────────────────────────────

async function executeKey(key) {
  const element = document.activeElement || document.body;

  // Parse modifier combos: "Ctrl+A", "Alt+Left", "Shift+Enter", "Ctrl+Shift+Z"
  const parts = key.split('+');
  const modifiers = parts.slice(0, -1).map(m => m.trim().toLowerCase());
  const baseKey = parts[parts.length - 1].trim();

  const opts = {
    key: baseKey,
    bubbles: true,
    cancelable: true,
    ctrlKey: modifiers.includes('ctrl'),
    altKey: modifiers.includes('alt'),
    shiftKey: modifiers.includes('shift'),
    metaKey: modifiers.includes('meta') || modifiers.includes('cmd'),
  };

  if (baseKey === 'Enter') { opts.keyCode = 13; opts.which = 13; }

  element.dispatchEvent(new KeyboardEvent('keydown', opts));
  element.dispatchEvent(new KeyboardEvent('keypress', opts));
  element.dispatchEvent(new KeyboardEvent('keyup', opts));

  if (baseKey === 'Enter') {
    const form = element.closest?.('form');
    if (form) {
      try { form.requestSubmit(); } catch (_) {
        try { form.submit(); } catch (__) {}
      }
    } else if (element.tagName === 'INPUT' || element.getAttribute('role') === 'searchbox' || element.getAttribute('role') === 'combobox') {
      // No form wrapper (Google News, Angular SPAs) — dispatch a real Enter keydown/up
      // on the element itself so the framework's keydown listener triggers navigation.
      element.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', keyCode: 13, which: 13, bubbles: true, cancelable: true }));
      element.dispatchEvent(new KeyboardEvent('keyup', { key: 'Enter', keyCode: 13, which: 13, bubbles: true, cancelable: true }));
    }
  }

  return `pressed_${key}`;
}

// ────────────────────────────────────────────
// Navigate
// ────────────────────────────────────────────

async function executeNavigate(url) {
  if (!url || typeof url !== 'string') return 'navigate_failed: no url';
  if (!url.startsWith('http://') && !url.startsWith('https://')) {
    url = 'https://' + url;
  }
  window.location.href = url;
  return `navigating_to_${url}`;
}

// ────────────────────────────────────────────
// Highlight element (visual feedback)
// ────────────────────────────────────────────

async function executeHighlight(x, y, label, captureWidth, captureHeight) {
  const scaled = scaleCoordinates(x, y, captureWidth, captureHeight);
  const element = document.elementFromPoint(scaled.x, scaled.y);
  
  if (!element || element === document.body || element === document.documentElement) {
    return `no_element_at_${x}_${y}`;
  }
  
  showClickFeedback(scaled.x, scaled.y, element, label);
  return `highlighted_${element.tagName.toLowerCase()}_${label || 'element'}`;
}

// ────────────────────────────────────────────
// Read selection
// ────────────────────────────────────────────

async function executeReadSelection(mode = 'selected') {
  try {
    let text = '';
    
    if (mode === 'selected') {
      const selection = window.getSelection();
      text = selection ? selection.toString().trim() : '';
      if (!text) return 'no_text_selected';
    } else if (mode === 'paragraph') {
      const selection = window.getSelection();
      if (selection && selection.anchorNode) {
        const node = selection.anchorNode.nodeType === Node.TEXT_NODE 
          ? selection.anchorNode.parentElement 
          : selection.anchorNode;
        const paragraph = node?.closest('p, div, article, section, li, blockquote');
        text = paragraph ? paragraph.textContent.trim() : '';
      }
      if (!text) {
        for (const p of document.querySelectorAll('p, article > div')) {
          const rect = p.getBoundingClientRect();
          if (rect.top >= 0 && rect.top < window.innerHeight) {
            text = p.textContent.trim();
            break;
          }
        }
      }
      if (!text) return 'no_paragraph_found';
    } else if (mode === 'page') {
      // For blind users: extract semantic article content, not raw DOM soup.
      // Exclude nav, header, footer, ads — they're noise.
      const NOISE_SELECTORS = 'nav, header, footer, aside, [role="navigation"], [role="banner"], [role="contentinfo"], .ad, .advertisement, .cookie-notice, script, style, noscript';

      const articleEl = document.querySelector('article')
        || document.querySelector('[role="main"]')
        || document.querySelector('main')
        || document.body;

      // Clone to safely remove noise without affecting the live DOM
      const clone = articleEl.cloneNode(true);
      clone.querySelectorAll(NOISE_SELECTORS).forEach(el => el.remove());

      const h1 = (document.querySelector('h1') || clone.querySelector('h1'))?.textContent?.trim() || '';
      const paras = [...clone.querySelectorAll('p')]
        .map(p => p.textContent.trim())
        .filter(t => t.length > 50); // skip short snippets (captions, labels, etc.)

      if (!h1 && !paras.length) {
        text = clone.textContent.trim().slice(0, 2000);
        if (!text) return 'no_page_content';
      } else {
        const lead = paras.slice(0, 4).join(' ');
        const remaining = paras.length > 4 ? ` (${paras.length - 4} more paragraphs — say "read more" to continue)` : '';
        text = `${h1 ? 'HEADLINE: ' + h1 + '. ' : ''}${lead}${remaining}`;
      }
    }
    
    return `reading_${mode}: ${text}`;
  } catch (err) {
    return `read_failed: ${err.message}`;
  }
}

// ────────────────────────────────────────────
// Helpers
// ────────────────────────────────────────────

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

function isInput(element) {
  if (!element) return false;
  const tag = element.tagName;
  return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || element.isContentEditable ||
         element.getAttribute('role') === 'textbox' || element.getAttribute('role') === 'searchbox' ||
         element.getAttribute('role') === 'combobox';
}

function isScrollable(el) {
  if (!el || el === document.body || el === document.documentElement) return false;
  const style = getComputedStyle(el);
  const ov = style.overflowY;
  return (ov === 'auto' || ov === 'scroll') && el.scrollHeight > el.clientHeight + 20;
}

function findScrollableContainer() {
  // Priority 1: walk up from focused element — handles modals, sidebars, overflow divs
  const focused = document.activeElement;
  if (focused && focused !== document.body) {
    let el = focused.parentElement;
    while (el && el !== document.body) {
      if (isScrollable(el)) return el;
      el = el.parentElement;
    }
  }

  // Priority 2: known SPA container selectors
  const selectors = [
    'main', '[role="main"]', '#root', '#app', '#__next', '#content', '.main-content',
    '.content', '.scroll-container', '.scrollable',
  ];
  for (const sel of selectors) {
    try {
      const el = document.querySelector(sel);
      if (el && isScrollable(el)) return el;
    } catch (_) {}
  }

  // Priority 3: brute force — find the tallest scrollable div
  const divs = document.querySelectorAll('div');
  let best = null;
  let bestOverflow = 0;
  for (const div of divs) {
    const overflow = div.scrollHeight - div.clientHeight;
    if (overflow > 100 && overflow > bestOverflow && isScrollable(div)) {
      best = div;
      bestOverflow = overflow;
    }
  }
  return best;
}

// ────────────────────────────────────────────
// Visual feedback
// ────────────────────────────────────────────

function showClickFeedback(x, y, element, label) {
  // Cursor dot
  const cursor = document.createElement('div');
  cursor.style.cssText = `position:fixed;left:${x}px;top:${y}px;width:20px;height:20px;border-radius:50%;background:rgba(108,92,231,0.5);border:2px solid rgb(108,92,231);pointer-events:none;z-index:999999;transform:translate(-50%,-50%);transition:opacity 0.3s;`;
  document.body.appendChild(cursor);
  
  // Element highlight
  if (element) {
    const rect = element.getBoundingClientRect();
    const overlay = document.createElement('div');
    overlay.style.cssText = `position:fixed;left:${rect.left}px;top:${rect.top}px;width:${rect.width}px;height:${rect.height}px;border:2px solid rgb(108,92,231);background:rgba(108,92,231,0.08);pointer-events:none;z-index:999998;border-radius:4px;`;
    
    if (label) {
      const lbl = document.createElement('div');
      lbl.textContent = label;
      lbl.style.cssText = 'position:absolute;top:-24px;left:0;background:rgb(108,92,231);color:white;padding:3px 8px;border-radius:4px;font-size:11px;font-family:system-ui,sans-serif;white-space:nowrap;';
      overlay.appendChild(lbl);
    }
    
    document.body.appendChild(overlay);
    setTimeout(() => overlay.remove(), 1500);
  }
  
  setTimeout(() => cursor.remove(), 800);
}

