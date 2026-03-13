# Contributing to Spectra

Thank you for your interest in contributing to Spectra! 

## Quick Start for Contributors

```bash
# 1. Fork and clone
git clone https://github.com/YOUR-USERNAME/spectra.git
cd spectra

# 2. Set up backend
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Add your GOOGLE_API_KEY to .env

# 3. Set up frontend
cd ../frontend
npm install
cp .env.local.example .env.local

# 4. Run both (from root)
cd ..
./run.sh
```

Visit http://localhost:3000 and say "Hey Spectra" to test.

---

## Ways to Contribute

### 🐛 Report Bugs
Create a GitHub issue with:
- Clear description of the problem
- Steps to reproduce
- Expected vs actual behaviour
- Screenshots or logs
- Environment (OS, browser, versions)

### 💡 Suggest Features
Create an issue with:
- Description of the feature
- Use case and benefits
- Proposed implementation (optional)
- Mockups or examples (optional)

### 🔧 Submit Code
1. Fork the repo
2. Create a branch: `git checkout -b feature/your-feature`
3. Make changes
4. Test thoroughly
5. Commit: `git commit -m "feat: add new feature"`
6. Push: `git push origin feature/your-feature`
7. Open a Pull Request

### 📝 Improve Documentation
- Fix typos
- Add examples
- Clarify instructions
- Translate to other languages

### ♿ Test Accessibility
- Test with screen readers (NVDA, JAWS, VoiceOver)
- Test keyboard navigation
- Report accessibility issues
- Suggest improvements

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
| `test:` | Adding tests |
| `chore:` | Maintenance |
| `a11y:` | Accessibility improvements |

Examples:
```
feat: add voice confirmation sound
fix: resolve WebSocket race condition
docs: update demo script
a11y: improve screen reader announcements
```

---

## 🏗️ Project Structure

```
spectra/
├── backend/                 # FastAPI + Gemini Live API
│   ├── app/
│   │   ├── main.py          # WebSocket endpoint
│   │   ├── agents/          # System instructions + tools
│   │   ├── streaming/       # Gemini session manager
│   │   └── tools/           # Screen tools (diff, snapshot)
│   └── requirements.txt
├── frontend/                # Next.js + React
│   ├── src/
│   │   ├── app/             # Pages
│   │   ├── hooks/           # React hooks
│   │   └── lib/             # Utilities
│   └── package.json
├── extension/               # Chrome extension
│   ├── manifest.json
│   ├── background.js
│   └── content.js
└── docs/                    # Documentation
```

---

## 🎯 Priority Areas

### 🔴 High Priority (Most Needed)
- **Screen reader testing** — Test with NVDA, JAWS, VoiceOver
- **Voice activation improvements** — Better wake word detection
- **Browser extension features** — More reliable click targeting
- **Error handling** — Graceful failures with user feedback
- **Multi-language support** — Expand beyond UK English

### 🟡 Medium Priority
- **Performance optimisation** — Reduce latency
- **Mobile accessibility** — Touch + voice on mobile
- **Custom voice preferences** — Speed, verbosity, voice selection
- **Form auto-fill** — Voice-driven form completion
- **Documentation** — Tutorials, examples, API docs

### 🟢 Nice to Have
- **Additional themes** — High contrast, dark mode variants
- **Keyboard shortcut customisation**
- **Session history** — Review past interactions
- **Demo mode** — Pre-loaded screenshots for demos
- **Screenshot preview** — Show what Spectra sees

---

## 📝 Code Style

### Python (Backend)
```python
# Use type hints
async def describe_screen(self, focus: str) -> str:
    """Analyse screenshot and return description for blind user."""
    ...

# Use docstrings
# Follow PEP 8
# Format with black: black .
# Lint with flake8: flake8 .
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
```

### Accessibility Requirements
All UI contributions must:
- ✅ Work without a mouse
- ✅ Work with screen readers
- ✅ Have keyboard shortcuts
- ✅ Provide clear audio/visual feedback
- ✅ Use proper ARIA labels
- ✅ Follow WCAG 2.1 AA standards

---

## 🧪 Testing

### Manual Testing Checklist
- [ ] Voice activation ("Hey Spectra")
- [ ] Screen capture starts
- [ ] Microphone works
- [ ] Text commands work
- [ ] Click actions execute
- [ ] Type actions execute
- [ ] Scroll actions execute
- [ ] Diff detection works
- [ ] Teach me app works
- [ ] Stop/cancel works
- [ ] Keyboard shortcuts (Q, W, Esc)
- [ ] Screen reader announces correctly
- [ ] Tab navigation works

### Backend Tests
```bash
cd backend
pytest
```

### Frontend Tests
```bash
cd frontend
npm test
```

---

## 🔒 Security

- **Never commit API keys** — Use `.env` files
- **No PII in examples** — Use placeholder data
- **Report vulnerabilities privately** — Email hello@aqta.ai
- **Review dependencies** — Check for known vulnerabilities

---

## 🙋‍♀️ Getting Help

| Channel | Use for |
|---------|---------|
| GitHub Issues | Bugs, features |
| GitHub Discussions | Questions, ideas |
| Email (hello@aqta.ai) | Private matters, security |

---

## 📜 Code of Conduct

We are committed to a welcoming environment for all contributors.

**Be respectful.** Treat everyone with kindness.

**Be inclusive.** Welcome people of all backgrounds.

**Be constructive.** Focus on improving the project.

**Be patient.** Remember that everyone is learning.

Violations may result in warnings or bans. Report issues to hello@aqta.ai.

---

## 🏆 Recognition

Contributors are:
- Listed in README.md
- Credited in release notes
- Mentioned in blog posts (with permission)

---

## 📄 License

By contributing, you agree that your contributions will be licensed under the [Apache License 2.0](LICENSE).

---

## 🙏 Thank You

Every contribution makes a difference. Whether you're fixing a typo, reporting a bug or adding a feature — thank you for helping make the web more accessible!

**Ready to contribute?** [Fork the repo](https://github.com/Aqta-ai/spectra/fork) and start coding! 🚀
