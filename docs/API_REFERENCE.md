# Spectra API Reference

Quick reference guide for Spectra's core APIs and components.

## Table of Contents

- [Performance Monitor](#performance-monitor)
- [Error Handler](#error-handler)
- [Location Context Handler](#location-context-handler)
- [Voice Command Processor](#voice-command-processor)
- [REST API Endpoints](#rest-api-endpoints)

## Performance Monitor

### Import

```python
from backend.app.performance_monitor import get_performance_monitor, PerformanceMonitor
```

### Quick Start

```python
# Get global instance
monitor = get_performance_monitor()

# Monitor vision call
result = await monitor.monitor_vision_call(vision_api.analyze, frame_data)

# Record metrics
monitor.record_action_result(success=True)
monitor.record_cache_hit()

# Get statistics
stats = monitor.get_performance_stats()
```

### Methods

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `monitor_vision_call` | `func, *args, **kwargs` | `Any` | Monitor async function execution |
| `record_action_result` | `success: bool` | `None` | Record action success/failure |
| `record_cache_hit` | - | `None` | Record cache hit |
| `record_cache_miss` | - | `None` | Record cache miss |
| `get_cache_hit_rate` | - | `float` | Get cache hit rate (0-100) |
| `get_action_success_rate` | - | `float` | Get action success rate (0-100) |
| `get_vision_success_rate` | - | `float` | Get vision success rate (0-100) |
| `get_performance_stats` | - | `Dict[str, Any]` | Get all performance metrics |
| `reset_metrics` | - | `None` | Reset all metrics |
| `log_performance_summary` | - | `None` | Log performance summary |

### Performance Stats Structure

```python
{
    "vision_metrics": {
        "avg_response_time": float,      # seconds
        "p95_response_time": float,      # seconds
        "min_response_time": float,
        "max_response_time": float,
        "total_calls": int,
        "failed_calls": int,
        "success_rate": float,           # percentage
        "slow_responses": int,
        "slow_response_threshold": float
    },
    "action_metrics": {
        "total_actions": int,
        "success_rate": float            # percentage
    },
    "cache_metrics": {
        "hits": int,
        "misses": int,
        "hit_rate": float,               # percentage
        "total_operations": int
    },
    "system_metrics": {
        "uptime_seconds": float,
        "uptime_hours": float
    },
    "alerts": [
        {
            "severity": str,             # "warning" or "critical"
            "metric": str,
            "message": str
        }
    ]
}
```

## Error Handler

### Import

```python
from backend.app.error_handler import error_handler, ErrorCategory
```

### Quick Start

```python
try:
    result = await vision_api.analyze(frame_data)
except Exception as e:
    # Handle error with logging and user message
    message = error_handler.handle_vision_error(
        error=e,
        frame_hash=frame_hash,
        session_id=session_id
    )
    
    # Check if should retry
    if error_handler.should_retry(e, attempt):
        delay = error_handler.get_retry_delay(attempt, category)
        await asyncio.sleep(delay)
```

### Error Categories

```python
class ErrorCategory(Enum):
    VISION_API = "vision_api"
    NETWORK = "network"
    AUTHENTICATION = "authentication"
    RATE_LIMIT = "rate_limit"
    FRAME_PROCESSING = "frame_processing"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"
```

### Methods

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `categorize_error` | `error: Exception` | `ErrorCategory` | Categorize error type |
| `handle_vision_error` | `error, frame_hash, frame_size, ...` | `str` | Handle error with logging |
| `should_retry` | `error, retry_attempt, max_retries` | `bool` | Check if should retry |
| `get_retry_delay` | `retry_attempt, category` | `float` | Get retry delay in seconds |
| `get_error_statistics` | - | `Dict[str, Any]` | Get error statistics |
| `log_api_request` | `endpoint, method, headers, ...` | `Dict` | Log API request |
| `log_api_response` | `request_details, status_code, ...` | `Dict` | Log API response |
| `is_deflection_response` | `response: str` | `bool` | Check for deflection phrases |

### Retry Delays by Category

| Category | Attempt 0 | Attempt 1 | Attempt 2 |
|----------|-----------|-----------|-----------|
| RATE_LIMIT | 0.5s | 1.5s | 4.5s |
| NETWORK | 0.5s | 1.0s | 2.0s |
| TIMEOUT | 0.5s | 0.75s | 1.125s |
| AUTHENTICATION | No retry | - | - |
| FRAME_PROCESSING | No retry | - | - |

## Location Context Handler

### Import

```python
from backend.app.location_context_handler import LocationContextHandler, LocationInfo
```

### Quick Start

```python
handler = LocationContextHandler()

# Check if location query
if handler.is_location_query("where am i?"):
    # Get screen description
    screen_desc = await vision_system.describe_screen(frame_data)
    
    # Handle query
    response = await handler.handle_location_query(
        query=user_query,
        screen_description=screen_desc
    )
```

### Methods

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `is_location_query` | `query: str` | `bool` | Check if location query |
| `extract_location_info` | `screen_description: str` | `LocationInfo` | Extract location from description |
| `format_location_response` | `location_info, fallback_description` | `str` | Format user response |
| `handle_location_query` | `query, screen_description` | `Optional[str]` | Handle location query |

### LocationInfo Structure

```python
@dataclass
class LocationInfo:
    site_name: Optional[str] = None      # e.g., "Google"
    url: Optional[str] = None            # e.g., "google.com"
    app_name: Optional[str] = None       # e.g., "Chrome"
    page_title: Optional[str] = None     # e.g., "Search Results"
    context: Optional[str] = None        # e.g., "search engine"
    confidence: float = 0.0              # 0.0 to 1.0
```

### Supported Websites (15+)

- Google, Gmail, YouTube
- Facebook, Twitter/X, LinkedIn, Instagram
- Amazon, Netflix, Spotify
- GitHub, Stack Overflow, Wikipedia
- Reddit, Discord

### Supported Applications (20+)

- Browsers: Chrome, Firefox, Safari, Edge
- Development: VS Code
- Office: Word, Excel, PowerPoint, Outlook
- Communication: Teams, Zoom, Slack
- Design: Photoshop, Illustrator, Figma
- Productivity: Notion, Trello

## Voice Command Processor

### Import

```python
from backend.app.voice_command_processor import (
    VoiceCommandProcessor,
    CommandAction,
    ParsedCommand,
    CommandContext
)
```

### Quick Start

```python
processor = VoiceCommandProcessor()

# Parse command
cmd = processor.parse_command("click the login button")

# Update context
processor.update_context(
    screen_description=vision_result,
    mentioned_element="search button"
)

# Parse context-dependent command
cmd = processor.parse_command("click it")

# Format for execution
execution = processor.format_command_for_execution(cmd)
```

### Command Actions

```python
class CommandAction(Enum):
    CLICK = "click"
    TYPE = "type"
    NAVIGATE = "navigate"
    SCROLL = "scroll"
    READ = "read"
    FIND = "find"
    WAIT = "wait"
    UNKNOWN = "unknown"
```

### Methods

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `is_voice_command` | `text: str` | `bool` | Check if text is command |
| `parse_command` | `text, context` | `ParsedCommand` | Parse natural language |
| `update_context` | `screen_description, mentioned_element, ...` | `None` | Update context |
| `get_command_help` | - | `Dict[str, List[str]]` | Get command examples |
| `format_command_for_execution` | `command` | `Dict[str, Any]` | Format for execution |

### ParsedCommand Structure

```python
@dataclass
class ParsedCommand:
    action: CommandAction                           # Command action
    target: Optional[str] = None                    # Target element
    parameters: Optional[Dict[str, Any]] = None     # Additional params
    confidence: float = 0.0                         # 0.0 to 1.0
    original_text: str = ""                         # Original input
    context_dependent: bool = False                 # Uses context
    compound: bool = False                          # Multiple commands
    sub_commands: Optional[List['ParsedCommand']] = None
    suggestions: Optional[List[str]] = None         # If unknown
```

### Command Variations

| Action | Variations |
|--------|-----------|
| CLICK | click, press, tap, select, choose, activate |
| TYPE | type, enter, write, input, fill in |
| NAVIGATE | go to, open, visit, navigate to, browse to |
| SCROLL | scroll, page, move |
| READ | read, tell me, describe, explain |
| FIND | find, search, look for, locate |

### Example Commands

```python
# Simple commands
"click the login button"
"type hello world"
"scroll down"
"go to google.com"

# Context-dependent
"click it"              # Refers to last mentioned element
"type in that"          # Refers to last mentioned field
"do that again"         # Repeats last action

# Compound commands
"scroll down and read the first paragraph"
"click the menu and then select settings"
"type my name and press enter"

# Natural language
"please click the blue button"
"could you scroll down a bit"
"I want to type hello world"
```

## REST API Endpoints

### Health Check

```http
GET /api/health
```

**Response**:
```json
{
  "status": "healthy",
  "timestamp": 1234567890.0,
  "metrics": { ... },
  "thresholds": {
    "vision_response_time": "< 2.0s",
    "vision_success_rate": "> 95%",
    "cache_hit_rate": "> 70%"
  }
}
```

### Performance Dashboard

```http
GET /api/performance/dashboard
```

**Response**:
```json
{
  "vision": {
    "avg_response_time": 1.2,
    "p95_response_time": 2.1,
    "success_rate": 97.5,
    "total_calls": 1000,
    "slow_responses": 5
  },
  "actions": {
    "total": 500,
    "success_rate": 98.0
  },
  "cache": {
    "hit_rate": 75.0,
    "total_operations": 800
  },
  "errors": {
    "total": 10,
    "rate": 0.5,
    "by_category": {
      "network": 5,
      "timeout": 3,
      "rate_limit": 2
    }
  },
  "alerts": []
}
```

### Vision Health

```http
GET /api/vision/health
```

**Response**:
```json
{
  "status": "healthy",
  "performance": { ... },
  "errors": { ... },
  "recommendations": [
    "Consider optimizing frame size or caching"
  ]
}
```

### WebSocket Connection

```http
WS /ws/session/{session_id}
```

**Message Format**:
```json
{
  "type": "audio" | "text" | "screen_frame" | "action",
  "data": { ... },
  "timestamp": 1234567890.0
}
```

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `GOOGLE_API_KEY` | Gemini API key | - | Yes |
| `ENVIRONMENT` | Environment name | development | No |
| `LOG_LEVEL` | Logging level | INFO | No |
| `CORS_ORIGINS` | Allowed CORS origins | * | No |
| `SENTRY_DSN` | Sentry DSN for error tracking | - | No |

### Performance Thresholds

| Metric | Target | Alert Threshold |
|--------|--------|----------------|
| Vision Response Time | < 2.0s | > 2.0s |
| Vision Success Rate | > 95% | < 95% |
| Cache Hit Rate | > 70% | < 70% |
| Slow Response Threshold | - | > 3.0s |
| Error Rate | < 1.0/min | > 1.0/min |

## Error Codes

| Code | Category | Description | Retry |
|------|----------|-------------|-------|
| 401 | AUTHENTICATION | Invalid API key | No |
| 429 | RATE_LIMIT | Rate limit exceeded | Yes |
| 500 | VISION_API | API error | Yes |
| 503 | NETWORK | Network error | Yes |
| 504 | TIMEOUT | Request timeout | Yes |

## Quick Reference

### Common Patterns

#### Monitor Vision Call
```python
monitor = get_performance_monitor()
result = await monitor.monitor_vision_call(func, *args)
```

#### Handle Error with Retry
```python
for attempt in range(3):
    try:
        result = await api_call()
        break
    except Exception as e:
        if not error_handler.should_retry(e, attempt):
            raise
        delay = error_handler.get_retry_delay(attempt, category)
        await asyncio.sleep(delay)
```

#### Process Location Query
```python
if handler.is_location_query(query):
    screen_desc = await vision_system.describe_screen(frame)
    response = await handler.handle_location_query(query, screen_desc)
```

#### Parse Voice Command
```python
cmd = processor.parse_command(text)
if cmd.action != CommandAction.UNKNOWN:
    execution = processor.format_command_for_execution(cmd)
    await execute_action(execution)
```

---

**Version**: 1.0.0  
**Last Updated**: 2024  
**Full Documentation**: [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md)
