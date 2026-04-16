# Contributing to Spectra

Thank you for your interest in contributing to Spectra! This guide will help you get started.

## Quick Start for Contributors

```bash
# 1. Fork and clone
git clone https://github.com/YOUR-USERNAME/spectra.git
cd spectra

# 2. Set up backend
cd backend
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Add your GOOGLE_API_KEY or GOOGLE_CLOUD_PROJECT to .env

# 3. Set up frontend
cd ../frontend
npm install
cp .env.local.example .env.local

# 4. Install Chrome extension
# Go to chrome://extensions → Enable Developer Mode → Load Unpacked → select extension/

# 5. Run both (from root)
cd ..
./run.sh
```

Visit http://localhost:3000, press Q, and start talking to test.

---

## Ways to Contribute

### 🐛 Report Bugs
Create a GitHub issue with:
- Clear description of the problem
- Steps to reproduce
- Expected vs actual behaviour
- Screenshots or logs
- Environment (OS, browser, Node/Python versions)

### 💡 Suggest Features
Create an issue with:
- Description of the feature
- Use case and benefits (especially accessibility benefits)
- Proposed implementation (optional)
- Mockups or examples (optional)

### 🔧 Submit Code
1. Fork the repo
2. Create a branch: `git checkout -b feature/your-feature`
3. Make changes
4. Test thoroughly (see Testing section below)
5. Commit: `git commit -m "feat: add new feature"`
6. Push: `git push origin feature/your-feature`
7. Open a Pull Request with a clear description

### 📝 Improve Documentation
- Fix typos and clarify instructions
- Add examples and tutorials
- Update API documentation
- Translate to other languages
- Add accessibility testing guides

### ♿ Test Accessibility
- Test with screen readers (NVDA, JAWS, VoiceOver, TalkBack)
- Test keyboard navigation
- Test with voice control only
- Report accessibility issues
- Suggest improvements for blind/low-vision users

---

## 📋 Commit Convention

