# Spectra Voice Commands Reference

Complete guide to voice commands and natural language interactions with Spectra.

## Table of Contents
- [Command Principles](#command-principles)
- [Navigation Commands](#navigation-commands)
- [Information Commands](#information-commands)
- [Action Commands](#action-commands)
- [Context Commands](#context-commands)
- [System Commands](#system-commands)
- [Advanced Patterns](#advanced-patterns)

## Command Principles

### Natural Language Processing
Spectra understands natural language, not rigid commands. You can:
- Use variations and synonyms
- Speak conversationally
- Combine multiple actions
- Reference previous context

### Command Variations
Most commands have multiple valid forms. Use whatever feels natural:

**Example: Clicking**
- "Click the search button"
- "Press the search button"
- "Tap the search button"
- "Select the search button"

All four commands do exactly the same thing.

## Navigation Commands

### Opening Websites

**Pattern**: `[action] [website name]`

**Variations**:
- "Go to [website]"
- "Open [website]"
- "Visit [website]"
- "Navigate to [website]"
- "Take me to [website]"

**Examples**:
```
✅ "Go to Google"
✅ "Open Gmail"
✅ "Visit YouTube"
✅ "Navigate to BBC News"
✅ "Take me to Amazon"
```

**With URLs**:
```
✅ "Go to google.com"
✅ "Open www.github.com"
✅ "Visit bbc.co.uk/news"
```

### Clicking Elements

**Pattern**: `[click action] [element description]`

**Click Actions** (all equivalent):
- click
- press
- tap
- select
- activate

**Examples**:
```
✅ "Click the login button"
✅ "Press the search link"
✅ "Tap the submit button"
✅ "Select the first result"
✅ "Click the blue button at the top"
✅ "Press the menu icon"
```

**With Position**:
```
✅ "Click the button on the right"
✅ "Select the first link"
✅ "Press the bottom button"
✅ "Click the third item"
```

**With Description**:
```
✅ "Click the red subscribe button"
✅ "Press the login button in the header"
✅ "Select the search result about climate change"
```

### Scrolling

**Basic Scrolling**:
```
✅ "Scroll down"
✅ "Scroll up"
✅ "Page down"
✅ "Page up"
```

**Distance Scrolling**:
```
✅ "Scroll down a little"
✅ "Scroll down a lot"
✅ "Scroll up halfway"
```

**Position Scrolling**:
```
✅ "Scroll to the top"
✅ "Scroll to the bottom"
✅ "Go to the top of the page"
✅ "Jump to the bottom"
```

**Element Scrolling**:
```
✅ "Scroll to the comments"
✅ "Scroll to the footer"
✅ "Scroll to the next section"
```

### Page Navigation

**Back and Forward**:
```
✅ "Go back"
✅ "Go forward"
✅ "Back to the previous page"
✅ "Forward one page"
```

**Refresh**:
```
✅ "Refresh the page"
✅ "Reload this page"
✅ "Refresh"
```

**New Tabs**:
```
✅ "Open in new tab"
✅ "Open this link in a new tab"
```

## Information Commands

### Location Queries

**Where Am I?**
```
✅ "Where am I?"
✅ "What website is this?"
✅ "What site am I on?"
✅ "What app am I in?"
✅ "What page is this?"
```

**Response Examples**:
- "You're on Google.com - I can see the search homepage"
- "You're in Gmail - viewing your inbox"
- "You're on BBC News - the main news page"

### Screen Description

**Full Description**:
```
✅ "What do you see?"
✅ "Describe the screen"
✅ "What's on the page?"
✅ "Tell me what's visible"
✅ "Describe what you see"
```

**Focused Description**:
```
✅ "What's at the top of the page?"
✅ "Describe the header"
✅ "What's in the sidebar?"
✅ "Tell me about the main content"
✅ "What buttons are available?"
```

### Content Reading

**Read Content**:
```
✅ "Read the article"
✅ "Read this page"
✅ "What does it say?"
✅ "Read the main content"
✅ "Read the first paragraph"
```

**Read Specific Elements**:
```
✅ "Read the headline"
✅ "What's the title?"
✅ "Read the first search result"
✅ "What does the button say?"
```

### Available Actions

**What Can I Do?**
```
✅ "What can I do here?"
✅ "What options are available?"
✅ "What actions can I take?"
✅ "Help me navigate this page"
✅ "What should I do next?"
```

## Action Commands

### Typing Text

**Pattern**: `[type action] [text content]`

**Type Actions** (all equivalent):
- type
- enter
- write
- input

**Examples**:
```
✅ "Type hello world"
✅ "Enter my email address"
✅ "Write a message"
✅ "Input search query"
```

**In Specific Fields**:
```
✅ "Type john@example.com in the email field"
✅ "Enter my password"
✅ "Write hello in the message box"
✅ "Type search term in the search box"
```

**Special Characters**:
```
✅ "Type hello@example.com"
✅ "Enter 123 Main Street"
✅ "Type question mark"
✅ "Enter dollar sign 50"
```

### Form Filling

**Identify Fields**:
```
✅ "What fields are on this form?"
✅ "What information do I need to provide?"
✅ "List the form fields"
```

**Fill Fields**:
```
✅ "Fill in the name field with John Smith"
✅ "Enter my email in the email field"
✅ "Type my address in the address field"
```

**Submit Forms**:
```
✅ "Submit the form"
✅ "Click submit"
✅ "Send the form"
```

### Search Operations

**Perform Search**:
```
✅ "Search for best restaurants"
✅ "Look up climate change"
✅ "Find information about Python programming"
```

**View Results**:
```
✅ "What are the search results?"
✅ "Read the first result"
✅ "Tell me about the top results"
✅ "What did you find?"
```

**Refine Search**:
```
✅ "Search again for Italian restaurants"
✅ "Narrow the search to London"
✅ "Filter by date"
```

## Context Commands

### Referencing Previous Elements

Spectra remembers what she just described. You can reference it:

**Pattern 1: Direct Reference**
```
You: "What's the first search result?"
Spectra: "The first result is Wikipedia..."
You: "Click it" ← Spectra clicks the Wikipedia link
```

**Pattern 2: Pronoun Reference**
```
You: "Describe the blue button"
Spectra: "The blue button says 'Subscribe'..."
You: "Press it" ← Spectra presses the subscribe button
```

**Pattern 3: That/This Reference**
```
You: "What's that link about?"
Spectra: "That link goes to the about page..."
You: "Open that" ← Spectra opens the about page
```

**Valid Context References**:
- "Click it"
- "Press that"
- "Select this"
- "Open it"
- "Read that"
- "Tell me more about it"

### Multi-Step Commands

**Sequential Actions**:
```
✅ "Scroll down and read the first paragraph"
✅ "Click the search button and wait for results"
✅ "Type hello world and press enter"
```

**Conditional Actions**:
```
✅ "If there's a login button, click it"
✅ "Find the search box and type my query"
✅ "Look for the subscribe button and press it"
```

## System Commands

### Session Control

**Start/Stop**:
```
✅ "Hello Spectra" (to start conversation)
✅ "Hey Spectra" (wake word)
✅ "Stop" (to stop current action)
✅ "Pause" (to pause reading)
✅ "Continue" (to resume)
```

**Screen Sharing**:
```
✅ "Enable screen sharing"
✅ "Turn on screen sharing"
✅ "Let me share my screen"
✅ "Stop screen sharing"
✅ "Turn off screen sharing"
```

### Help and Clarification

**Request Help**:
```
✅ "Help"
✅ "What can you do?"
✅ "How do I [task]?"
✅ "I need help with [task]"
```

**Clarification**:
```
✅ "What did you say?"
✅ "Can you repeat that?"
✅ "Say that again"
✅ "I didn't understand"
```

**Confirmation**:
```
✅ "Are you sure?"
✅ "Confirm that action"
✅ "Yes, do it"
✅ "No, cancel"
```

## Advanced Patterns

### Compound Queries

**Information + Action**:
```
✅ "Find the login button and click it"
✅ "Look for search results and read the first one"
✅ "Check if there's a subscribe button and press it"
```

**Multiple Conditions**:
```
✅ "If you see a popup, close it, then scroll down"
✅ "Find the email field, type my address, then submit"
```

### Descriptive Targeting

**By Colour**:
```
✅ "Click the red button"
✅ "Select the blue link"
✅ "Press the green submit button"
```

**By Position**:
```
✅ "Click the button at the top right"
✅ "Select the first item in the list"
✅ "Press the bottom button"
✅ "Click the third link"
```

**By Text Content**:
```
✅ "Click the button that says 'Login'"
✅ "Select the link about climate change"
✅ "Press the 'Subscribe Now' button"
```

**By Context**:
```
✅ "Click the login button in the header"
✅ "Select the search result about Python"
✅ "Press the submit button in the form"
```

### Spelling and Special Input

**Spelling Out Words**:
```
✅ "Type S-M-I-T-H"
✅ "Enter my name spelled J-O-H-N"
✅ "Spell out my email: j-o-h-n at example dot com"
```

**Special Characters**:
```
✅ "Type at sign" → @
✅ "Enter dollar sign" → $
✅ "Type hashtag" → #
✅ "Enter asterisk" → *
✅ "Type forward slash" → /
```

**Numbers**:
```
✅ "Type one two three" → 123
✅ "Enter fifty dollars" → 50
✅ "Type the number five" → 5
```

### Workflow Patterns

**Email Workflow**:
```
1. "Go to Gmail"
2. "What emails do I have?"
3. "Open the first email"
4. "Read it to me"
5. "Reply to this email"
6. "Type [your message]"
7. "Send the email"
```

**Shopping Workflow**:
```
1. "Go to Amazon"
2. "Search for wireless headphones"
3. "What are the top results?"
4. "Tell me about the first product"
5. "Add it to cart"
6. "Go to checkout"
```

**Research Workflow**:
```
1. "Go to Google"
2. "Search for climate change effects"
3. "Read the first result"
4. "Scroll down"
5. "What are the key points?"
6. "Open the second result in a new tab"
```

## Command Tips

### For Best Recognition

**DO**:
- ✅ Speak clearly at normal pace
- ✅ Use natural, conversational language
- ✅ Be specific when multiple elements exist
- ✅ Use context references for efficiency
- ✅ Try variations if first attempt doesn't work

**DON'T**:
- ❌ Speak too slowly or robotically
- ❌ Use overly technical jargon
- ❌ Rush through commands
- ❌ Assume Spectra knows unstated context
- ❌ Give up after one attempt

### When Commands Don't Work

**If Spectra doesn't understand**:
1. Try a command variation
2. Be more specific about the element
3. Ask Spectra to describe what she sees first
4. Use position or colour descriptors

**Example**:
```
❌ "Click the button" (too vague if multiple buttons)
✅ "Click the blue login button at the top"
```

### Efficiency Tips

**Use Context**:
```
Instead of:
"What's the first result?"
"Click the first result"

Try:
"What's the first result?"
"Click it" ← Faster!
```

**Combine Actions**:
```
Instead of:
"Scroll down"
"Read the next paragraph"

Try:
"Scroll down and read the next paragraph" ← One command!
```

**Be Specific First Time**:
```
Instead of:
"Click the button"
"No, the other button"
"The blue one"

Try:
"Click the blue submit button" ← Gets it right first time!
```

## Language and Variations

### British vs American English

Spectra understands both:
```
✅ "Colour" or "Color"
✅ "Centre" or "Center"
✅ "Favourite" or "Favorite"
```

### Formal vs Casual

Both work equally well:
```
Formal: "Please navigate to Google.com"
Casual: "Go to Google"
Both work! ✅
```

### Questions vs Commands

Both forms are understood:
```
Question: "Can you click the login button?"
Command: "Click the login button"
Both work! ✅
```

## Troubleshooting Commands

### If Spectra Can't Find an Element

**Try**:
1. "Describe the screen" - See what Spectra sees
2. "What buttons are available?" - List options
3. "Scroll down" - Element might be off-screen
4. Use more specific description - Colour, position, text

### If Action Doesn't Execute

**Check**:
1. Screen sharing is enabled (press W)
2. Element is visible on screen
3. Page has finished loading
4. Try alternative command variation

### If Spectra Misunderstands

**Clarify**:
1. "No, I meant [clarification]"
2. "Cancel that"
3. "Let me try again"
4. Use more specific language

## Quick Reference Card

### Most Common Commands

| Task | Command |
|------|---------|
| Where am I? | "Where am I?" |
| Describe screen | "What do you see?" |
| Click element | "Click the [element]" |
| Type text | "Type [text]" |
| Scroll | "Scroll down/up" |
| Go to website | "Go to [website]" |
| Search | "Search for [query]" |
| Go back | "Go back" |
| Read content | "Read the article" |
| Help | "What can I do here?" |

### Command Variations Quick List

**Click**: click, press, tap, select, activate
**Type**: type, enter, write, input
**Navigate**: go to, open, visit, navigate to
**Describe**: what do you see, describe, tell me about
**Read**: read, what does it say, tell me

---

## Practice Exercises

### Exercise 1: Basic Navigation
1. "Go to Google"
2. "What do you see?"
3. "Type best coffee shops"
4. "Click the search button"
5. "What are the results?"

### Exercise 2: Using Context
1. "What's the first search result?"
2. "Click it" ← Uses context
3. "Read the article"
4. "Scroll down"
5. "What's next?"

### Exercise 3: Complex Task
1. "Go to Gmail"
2. "What emails do I have?"
3. "Open the first unread email"
4. "Read it to me"
5. "Reply to this email"
6. "Type thank you for your message"
7. "Send the email"

---

**Remember**: Spectra understands natural language. Don't memorise commands - just talk naturally and use variations that feel comfortable to you!
