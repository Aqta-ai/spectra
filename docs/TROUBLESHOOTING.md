# Spectra Troubleshooting Guide

This guide helps you resolve common issues when using Spectra for accessibility.

## Quick Diagnostics

### Check Your Status

Look at the Spectra interface status indicators:

**Connection Status:**
- 🟢 Green "Listening..." = Everything working
- 🔴 Red "Disconnected" = Connection problem
- 🟡 Yellow "Connecting..." = Starting up

**Screen Sharing Status:**
- "Screen sharing: on" = Spectra can see your screen
- "Screen sharing: off" = Spectra cannot see your screen

## Common Issues

### Issue 1: Spectra Isn't Responding to Voice

**Symptoms:**
- You speak but nothing happens
- No "Listening..." indicator
- Microphone icon shows red or crossed out

**Solutions:**

**Step 1: Check Microphone Permissions**
1. Click the lock icon in browser address bar
2. Find "Microphone" permission
3. Ensure it's set to "Allow"
4. Refresh the page if you changed permissions

**Step 2: Check System Microphone**
- Windows: Settings → Privacy → Microphone → Allow apps
- Mac: System Preferences → Security & Privacy → Microphone
- Ensure browser has microphone access

**Step 3: Test Microphone**
1. Try speaking in another app (voice recorder)
2. Check microphone is not muted
3. Verify correct microphone is selected in system settings

**Step 4: Restart Spectra**
1. Press `Q` to stop Spectra
2. Wait 2 seconds
3. Press `Q` again to start
4. Say "Hello Spectra"

**Still Not Working?**
- Try a different browser (Chrome or Edge recommended)
- Restart your browser completely
- Check for browser updates
- Restart your computer

---

### Issue 2: Spectra Can't See My Screen

**Symptoms:**
- Spectra says "I cannot see your screen"
- Screen descriptions are generic or unhelpful
- "Where am I?" doesn't give specific location

**Solutions:**

**Step 1: Enable Screen Sharing**
1. Press `W` key to toggle screen sharing
2. Look for "Screen sharing: on" status
3. If prompted, grant screen capture permission

**Step 2: Select Correct Screen/Window**
When the screen sharing dialog appears:
1. Choose "Entire Screen" for best results
2. Or select the specific browser window
3. Click "Share" button
4. Check "Screen sharing: on" appears

**Step 3: Verify Permissions**
- Mac: System Preferences → Security & Privacy → Screen Recording
- Ensure browser has screen recording permission
- May need to restart browser after granting permission

**Step 4: Test Vision System**
1. Say "What do you see?"
2. Spectra should describe actual screen content
3. If she says "I have limitations", there's still a problem

**Still Not Working?**
- Try sharing a different window
- Restart browser and try again
- Check for browser extension conflicts
- Disable other screen capture tools temporarily

---

### Issue 3: Vision System Errors

**Symptoms:**
- "Vision analysis failed" messages
- "Invalid API key" errors
- "Rate limit exceeded" warnings
- "Vision analysis timed out"

**Error: Invalid API Key**
```
Vision analysis failed: Invalid API key
```

**Solution:**
This is a backend configuration issue. Contact support or:
1. Check backend/.env file has GOOGLE_API_KEY
2. Verify API key is valid and active
3. Restart backend server

**Error: Rate Limit Exceeded**
```
Vision analysis failed: Rate limit exceeded
```

**Solution:**
1. Wait 30-60 seconds before trying again
2. Avoid rapid repeated vision requests
3. Use cached results when possible
4. If persistent, contact support about API quota

**Error: Vision Analysis Timed Out**
```
Vision analysis timed out
```

**Solution:**
1. Check your internet connection
2. Try again - may be temporary network issue
3. Close other bandwidth-heavy applications
4. If persistent, check with your network administrator

**Error: Network Connection Failed**
```
Vision analysis failed: Network error
```

**Solution:**
1. Check internet connection is active
2. Try loading a website to verify connectivity
3. Check firewall isn't blocking Spectra
4. Try different network if available

---

### Issue 4: Commands Not Recognised

**Symptoms:**
- Spectra doesn't understand your commands
- Wrong actions are executed
- "I don't understand" responses

**Solutions:**

**Improve Recognition:**

**1. Speak Clearly**
- Normal conversational pace (not too fast or slow)
- Clear pronunciation
- Avoid background noise if possible

**2. Be More Specific**
Instead of: "Click the button"
Try: "Click the blue login button at the top"

**3. Use Command Variations**
If "click" doesn't work, try:
- "Press the button"
- "Tap the button"
- "Select the button"

**4. Check What Spectra Sees**
Before commanding:
1. Say "What do you see?"
2. Verify element you want is visible
3. Use Spectra's description in your command

**5. Use Context**
```
You: "What's the first search result?"
Spectra: "The first result is Wikipedia..."
You: "Click it" ← More reliable than describing again
```

**Common Misunderstandings:**

**Problem: Multiple Similar Elements**
```
❌ "Click the button" (which button?)
✅ "Click the submit button"
✅ "Click the first button"
✅ "Click the blue button on the right"
```

