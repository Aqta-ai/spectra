# Chrome Web Store Assets Guide

This document outlines all required assets for the Chrome Web Store listing.

## Required Images

### 1. Store Icon (128x128px)
**File:** Already exists at `icons/icon128.png` ✅
- Current purple "S" logo is perfect
- Ensure it's exactly 128x128px

### 2. Marquee Promotional Image (1400x560px)
**File:** `store-assets/marquee-1400x560.png`
**Design:**
- Background: Dark navy gradient (matching app)
- Left side: Large Spectra logo/orb
- Right side: Text overlay
  - "Spectra"
  - "Your screen, your voice, your way"
  - "AI-powered hands-free web navigation"
- Bottom: Small screenshots showing click action with purple highlight

### 3. Small Promotional Tile (440x280px)  
**File:** `store-assets/small-tile-440x280.png`
**Design:**
- Simplified version of marquee
- Spectra logo centered
- Tagline below: "Voice-first accessibility"
- Purple gradient background

### 4. Screenshots (5 required, 1280x800px or 640x400px)

#### Screenshot 1: Extension Icon & Status
**File:** `store-assets/screenshot-1-toolbar.png`
**Caption:** "Spectra Bridge in your Chrome toolbar"
**Content:**
- Chrome toolbar with Spectra icon visible
- Tooltip showing "Spectra Bridge"
- Clean, simple view

#### Screenshot 2: Voice Command in Action
**File:** `store-assets/screenshot-2-voice-command.png`
**Caption:** "Control the web by voice"
**Content:**
- spectra.aqta.ai open
- Voice command visible: "Click the search button"
- Orb showing "listening" state

#### Screenshot 3: Click Action with Highlight
**File:** `store-assets/screenshot-3-purple-highlight.png`
**Caption:** "Visual feedback on every action"
**Content:**
- Any webpage
- Purple highlight circle visible on an element
- Shows the extension's visual feedback

#### Screenshot 4: Screen Sharing Active
**File:** `store-assets/screenshot-4-screen-share.png`
**Caption:** "Spectra sees your screen to help you navigate"
**Content:**
- Browser showing screen share active (green indicator)
- spectra.aqta.ai showing "Connected" status
- Clean, professional view

#### Screenshot 5: Multi-Step Task
**File:** `store-assets/screenshot-5-flight-booking.png`
**Caption:** "Handles complex multi-step tasks"
**Content:**
- Google Flights or similar
- Spectra conversation showing flight search
- Demonstrates AI capability

## Store Listing Copy

### Short Description (132 characters max)
```
AI accessibility agent: control any website by voice. Click, type, navigate hands-free. For everyone.
```

### Full Description
```
Spectra Bridge brings voice-first AI accessibility to every website. 

🎤 VOICE CONTROL
Speak naturally to control any website:
• "Click the sign in button"
• "Fill in this form"
• "Read me this article"
• "Search for flights to Paris"

✨ KEY FEATURES
• Works on ANY website (no special integration needed)
• Visual feedback with purple highlights
• Hands-free browsing
• Screen-aware AI understands layout and context
• Built for accessibility, designed for everyone

🔒 PRIVACY
• No data collection
• Extension only executes commands from spectra.aqta.ai
• Open source for transparency

🚀 POWERED BY GEMINI
Uses Google's Gemini Live API for real-time understanding and natural conversation.

REQUIREMENTS
• Chrome browser
• Visit spectra.aqta.ai to start
• Microphone for voice input (optional)

Built by Aqta Technologies for the 2.2 billion people with vision impairments, RSI, or anyone who wants hands-free web navigation.

Apache 2.0 License | GitHub: Aqta-ai/spectra
```

### Category
**Accessibility**

### Language
**English (UK)**

### Additional Fields
- **Support URL:** https://spectra.aqta.ai/guide
- **Homepage URL:** https://spectra.aqta.ai
- **Privacy Policy URL:** https://spectra.aqta.ai/privacy

## Design Specifications

### Color Palette
- Primary Purple: `#6C5CE7` (Spectra primary)
- Secondary Purple: `#a29bfe`
- Dark Navy: `#1a1a2e` (background)
- White text: `#ffffff`

### Typography
- Headings: System font, bold, 32-48px
- Body: 16-18px, regular
- Captions: 12-14px

### Brand Guidelines
- Always show the purple "S" orb
- Use the tagline "Your screen, your voice, your way"
- Emphasize accessibility + universal design
- Show real screenshots, not mockups

## Creating the Assets

### Tools Recommended
1. **Figma** (free): Best for quick design
2. **Photoshop/GIMP**: For screenshot editing
3. **Chrome DevTools**: Use device toolbar to capture exact dimensions

### Quick Screenshot Guide
```bash
# Set Chrome window to exactly 1280x800
# Use Cmd+Shift+5 (Mac) or Snipping Tool (Windows)
# Crop to exact dimensions
# Save as PNG with high quality
```

### Asset Checklist
- [ ] Marquee 1400x560px
- [ ] Small tile 440x280px
- [ ] Screenshot 1: Toolbar (1280x800px)
- [ ] Screenshot 2: Voice (1280x800px)
- [ ] Screenshot 3: Highlight (1280x800px)
- [ ] Screenshot 4: Screen share (1280x800px)
- [ ] Screenshot 5: Multi-step (1280x800px)
- [ ] Review all text for clarity
- [ ] Check all links work
- [ ] Verify privacy policy is published

## Submission Steps

1. **Developer Dashboard:** https://chrome.google.com/webstore/devconsole
2. **Upload Extension:** Zip the `extension/` folder (exclude node_modules, .git)
3. **Fill in Details:** Copy from sections above
4. **Upload Images:** All assets from this guide
5. **Set Permissions Justification:**
   - `<all_urls>`: "Required to execute accessibility actions (click, type, scroll) on any website the user visits"
   - `activeTab`: "Identifies the active tab to send actions to"
   - `scripting`: "Injects content script to execute DOM actions"
6. **Submit for Review:** Typically 1-3 days
7. **Monitor:** Check dashboard for review status

## Expected Review Time
- **Initial review:** 1-3 business days
- **Resubmission:** 12-48 hours
- **Common rejection reasons:**
  - Missing justification for `<all_urls>`
  - Privacy policy not accessible
  - Screenshots unclear

## Post-Approval
- Update README.md with Web Store link
- Update spectra.aqta.ai onboarding to point to store
- Tweet/announce the launch
- Monitor reviews and respond promptly
