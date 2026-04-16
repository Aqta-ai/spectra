# Chrome Web Store Submission Checklist

## Pre-Submission Checklist

### ✅ Extension Files Ready
- [x] manifest.json (version 2.0.1)
- [x] background.js
- [x] content.js  
- [x] Icons (16, 32, 48, 64, 128px)
- [ ] Zip extension folder (exclude any dev files)

### ✅ Assets Created
- [ ] Marquee 1400x560px
- [ ] Small tile 440x280px
- [ ] 5 screenshots (1280x800px each)
- See `CHROME_WEB_STORE_ASSETS.md` for specs

### ✅ Documentation Ready
- [x] Privacy policy published at https://spectra.aqta.ai/privacy
- [x] Support page at https://spectra.aqta.ai/guide
- [x] Homepage at https://spectra.aqta.ai

### ✅ Testing Complete
- [ ] Test extension in clean Chrome profile
- [ ] Verify all actions work (click, type, scroll, navigate)
- [ ] Test on multiple websites
- [ ] Verify purple highlight appears
- [ ] Test with spectra.aqta.ai connection

## Submission Steps

### 1. Create Extension Package
```bash
cd extension
# Remove any unnecessary files
rm -f *.md .DS_Store
# Create zip
zip -r spectra-bridge-v2.0.1.zip . -x "*.md" -x ".DS_Store" -x "__MACOSX/*"
```

### 2. Developer Dashboard Setup
- Visit: https://chrome.google.com/webstore/devconsole
- One-time $5 developer registration fee
- Verify developer account

### 3. Upload Extension
- Click "New Item"
- Upload `spectra-bridge-v2.0.1.zip`
- Wait for upload to complete

### 4. Fill in Store Listing

#### Product Details
**Extension Name:** Spectra Bridge  
**Summary (132 char max):**
```
AI accessibility agent: control any website by voice. Click, type, navigate hands-free. For everyone.
```

**Description:**
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

**Category:** Accessibility  
**Language:** English (UK)

#### Assets
- Upload all images from `store-assets/` folder
- Ensure exact dimensions match requirements

#### Links
- **Website:** https://spectra.aqta.ai
- **Support URL:** https://spectra.aqta.ai/guide  
- **Privacy Policy:** https://spectra.aqta.ai/privacy

### 5. Permission Justifications

**Important:** Chrome Web Store requires detailed justifications for sensitive permissions.

**`<all_urls>` (Host permissions):**
```
Spectra Bridge is an accessibility tool that enables voice control of any website. This permission is required to:
1. Execute DOM actions (click, type, scroll) on any site the user visits
2. Inject content scripts to find and interact with page elements
3. Provide visual feedback (purple highlights) when actions are executed

The extension only acts on explicit commands from the Spectra web app (spectra.aqta.ai) and never collects or transmits user data. All code is open source for transparency.
```

**`activeTab`:**
```
Required to identify which browser tab to send actions to when the user issues voice commands.
```

**`scripting`:**
```
Required to inject content.js into web pages to execute accessibility actions (clicking buttons, filling forms, scrolling) on behalf of users who control the browser by voice.
```

### 6. Privacy Practices Declaration

**Data Collection:** None  
**Data Usage:** N/A (no data collected)  
**Data Sharing:** N/A (no data collected)

**Certification:**
- [ ] Check "This extension does not collect any user data"
- [ ] Link to privacy policy: https://spectra.aqta.ai/privacy

### 7. Distribution
- **Visibility:** Public
- **Regions:** All regions
- **Pricing:** Free

### 8. Review & Submit
- [ ] Preview listing
- [ ] Double-check all text for typos
- [ ] Verify all links work
- [ ] Click "Submit for Review"

## Post-Submission

### During Review (1-3 days)
- Monitor Chrome Web Store developer dashboard
- Check email for review updates
- Be ready to respond to questions

### If Approved ✅
1. Update README.md:
   ```markdown
   Install [Spectra from the Chrome Web Store](https://chromewebstore.google.com/detail/spectra/YOUR_ID_HERE)
   ```
2. Update spectra.aqta.ai onboarding
3. Update extension banner link
4. Announce on social media
5. Monitor reviews and respond

### If Rejected ⚠️
Common reasons and fixes:
- **Missing permission justification:** Add detailed explanation (see above)
- **Privacy policy not accessible:** Verify https://spectra.aqta.ai/privacy loads
- **Unclear functionality:** Add more screenshots showing use cases
- **Security concerns:** Emphasize open-source nature and no data collection

## Expected Timeline
- **Upload & fill details:** 30-60 minutes
- **Review wait:** 1-3 business days
- **Approval → live:** Immediate
- **First install:** Within 1 hour of approval

## Support Resources
- Chrome Web Store Developer Policy: https://developer.chrome.com/docs/webstore/program-policies
- Extension publishing guide: https://developer.chrome.com/docs/webstore/publish
- Developer dashboard help: https://support.google.com/chrome_webstore

## Notes
- Keep extension version in sync with manifest.json (currently 2.0.1)
- Update changelogs for each version
- Respond to user reviews within 24-48 hours
- Plan updates every 2-3 months for maintenance
