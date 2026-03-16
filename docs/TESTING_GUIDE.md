# 🧪 Spectra Testing Guide

Complete guide to testing Spectra, including unit tests, integration tests, E2E tests, and performance testing.

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Backend Testing](#backend-testing)
4. [Frontend Testing](#frontend-testing)
5. [E2E Testing](#e2e-testing)
6. [Performance Testing](#performance-testing)
7. [Writing Tests](#writing-tests)
8. [CI/CD Integration](#cicd-integration)
9. [Troubleshooting](#troubleshooting)

---

## Overview

Spectra uses a comprehensive testing strategy:

- **Backend**: pytest for Python tests
- **Frontend**: Jest/Vitest for TypeScript/React tests
- **E2E**: Playwright for end-to-end testing
- **Load**: Locust for performance testing

### Test Coverage Goals

| Component | Target | Current |
|-----------|--------|---------|
| Backend | 90% | ~75% |
| Frontend | 85% | ~40% |
| E2E | 100% critical flows | ~20% |
| Performance | All benchmarks | ✅ |

---

## Quick Start

### Run All Tests

```bash
./run-tests.sh
```

### Run Specific Test Suites

```bash
# Backend only
./run-tests.sh --backend-only

# Frontend only
./run-tests.sh --frontend-only

# With coverage
./run-tests.sh --coverage

# Verbose output
./run-tests.sh --verbose

# E2E tests
./run-tests.sh --e2e
```

---

## Backend Testing

### Setup

```bash
cd backend

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov pytest-mock
```

### Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_orchestrator.py

# Run specific test
pytest tests/test_orchestrator.py::TestOrchestrator::test_basic_command

# Run with coverage
pytest --cov=app --cov-report=html tests/

# Run with markers
pytest -m integration tests/
pytest -m "not slow" tests/
```

### Test Structure

```
backend/tests/
├── test_orchestrator.py          # Agent orchestration
├── test_session.py               # Session management
├── test_memory.py                # Memory system
├── test_error_handler.py         # Error handling
├── test_performance_monitor.py   # Performance tracking
├── test_api_endpoints.py         # API endpoints (NEW)
├── test_connection_recovery.py   # Connection resilience (NEW)
├── test_fast_pipeline.py         # Fast pipeline
├── test_orchestrator_integration.py  # Integration tests
└── load/
    └── test_concurrent_users.py  # Load testing
```

### Writing Backend Tests

```python
import pytest
from backend.app.main import app

class TestMyFeature:
    """Test my feature"""
    
    def test_basic_functionality(self):
        """Test basic functionality"""
        result = my_function()
        assert result == expected_value
    
    @pytest.mark.asyncio
    async def test_async_functionality(self):
        """Test async functionality"""
        result = await my_async_function()
        assert result is not None
    
    @pytest.mark.integration
    async def test_integration(self):
        """Test integration with other components"""
        # Integration test code
        pass
    
    @pytest.mark.slow
    def test_slow_operation(self):
        """Test slow operation"""
        # Slow test code
        pass
```

### Test Markers

```python
# Mark tests with categories
@pytest.mark.unit          # Unit tests
@pytest.mark.integration   # Integration tests
@pytest.mark.slow          # Slow tests (>1s)
@pytest.mark.asyncio       # Async tests
@pytest.mark.load          # Load tests
@pytest.mark.security      # Security tests
```

---

## Frontend Testing

### Setup

```bash
cd frontend

# Install dependencies
npm install

# Install test dependencies
npm install --save-dev @testing-library/react @testing-library/jest-dom
npm install --save-dev @playwright/test vitest
```

### Running Tests

```bash
# Run all tests
npm run test

# Run specific test file
npm run test -- OnboardingGuide.test.tsx

# Run with coverage
npm run test:coverage

# Watch mode
npm run test:watch

# E2E tests
npm run test:e2e
```

### Test Structure

```
frontend/tests/
├── components/
│   ├── OnboardingGuide.test.tsx
│   ├── VoiceControls.test.tsx
│   └── ActionFeedback.test.tsx
├── hooks/
│   ├── useSpectraSocket.test.ts (NEW)
│   ├── useScreenCapture.test.ts
│   └── useWakeWord.test.ts
├── lib/
│   ├── actionExecutor.test.ts
│   └── audioPlayer.test.ts
├── accessibility.test.ts
├── audio-ducking.test.ts
└── e2e/
    ├── user-journey.spec.ts
    └── accessibility.spec.ts
```

### Writing Frontend Tests

#### Component Tests

```typescript
import { render, screen, fireEvent } from '@testing-library/react';
import { MyComponent } from '@/components/MyComponent';

describe('MyComponent', () => {
  it('renders correctly', () => {
    render(<MyComponent />);
    expect(screen.getByText(/expected text/i)).toBeInTheDocument();
  });

  it('handles user interaction', () => {
    const onClick = jest.fn();
    render(<MyComponent onClick={onClick} />);
    
    const button = screen.getByRole('button');
    fireEvent.click(button);
    
    expect(onClick).toHaveBeenCalled();
  });

  it('updates state correctly', () => {
    const { rerender } = render(<MyComponent value="initial" />);
    expect(screen.getByText('initial')).toBeInTheDocument();
    
    rerender(<MyComponent value="updated" />);
    expect(screen.getByText('updated')).toBeInTheDocument();
  });
});
```

#### Hook Tests

```typescript
import { renderHook, act } from '@testing-library/react';
import { useMyHook } from '@/hooks/useMyHook';

describe('useMyHook', () => {
  it('initializes with default values', () => {
    const { result } = renderHook(() => useMyHook());
    
    expect(result.current.value).toBe(defaultValue);
  });

  it('updates value correctly', () => {
    const { result } = renderHook(() => useMyHook());
    
    act(() => {
      result.current.setValue('new value');
    });
    
    expect(result.current.value).toBe('new value');
  });

  it('handles async operations', async () => {
    const { result } = renderHook(() => useMyHook());
    
    await act(async () => {
      await result.current.fetchData();
    });
    
    expect(result.current.data).toBeDefined();
  });
});
```

---

## E2E Testing

### Setup

```bash
cd frontend

# Install Playwright
npm install --save-dev @playwright/test
npx playwright install
```

### Running E2E Tests

```bash
# Run all E2E tests
npm run test:e2e

# Run in headed mode (see browser)
npm run test:e2e -- --headed

# Run specific test
npm run test:e2e -- user-journey.spec.ts

# Debug mode
npm run test:e2e -- --debug

# Generate report
npm run test:e2e -- --reporter=html
```

### Writing E2E Tests

```typescript
import { test, expect } from '@playwright/test';

test.describe('User Journey', () => {
  test.beforeEach(async ({ page, context }) => {
    // Grant permissions
    await context.grantPermissions(['microphone', 'display-capture']);
    
    // Navigate to app
    await page.goto('http://localhost:3000');
  });

  test('complete user flow', async ({ page }) => {
    // Start Spectra
    await page.keyboard.press('q');
    await expect(page.locator('[data-testid="status"]')).toHaveText('Listening');
    
    // Share screen
    await page.keyboard.press('w');
    
    // Verify UI state
    await expect(page.locator('[data-testid="screen-sharing"]')).toBeVisible();
    
    // Simulate voice command
    await page.evaluate(() => {
      window.spectraSocket.send({
        type: 'text',
        data: 'Click the submit button'
      });
    });
    
    // Wait for action
    await expect(page.locator('[data-testid="action-feedback"]')).toBeVisible();
  });

  test('keyboard navigation', async ({ page }) => {
    // Test keyboard shortcuts
    await page.keyboard.press('q');
    await expect(page.locator('[data-testid="status"]')).toHaveText('Listening');
    
    await page.keyboard.press('Escape');
    await expect(page.locator('[data-testid="status"]')).toHaveText('Stopped');
  });

  test('accessibility', async ({ page }) => {
    // Test with screen reader
    const accessibilityTree = await page.accessibility.snapshot();
    expect(accessibilityTree).toBeDefined();
    
    // Test focus management
    await page.keyboard.press('Tab');
    const focusedElement = await page.evaluate(() => document.activeElement?.tagName);
    expect(focusedElement).toBe('BUTTON');
  });
});
```

---

## Performance Testing

### Setup

```bash
cd backend

# Install Locust
pip install locust
```

### Running Load Tests

```bash
# Start Locust web UI
locust -f tests/load/test_concurrent_users.py --host=http://localhost:8080

# Run from command line
locust -f tests/load/test_concurrent_users.py \
  --headless \
  --users 100 \
  --spawn-rate 10 \
  --run-time 5m \
  --host=http://localhost:8080
```

### Writing Load Tests

```python
from locust import HttpUser, task, between
import json

class SpectraUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        """Called when a user starts"""
        self.session_id = None
    
    @task(3)
    def websocket_session(self):
        """Simulate WebSocket session"""
        with self.client.websocket_connect("/ws") as ws:
            # Receive connection message
            data = ws.receive_json()
            self.session_id = data.get("session_id")
            
            # Send audio
            ws.send_json({
                "type": "audio",
                "data": "base64_audio_data"
            })
            
            # Send screenshot
            ws.send_json({
                "type": "screenshot",
                "data": "base64_image_data",
                "width": 1280,
                "height": 720
            })
            
            # Receive response
            response = ws.receive_json()
    
    @task(1)
    def health_check(self):
        """Check health endpoint"""
        self.client.get("/health")
```

### Performance Benchmarks

```bash
# Run performance benchmarks
cd backend
python scripts/benchmark_fast_pipeline.py
python scripts/benchmark_orchestrator.py
```

---

## Writing Tests

### Best Practices

1. **Test Naming**: Use descriptive names
   ```python
   # Good
   def test_user_can_click_button_after_voice_command():
       pass
   
   # Bad
   def test_click():
       pass
   ```

2. **Arrange-Act-Assert**: Structure tests clearly
   ```python
   def test_feature():
       # Arrange: Set up test data
       user = create_test_user()
       
       # Act: Perform action
       result = user.perform_action()
       
       # Assert: Verify result
       assert result.success is True
   ```

3. **Test Independence**: Tests should not depend on each other
   ```python
   # Good: Each test is independent
   def test_feature_a():
       setup_test_data()
       # test code
   
   def test_feature_b():
       setup_test_data()
       # test code
   ```

4. **Mock External Dependencies**: Don't call real APIs
   ```python
   @patch('backend.app.streaming.session.GeminiClient')
   def test_with_mock(mock_client):
       mock_client.return_value.send.return_value = "response"
       # test code
   ```

5. **Test Edge Cases**: Don't just test happy path
   ```python
   def test_handles_empty_input():
       result = process_input("")
       assert result.error == "Input cannot be empty"
   
   def test_handles_invalid_input():
       result = process_input("invalid")
       assert result.error == "Invalid input format"
   ```

### Test Coverage

```bash
# Backend coverage
cd backend
pytest --cov=app --cov-report=html tests/
open htmlcov/index.html

# Frontend coverage
cd frontend
npm run test:coverage
open coverage/index.html
```

### Coverage Goals

- **Critical paths**: 100% coverage
- **Core functionality**: 90%+ coverage
- **UI components**: 85%+ coverage
- **Utilities**: 80%+ coverage

---

## CI/CD Integration

### GitHub Actions

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install pytest pytest-cov
      - name: Run tests
        run: |
          cd backend
          pytest --cov=app --cov-report=xml tests/
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./backend/coverage.xml

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '20'
      - name: Install dependencies
        run: |
          cd frontend
          npm install
      - name: Run tests
        run: |
          cd frontend
          npm run test:coverage
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./frontend/coverage/coverage-final.json

  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '20'
      - name: Install dependencies
        run: |
          cd frontend
          npm install
          npx playwright install --with-deps
      - name: Run E2E tests
        run: |
          cd frontend
          npm run test:e2e
```

---

## Troubleshooting

### Common Issues

#### Backend Tests Failing

```bash
# Check Python version
python --version  # Should be 3.11+

# Reinstall dependencies
cd backend
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Clear pytest cache
rm -rf .pytest_cache
pytest --cache-clear tests/
```

#### Frontend Tests Failing

```bash
# Check Node version
node --version  # Should be 20+

# Reinstall dependencies
cd frontend
rm -rf node_modules package-lock.json
npm install

# Clear Jest cache
npm run test -- --clearCache
```

#### E2E Tests Failing

```bash
# Reinstall Playwright
cd frontend
npx playwright install --with-deps

# Run in headed mode to debug
npm run test:e2e -- --headed --debug
```

#### WebSocket Tests Failing

```bash
# Check if backend is running
curl http://localhost:8080/health

# Check WebSocket connection
wscat -c ws://localhost:8080/ws
```

### Debug Tips

1. **Use verbose output**: `pytest -v` or `npm run test -- --verbose`
2. **Run single test**: Focus on failing test
3. **Check logs**: Look at test output and logs
4. **Use debugger**: `pytest --pdb` or `debugger;` in JS
5. **Mock external services**: Don't rely on real APIs

---

## Test Metrics

### Current Status

```
Backend Tests:     17 files, ~150 tests
Frontend Tests:    2 files, ~20 tests
E2E Tests:         0 files (planned)
Load Tests:        1 file

Backend Coverage:  ~75%
Frontend Coverage: ~40%
```

### Goals

```
Backend Tests:     25+ files, 300+ tests
Frontend Tests:    15+ files, 150+ tests
E2E Tests:         5+ files, 50+ tests
Load Tests:        3+ files

Backend Coverage:  90%+
Frontend Coverage: 85%+
```

---

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [Testing Library](https://testing-library.com/)
- [Playwright Documentation](https://playwright.dev/)
- [Locust Documentation](https://docs.locust.io/)
- [Jest Documentation](https://jestjs.io/)

---

**Happy Testing! 🧪**