Use [Conventional Commits](https://www.conventionalcommits.org/):

| Prefix | Use for |
|--------|---------|
| `feat:` | New feature |
| `fix:` | Bug fix |
| `docs:` | Documentation |
| `style:` | Formatting (no code change) |
| `refactor:` | Code restructuring |
| `perf:` | Performance improvements |
| `test:` | Adding tests |
| `chore:` | Maintenance |
| `a11y:` | Accessibility improvements |

Examples:
```
feat: add voice confirmation sound
fix: resolve WebSocket race condition
docs: update overlay API documentation
a11y: improve screen reader announcements
perf: optimize overlay fetch speed
```

---

## 🏗️ Project Structure

```
spectra/
├── backend/                 # FastAPI + Gemini Live API
│   ├── app/
│   │   ├── main.py          # WebSocket endpoint + health check
│   │   ├── overlay.py       # Overlay API for page analysis
│   │   ├── agents/          # System instructions + orchestrator
│   │   ├── streaming/       # Gemini Live session manager
│   │   ├── tools/           # Browser tools (screen, diff)
│   │   └── intelligence/    # Context engine
│   ├── tests/               # 20 test files (pytest)
│   └── requirements.txt
├── frontend/                # Next.js 14 + React + TypeScript
│   ├── src/
│   │   ├── app/             # Pages (main, overlay, guide, privacy)
│   │   ├── hooks/           # React hooks (audio, screen, socket)
│   │   ├── lib/             # Utilities (action executor, audio player)
│   │   └── components/      # React components
│   ├── tests/               # Frontend tests (vitest)
│   └── package.json
├── extension/               # Chrome extension (MV3)
│   ├── manifest.json
│   ├── background.js        # Service worker
│   └── content.js           # DOM action executor
├── infra/                   # Terraform for Cloud Run
└── docs/                    # Documentation
```

---

## 🎯 Priority Areas

### High Priority (Most Needed)
- **Screen reader testing** — Test with NVDA, JAWS, VoiceOver, TalkBack
- **Voice activation improvements** — Better wake word detection, reduce false positives
- **Browser extension reliability** — More accurate click targeting, better error handling
- **Error handling** — Graceful failures with clear user feedback
- **Multi-language support** — Test and improve non-English voice commands
- **Performance optimisation** — Reduce latency in voice-to-action pipeline

### Medium Priority
- **Mobile accessibility** — Touch + voice on mobile browsers
- **Custom voice preferences** — Speed, verbosity, voice selection
- **Form auto-fill** — Voice-driven form completion
- **Documentation** — Tutorials, video guides, API docs
- **Overlay enhancements** — Faster analysis, more element types
- **Session persistence** — Remember user preferences

### Nice to Have
- **Additional themes** — High contrast, dark mode variants
- **Keyboard shortcut customisation**
- **Session history** — Review past interactions
- **Screenshot preview** — Show what Spectra sees
- **Browser extension for Firefox/Edge**
- **Offline mode improvements**

---

## 📝 Code Style

### Python (Backend)
```python
# Use type hints
async def describe_screen(self, focus: str) -> str:
    """Analyse screenshot and return description for blind user."""
    ...

# Use docstrings for all public functions
# Follow PEP 8
# Format with black: black .
# Lint with flake8: flake8 .
# Keep functions focused and small
```

### TypeScript (Frontend)
```typescript
// Use TypeScript types (avoid `any`)
interface Message {
  role: "user" | "spectra";
  text: string;
  timestamp: number;
}

// Use functional components with hooks
// Add JSDoc for complex functions
// Run: npm run lint
// Use meaningful variable names
```

### Accessibility Requirements
All UI contributions must:
- ✅ Work without a mouse (keyboard only)
- ✅ Work with screen readers (proper ARIA labels)
- ✅ Have keyboard shortcuts documented
- ✅ Provide clear audio/visual feedback
- ✅ Use semantic HTML
- ✅ Follow WCAG 2.1 AA standards
- ✅ Test with actual assistive technology

---

## 🧪 Testing

### Manual Testing Checklist
- [ ] Voice activation ("Hey Spectra")
- [ ] Screen capture starts and streams
- [ ] Microphone captures audio
- [ ] Voice commands work ("What's on screen?", "Click the button")
- [ ] Click actions execute correctly
- [ ] Type actions work in inputs
- [ ] Scroll actions work
- [ ] Navigation works ("Go to bbc.com")
- [ ] Stop/cancel works (Escape key, "Stop")
- [ ] Keyboard shortcuts (Q, W, Escape)
- [ ] Screen reader announces correctly
- [ ] Tab navigation works
- [ ] Overlay page loads and analyses URLs
- [ ] Extension is detected and functional

### Backend Tests
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest tests/ -v

# Run specific test categories
pytest tests/test_session.py -v
pytest tests/test_wcag_compliance.py -v
pytest tests/test_blind_user_experience.py -v
```

### Frontend Tests
```bash
cd frontend
npm install
npm test

# Run accessibility tests
npm run test:a11y
```

### Testing with Screen Readers
- **Windows:** NVDA (free) or JAWS
- **macOS:** VoiceOver (built-in)
- **Linux:** Orca
- **Mobile:** TalkBack (Android), VoiceOver (iOS)

---

## 🚀 Performance Guidelines

When contributing, keep performance in mind:

- **Backend:** Keep API responses under 2 seconds
- **Frontend:** Optimise bundle size, lazy load components
- **Overlay:** Limit HTML processing to 20KB, cache results
- **Audio:** Use efficient PCM streaming, minimise latency
- **Screen capture:** Keep at 2 FPS, use adaptive quality

---

## Security

- **Never commit API keys** — Use `.env` files (gitignored)
- **No PII in examples** — Use placeholder data like [name], [email]
- **Report vulnerabilities privately** — Email hello@aqta.ai
- **Review dependencies** — Check for known vulnerabilities
- **Validate user input** — Sanitize URLs, prevent injection attacks

---

## 🙋‍♀️ Getting Help

| Channel | Use for |
|---------|---------|
| GitHub Issues | Bugs, feature requests |
| GitHub Discussions | Questions, ideas, general discussion |
| Email (hello@aqta.ai) | Private matters, security issues |

---

## 📜 Code of Conduct

We are committed to a welcoming environment for all contributors.

**Be respectful.** Treat everyone with kindness and empathy.

**Be inclusive.** Welcome people of all backgrounds, abilities, and experience levels.

**Be constructive.** Focus on improving the project and helping others.

**Be patient.** Remember that everyone is learning and contributing in their own way.

Violations may result in warnings or bans. Report issues to hello@aqta.ai.

---

## 🏆 Recognition

Contributors are:
- Listed in README.md acknowledgments
- Credited in release notes
- Mentioned in blog posts (with permission)
- Invited to join the Spectra community

---

## 📄 Licence

By contributing, you agree that your contributions will be licenced under the [Apache Licence 2.0](LICENSE).

---

## 💡 Tips for First-Time Contributors

- Start with documentation improvements or bug fixes
- Look for issues labelled `good first issue` or `help wanted`
- Ask questions if anything is unclear
- Test your changes thoroughly before submitting
- Keep PRs focused on a single change
- Be patient with the review process

---

## 🙏 Thank You

Every contribution makes a difference. Whether you're fixing a typo, reporting a bug, or adding a feature — thank you for helping make the web more accessible!

**Ready to contribute?** [Fork the repo](https://github.com/Aqta-ai/spectra/fork) and start coding! 🚀

---

Built with 💜 for the accessibility community by [Anya Chueayen](https://github.com/anyapages) and contributors.

**GitHub:** [github.com/Aqta-ai/spectra](https://github.com/Aqta-ai/spectra)