**Problem: Element Not Visible**
```
Solution: "Scroll down" first, then try command
```

**Problem: Page Still Loading**
```
Solution: Wait a moment, then try command
```

---

### Issue 5: Audio Conflicts with Screen Reader

**Symptoms:**
- Can't hear screen reader when Spectra speaks
- Can't hear Spectra when screen reader speaks
- Audio cutting out or overlapping

**Solutions:**

**Check Audio Ducking:**
Spectra should automatically reduce volume when screen reader speaks.

**If You Can't Hear Screen Reader:**
1. Check screen reader volume in its settings
2. Verify screen reader is actually running
3. Try stopping Spectra (`Q`), use screen reader, then restart
4. Check system audio mixer - ensure screen reader not muted

**If You Can't Hear Spectra:**
1. Check browser audio permissions
2. Verify system volume is not muted
3. Check Spectra volume in browser tab
4. Try refreshing the page

**If Both Are Conflicting:**
1. Use screen reader for interface navigation
2. Use Spectra for web content reading
3. Pause one while using the other if needed
4. Adjust relative volumes in system mixer

**Best Practice:**
- Start screen reader first
- Then start Spectra
- Use keyboard shortcuts to control both
- Let audio ducking handle volume automatically

---

### Issue 6: Slow Response Times

**Symptoms:**
- Long delays before Spectra responds
- Vision analysis takes >5 seconds
- Commands execute slowly

**Solutions:**

**Check Network Speed:**
1. Test internet speed (speedtest.net)
2. Close bandwidth-heavy applications
3. Move closer to WiFi router if wireless
4. Try wired connection if available

**Optimise Performance:**
1. Close unnecessary browser tabs
2. Restart browser to clear memory
3. Clear browser cache
4. Disable unnecessary browser extensions

**Check System Resources:**
1. Close other applications
2. Check CPU/memory usage
3. Restart computer if running slow
4. Ensure adequate free disk space

**Backend Issues:**
If consistently slow:
1. Check backend server status
2. Verify backend has adequate resources
3. Check backend logs for errors
4. Contact support if persistent

---

### Issue 7: Spectra Gives Wrong Location

**Symptoms:**
- "Where am I?" gives incorrect website
- Location doesn't match what you expect
- Generic responses instead of specific sites

**Solutions:**

**Ensure Screen Sharing is On:**
1. Press `W` to enable screen sharing
2. Verify "Screen sharing: on" status
3. Make sure correct window is shared

**Wait for Page to Load:**
1. Give page a moment to fully load
2. Try "Where am I?" again after loading
3. Refresh page if it seems stuck

**Make Window Visible:**
1. Ensure browser window is in foreground
2. Maximise window if minimised
3. Make sure content is actually visible

**Try Fresh Analysis:**
1. Say "Describe the screen"
2. Then ask "Where am I?"
3. Spectra will do fresh analysis

**Known Limitations:**
- Some single-page apps may be harder to identify
- Custom web apps without clear branding
- Pages with minimal visual indicators

---

### Issue 8: Keyboard Shortcuts Not Working

**Symptoms:**
- `Q` doesn't start/stop Spectra
- `W` doesn't toggle screen sharing
- Keyboard shortcuts do nothing

**Solutions:**

**Check Focus:**
1. Click inside the Spectra interface
2. Ensure browser window has focus
3. Don't have cursor in text input field

**Check Keyboard Shortcut Conflicts:**
1. Disable other browser extensions temporarily
2. Check for OS-level keyboard shortcut conflicts
3. Try alternative: Click buttons with mouse/screen reader

**Browser Issues:**
1. Refresh the page
2. Try in different browser
3. Check browser console for errors (F12)

**Accessibility Mode:**
If using screen reader:
1. Ensure screen reader isn't capturing keystrokes
2. Try screen reader pass-through mode
3. Use Tab to navigate to buttons instead

---

### Issue 9: Connection Keeps Dropping

**Symptoms:**
- Frequent "Disconnected" status
- Session ends unexpectedly
- Have to restart Spectra repeatedly

**Solutions:**

**Network Stability:**
1. Check WiFi signal strength
2. Try wired connection if available
3. Restart router if connection unstable
4. Check for network interruptions

**Browser Issues:**
1. Update browser to latest version
2. Clear browser cache and cookies
3. Disable problematic extensions
4. Try different browser

**Backend Connection:**
1. Check backend server is running
2. Verify backend URL is correct
3. Check firewall isn't blocking WebSocket
4. Contact support if persistent

**Power Saving:**
- Disable computer sleep mode during use
- Prevent browser from suspending tabs
- Check power settings aren't too aggressive

---

### Issue 10: Form Filling Problems

**Symptoms:**
- Can't find form fields
- Text goes in wrong field
- Submit button doesn't work

**Solutions:**

**Identify Fields First:**
1. Say "What fields are on this form?"
2. Spectra will list available fields
3. Use field names in your commands

**Be Specific:**
```
❌ "Type my email"
✅ "Type john@example.com in the email field"
```

**Check Field Focus:**
1. Say "Click the email field"
2. Then "Type [your email]"
3. Ensures text goes in correct field

**Multi-Step Approach:**
```
1. "What fields do I need to fill?"
2. "Click the first field"
3. "Type [value]"
4. "Click the next field"
5. "Type [value]"
6. "Submit the form"
```

**Common Issues:**
- Hidden fields: Spectra can't interact with invisible fields
- Dynamic forms: Wait for form to fully load
- Validation: Fix errors before submitting

---

## Error Messages Explained

### "I cannot see your screen"
**Meaning:** Screen sharing is not enabled or not working
**Fix:** Press `W` to enable screen sharing

### "I have limitations"
**Meaning:** Vision system is not working properly (this shouldn't happen!)
**Fix:** Restart Spectra, check screen sharing, contact support if persistent

### "Vision analysis failed: [error]"
**Meaning:** Technical error in vision system
**Fix:** Check specific error message above for solutions

### "I don't understand that command"
**Meaning:** Command not recognised or ambiguous
**Fix:** Try command variation or be more specific

### "I cannot find that element"
**Meaning:** Element not visible or doesn't exist
**Fix:** Check what Spectra sees, scroll if needed, be more specific

### "Connection lost"
**Meaning:** Network connection to backend interrupted
**Fix:** Check internet, press `Q` to restart

---

## Getting Additional Help

### Self-Help Resources

**Documentation:**
- Accessibility Quick Start Guide
- Voice Commands Reference
- Video Tutorials (coming soon)

**In-App Help:**
- Say "Help" to Spectra
- Press Tab to navigate to Guide link
- Check status messages for hints

### Contact Support

**Before Contacting Support:**
1. Note the specific error message
2. Document steps to reproduce issue
3. Check browser console for errors (F12)
4. Try basic troubleshooting steps above

**Information to Provide:**
- Operating system and version
- Browser and version
- Screen reader (if using one)
- Exact error messages
- Steps to reproduce
- When issue started

**Support Channels:**
- Email: support@spectra.example.com
- GitHub Issues: github.com/spectra/issues
- Community Forum: forum.spectra.example.com

---

## Preventive Maintenance

### Regular Checks

**Weekly:**
- Clear browser cache
- Update browser to latest version
- Check for Spectra extension updates
- Restart browser

**Monthly:**
- Review and update permissions
- Check system audio settings
- Test microphone and speakers
- Verify screen sharing still works

### Best Practices

**For Reliability:**
- Use Chrome or Edge (best compatibility)
- Keep browser updated
- Maintain stable internet connection
- Close unnecessary tabs and apps

**For Performance:**
- Restart browser daily
- Clear cache regularly
- Monitor system resources
- Use wired connection when possible

**For Accessibility:**
- Test with screen reader regularly
- Verify keyboard shortcuts work
- Check audio ducking is functioning
- Keep screen reader updated

---

## Known Issues and Workarounds

### Issue: Complex Layouts
**Problem:** Some complex web layouts are hard for vision system to parse
**Workaround:** Be very specific in commands, use position descriptors

### Issue: Dynamic Content
**Problem:** Rapidly changing content may confuse vision system
**Workaround:** Wait for content to stabilise before commanding

### Issue: Popup Dialogs
**Problem:** Popups may not be immediately recognised
**Workaround:** Say "What do you see?" to force fresh analysis

### Issue: Video Players
**Problem:** Video player controls may be hard to target
**Workaround:** Use keyboard shortcuts (space for play/pause, etc.)

### Issue: Custom Web Apps
**Problem:** Non-standard UI elements may be harder to identify
**Workaround:** Use very specific descriptions, try multiple command variations

---

## Diagnostic Checklist

Use this checklist to systematically diagnose issues:

### Connection Issues
- [ ] Internet connection is active
- [ ] Browser is up to date
- [ ] Spectra extension is installed and enabled
- [ ] No firewall blocking WebSocket connections
- [ ] Backend server is running (if self-hosted)

### Microphone Issues
- [ ] Microphone is connected and working
- [ ] Browser has microphone permission
- [ ] System allows browser microphone access
- [ ] Microphone is not muted
- [ ] Correct microphone is selected

### Vision Issues
- [ ] Screen sharing is enabled (press W)
- [ ] Correct window/screen is shared
- [ ] Browser has screen recording permission
- [ ] Content is actually visible on screen
- [ ] Page has finished loading

### Command Issues
- [ ] Speaking clearly at normal pace
- [ ] Using specific element descriptions
- [ ] Element is visible on screen
- [ ] Page has finished loading
- [ ] Trying command variations

### Audio Issues
- [ ] System volume is not muted
- [ ] Browser tab is not muted
- [ ] Screen reader volume is adequate
- [ ] No audio device conflicts
- [ ] Audio ducking is working

---

**Remember:** Most issues can be resolved by:
1. Checking permissions
2. Restarting Spectra (press Q twice)
3. Refreshing the browser page
4. Being more specific in commands

If problems persist after trying these solutions, contact support with detailed information about your issue.
