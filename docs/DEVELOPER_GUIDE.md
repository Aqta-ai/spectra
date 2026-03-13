# Spectra Developer Guide

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Core Components](#core-components)
3. [API Documentation](#api-documentation)
4. [Vision System Debugging](#vision-system-debugging)
5. [Performance Monitoring](#performance-monitoring)
6. [Development Workflow](#development-workflow)
7. [Testing](#testing)
8. [Deployment](#deployment)

## Architecture Overview

Spectra is an AI-powered accessibility assistant designed to help blind and visually impaired users interact with their computers through voice commands and screen analysis. The system consists of several key components working together to provide a seamless hands-free experience.

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (React)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Voice Input  │  │ Audio Output │  │ Screen Share │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            │
                    WebSocket Connection
                            │
┌─────────────────────────────────────────────────────────────┐
│                    Backend (FastAPI + Python)                │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Gemini Live API Integration              │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   Vision     │  │    Voice     │  │   Location   │    │
│  │   System     │  │   Command    │  │   Context    │    │
│  │              │  │   Processor  │  │   Handler    │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │    Error     │  │ Performance  │  │    Action    │    │
│  │   Handler    │  │   Monitor    │  │   Executor   │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────┘
                            │
                    Browser Extension
                            │
┌─────────────────────────────────────────────────────────────┐
│                    Chrome Extension                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Content    │  │  Background  │  │    Action    │     │
│  │   Script     │  │    Script    │  │   Injector   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **User Input**: Voice commands captured by frontend
2. **WebSocket Streaming**: Real-time bidirectional communication with backend
3. **Gemini Live API**: Processes voice input and generates responses
4. **Vision Analysis**: Screen frames analyzed using Gemini Vision API
5. **Command Processing**: Natural language commands parsed and executed
6. **Action Execution**: Browser extension executes UI actions
7. **Audio Response**: Text-to-speech output delivered to user

### Key Design Principles

- **Accessibility First**: Every feature designed for blind and visually impaired users
- **Real-time Performance**: Sub-2-second response times for vision analysis
- **Reliability**: Comprehensive error handling and retry logic
- **Context Awareness**: Maintains conversation and screen context
- **Natural Language**: Supports command variations and compound commands

## Core Components

### 1. Performance Monitor

The `PerformanceMonitor` class tracks system performance metrics and provides alerts for degradation.

**Location**: `backend/app/performance_monitor.py`

**Key Features**:
- Vision API response time tracking
- Action success rate monitoring
- Cache hit rate calculation
- Automatic performance degradation alerts
- Comprehensive statistics reporting

**Usage Example**:
```python
from backend.app.performance_monitor import get_performance_monitor

# Get the global performance monitor instance
monitor = get_performance_monitor()

# Monitor a vision API call
async def analyze_screen(frame_data):
    result = await monitor.monitor_vision_call(
        vision_api.analyze,
        frame_data
    )
    return result

# Record action results
monitor.record_action_result(success=True)

# Record cache operations
monitor.record_cache_hit()
monitor.record_cache_miss()

# Get performance statistics
stats = monitor.get_performance_stats()
print(f"Average vision response time: {stats['vision_metrics']['avg_response_time']}s")
print(f"Cache hit rate: {stats['cache_metrics']['hit_rate']}%")
```

**Performance Thresholds**:
- Vision response time target: < 2 seconds
- Vision success rate target: > 95%
- Cache hit rate target: > 70%
- Slow response threshold: 3 seconds

### 2. Error Handler

The `SpectraErrorHandler` class provides comprehensive error handling with detailed logging and user-friendly messages.

**Location**: `backend/app/error_handler.py`

**Key Features**:
- Structured error categorization
- Detailed logging with context information
- User-friendly error messages with debugging hints
- Retry logic coordination
- Error statistics and pattern analysis

**Error Categories**:
- `VISION_API`: Gemini Vision API errors
- `NETWORK`: Network connectivity issues
- `AUTHENTICATION`: API key or authentication problems
- `RATE_LIMIT`: API rate limiting
- `FRAME_PROCESSING`: Screen capture processing errors
- `TIMEOUT`: Request timeout errors
- `UNKNOWN`: Unclassified errors

**Usage Example**:
```python
from backend.app.error_handler import error_handler

try:
    result = await vision_api.analyze(frame_data)
except Exception as e:
    # Handle the error with comprehensive logging
    user_message = error_handler.handle_vision_error(
        error=e,
        frame_hash=frame_hash,
        frame_size=len(frame_data),
        session_id=session_id,
        retry_attempt=attempt
    )
    
    # Check if we should retry
    if error_handler.should_retry(e, attempt):
        delay = error_handler.get_retry_delay(attempt, category)
        await asyncio.sleep(delay)
        # Retry the operation
    else:
        # Return error message to user
        return user_message
```

**Retry Strategy**:
- Authentication errors: No retry (requires configuration fix)
- Rate limit errors: Exponential backoff (0.5s, 1.5s, 4.5s)
- Network errors: Exponential backoff (0.5s, 1.0s, 2.0s)
- Timeout errors: Standard backoff (0.5s, 0.75s, 1.125s)

### 3. Location Context Handler

The `LocationContextHandler` class processes location queries to help users understand what website or application they're viewing.

**Location**: `backend/app/location_context_handler.py`

**Key Features**:
- Location query detection
- Website and application identification
- Enhanced pattern matching with UI element recognition
- Logo and visual brand detection
- Confidence-based response formatting

**Usage Example**:
```python
from backend.app.location_context_handler import LocationContextHandler

handler = LocationContextHandler()

# Check if query is asking about location
if handler.is_location_query(user_query):
    # Get screen description from vision system
    screen_description = await vision_system.describe_screen(frame_data)
    
    # Handle the location query
    response = await handler.handle_location_query(
        query=user_query,
        screen_description=screen_description
    )
    
    # Response will be like: "You're on Google.com - search engine"
    return response
```

**Supported Websites** (15+ with enhanced detection):
- Google, Gmail, YouTube
- Facebook, Twitter/X, LinkedIn, Instagram
- Amazon, Netflix, Spotify
- GitHub, Stack Overflow, Wikipedia
- Reddit, Discord

**Supported Applications** (20+ with UI pattern matching):
- Browsers: Chrome, Firefox, Safari, Edge
- Development: VS Code, IDEs
- Office: Word, Excel, PowerPoint, Outlook
- Communication: Teams, Zoom, Slack, Discord
- Design: Photoshop, Illustrator, Figma
- Productivity: Notion, Trello

### 4. Voice Command Processor

The `VoiceCommandProcessor` class parses natural language voice commands into structured actions.

**Location**: `backend/app/voice_command_processor.py`

**Key Features**:
- Natural language command parsing
- Support for command variations
- Context-dependent command resolution
- Compound command handling
- Command suggestions for ambiguous input

**Supported Actions**:
- `CLICK`: Click, press, tap, select elements
- `TYPE`: Type, enter, write text
- `NAVIGATE`: Go to, open, visit URLs/pages
- `SCROLL`: Scroll, page up/down
- `READ`: Read, describe screen content
- `FIND`: Find, search, locate elements
- `WAIT`: Wait, pause execution

**Usage Example**:
```python
from backend.app.voice_command_processor import VoiceCommandProcessor, CommandContext

processor = VoiceCommandProcessor()

# Parse a simple command
command = processor.parse_command("click the login button")
print(f"Action: {command.action.value}")  # "click"
print(f"Target: {command.target}")  # "login button"
print(f"Confidence: {command.confidence}")  # 0.9

# Parse a context-dependent command
processor.update_context(mentioned_element="search button")
command = processor.parse_command("click it")
print(f"Target: {command.target}")  # "search button"
print(f"Context dependent: {command.context_dependent}")  # True

# Parse a compound command
command = processor.parse_command("scroll down and read the first paragraph")
print(f"Compound: {command.compound}")  # True
print(f"Sub-commands: {len(command.sub_commands)}")  # 2

# Get command suggestions for unknown input
command = processor.parse_command("do something")
if command.action == CommandAction.UNKNOWN:
    print(f"Suggestions: {command.suggestions}")

# Format command for execution
execution_format = processor.format_command_for_execution(command)
```

**Command Variations Supported**:
- Click: "click", "press", "tap", "select", "choose", "activate"
- Type: "type", "enter", "write", "input", "fill in"
- Navigate: "go to", "open", "visit", "navigate to", "browse to"
- Scroll: "scroll", "page", "move"

**Context Resolution**:
The processor maintains context to resolve pronouns and references:
- "click it" → resolves to last mentioned element
- "type in that" → resolves to last mentioned field
- "do that again" → repeats last action



## API Documentation

### Performance Monitor API

#### Class: `PerformanceMonitor`

**Constructor**:
```python
PerformanceMonitor(slow_response_threshold: float = 3.0)
```

**Parameters**:
- `slow_response_threshold`: Threshold in seconds for slow response alerts (default: 3.0)

**Methods**:

##### `monitor_vision_call(func, *args, **kwargs) -> Any`
Monitor a vision API call and track its performance.

**Parameters**:
- `func`: The async function to monitor
- `*args`: Positional arguments for the function
- `**kwargs`: Keyword arguments for the function

**Returns**: The result from the monitored function

**Raises**: Re-raises any exception from the monitored function

**Example**:
```python
result = await monitor.monitor_vision_call(
    vision_api.analyze_screen,
    frame_data,
    focus="full"
)
```

##### `record_action_result(success: bool) -> None`
Record the result of an action execution.

**Parameters**:
- `success`: Whether the action succeeded

##### `record_cache_hit() -> None`
Record a cache hit.

##### `record_cache_miss() -> None`
Record a cache miss.

##### `get_cache_hit_rate() -> float`
Calculate the cache hit rate.

**Returns**: Cache hit rate as a percentage (0-100), or 0 if no cache operations

##### `get_action_success_rate() -> float`
Calculate the action success rate.

**Returns**: Action success rate as a percentage (0-100), or 0 if no actions

##### `get_vision_success_rate() -> float`
Calculate the vision API success rate.

**Returns**: Vision success rate as a percentage (0-100), or 0 if no calls

##### `get_performance_stats() -> Dict[str, Any]`
Get comprehensive performance statistics.

**Returns**: Dictionary containing:
```python
{
    "vision_metrics": {
        "avg_response_time": float,  # Average response time in seconds
        "p95_response_time": float,  # 95th percentile response time
        "min_response_time": float,  # Minimum response time
        "max_response_time": float,  # Maximum response time
        "total_calls": int,          # Total vision API calls
        "failed_calls": int,         # Number of failed calls
        "success_rate": float,       # Success rate percentage
        "slow_responses": int,       # Count of slow responses
        "slow_response_threshold": float  # Threshold for slow responses
    },
    "action_metrics": {
        "total_actions": int,        # Total actions executed
        "success_rate": float        # Action success rate percentage
    },
    "cache_metrics": {
        "hits": int,                 # Cache hits
        "misses": int,               # Cache misses
        "hit_rate": float,           # Hit rate percentage
        "total_operations": int      # Total cache operations
    },
    "system_metrics": {
        "uptime_seconds": float,     # System uptime in seconds
        "uptime_hours": float        # System uptime in hours
    },
    "alerts": List[Dict[str, str]]   # Active performance alerts
}
```

##### `reset_metrics() -> None`
Reset all performance metrics.

##### `log_performance_summary() -> None`
Log a summary of current performance metrics.

**Global Functions**:

##### `get_performance_monitor() -> PerformanceMonitor`
Get the global performance monitor instance.

**Returns**: The global PerformanceMonitor instance

##### `reset_performance_monitor() -> None`
Reset the global performance monitor instance.

---

### Error Handler API

#### Class: `SpectraErrorHandler`

**Constructor**:
```python
SpectraErrorHandler()
```

**Methods**:

##### `categorize_error(error: Exception) -> ErrorCategory`
Categorize an error based on its type and message.

**Parameters**:
- `error`: The exception to categorize

**Returns**: ErrorCategory enum value

##### `handle_vision_error(...) -> str`
Handle vision system errors with comprehensive logging and user feedback.

**Parameters**:
```python
handle_vision_error(
    error: Exception,
    frame_hash: Optional[str] = None,
    frame_size: Optional[int] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    retry_attempt: int = 0,
    api_request_details: Optional[Dict[str, Any]] = None,
    api_response_details: Optional[Dict[str, Any]] = None,
    additional_context: Optional[Dict[str, Any]] = None
) -> str
```

**Returns**: User-friendly error message with debugging hints

**Example**:
```python
try:
    result = await vision_api.analyze(frame_data)
except Exception as e:
    message = error_handler.handle_vision_error(
        error=e,
        frame_hash=hashlib.md5(frame_data).hexdigest(),
        frame_size=len(frame_data),
        session_id=session.id,
        retry_attempt=0
    )
    logger.error(message)
```

##### `should_retry(error: Exception, retry_attempt: int, max_retries: int = 3) -> bool`
Determine if an error should trigger a retry attempt.

**Parameters**:
- `error`: The exception that occurred
- `retry_attempt`: Current retry attempt number (0-based)
- `max_retries`: Maximum number of retry attempts (default: 3)

**Returns**: True if the error should be retried, False otherwise

##### `get_retry_delay(retry_attempt: int, category: ErrorCategory) -> float`
Calculate appropriate delay before retry based on error category.

**Parameters**:
- `retry_attempt`: Current retry attempt number (0-based)
- `category`: Error category

**Returns**: Delay in seconds before next retry attempt

##### `get_error_statistics() -> Dict[str, Any]`
Get error statistics for monitoring and debugging.

**Returns**: Dictionary containing:
```python
{
    "total_errors": int,                    # Total errors in history
    "categories": Dict[str, int],           # Error count by category
    "recent_errors": List[Dict[str, Any]],  # Last 10 recent errors
    "error_rate": float                     # Errors per minute
}
```

##### `log_api_request(...) -> Dict[str, Any]`
Log API request details for debugging.

**Parameters**:
```python
log_api_request(
    endpoint: str,
    method: str = "POST",
    headers: Optional[Dict[str, str]] = None,
    payload_size: Optional[int] = None,
    frame_hash: Optional[str] = None,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None
) -> Dict[str, Any]
```

**Returns**: Request details dictionary for correlation with response

##### `log_api_response(...) -> Dict[str, Any]`
Log API response details for debugging.

**Parameters**:
```python
log_api_response(
    request_details: Dict[str, Any],
    status_code: Optional[int] = None,
    response_size: Optional[int] = None,
    response_time_ms: Optional[float] = None,
    error: Optional[Exception] = None,
    response_headers: Optional[Dict[str, str]] = None
) -> Dict[str, Any]
```

**Returns**: Response details dictionary

##### `is_deflection_response(response: str) -> bool`
Check if a response contains deflection phrases that should be filtered out.

**Parameters**:
- `response`: The response text to check

**Returns**: True if the response contains deflection phrases, False otherwise

**Deflection Phrases Detected**:
- "i have limitations"
- "i cannot see"
- "as an ai"
- "i don't have access"
- "i'm not able to"
- "i can't actually see"

**Global Instance**:
```python
from backend.app.error_handler import error_handler

# Use the global error handler instance
message = error_handler.handle_vision_error(error)
```

---

### Location Context Handler API

#### Class: `LocationContextHandler`

**Constructor**:
```python
LocationContextHandler()
```

**Methods**:

##### `is_location_query(query: str) -> bool`
Determine if the user's query is asking about their current location.

**Parameters**:
- `query`: The user's input text

**Returns**: True if this is a location query, False otherwise

**Location Query Patterns**:
- "where am i"
- "what site am i on"
- "what website is this"
- "what app am i in"
- "what page is this"

**Example**:
```python
handler = LocationContextHandler()

if handler.is_location_query("where am i?"):
    # Process as location query
    pass
```

##### `extract_location_info(screen_description: str) -> LocationInfo`
Extract location information from a screen description.

**Parameters**:
- `screen_description`: The description of the current screen content

**Returns**: LocationInfo object with extracted information

**LocationInfo Fields**:
```python
@dataclass
class LocationInfo:
    site_name: Optional[str] = None      # Website name (e.g., "Google")
    url: Optional[str] = None            # URL if detected
    app_name: Optional[str] = None       # Application name
    page_title: Optional[str] = None     # Page title
    context: Optional[str] = None        # Context (e.g., "search engine")
    confidence: float = 0.0              # Confidence score (0.0-1.0)
```

##### `format_location_response(location_info: LocationInfo, fallback_description: str = "") -> str`
Format a user-friendly response about the user's current location.

**Parameters**:
- `location_info`: The extracted location information
- `fallback_description`: Optional fallback description if location cannot be determined

**Returns**: A formatted response string

**Response Examples**:
- High confidence: "You're on Google.com - search engine"
- Medium confidence: "You're on a page titled 'Welcome to GitHub'"
- Low confidence: "I can see your screen but cannot determine the specific website or application"

##### `async handle_location_query(query: str, screen_description: str) -> Optional[str]`
Handle a location query by analyzing screen content and returning a formatted response.

**Parameters**:
- `query`: The user's query text
- `screen_description`: The current screen description from vision analysis

**Returns**: A formatted location response, or None if this is not a location query

**Complete Example**:
```python
handler = LocationContextHandler()

# In your message processing loop
if handler.is_location_query(user_message):
    # Get fresh screen analysis
    screen_description = await vision_system.describe_screen(frame_data)
    
    # Handle the location query
    response = await handler.handle_location_query(
        query=user_message,
        screen_description=screen_description
    )
    
    # Send response to user
    await send_response(response)
```

---

### Voice Command Processor API

#### Class: `VoiceCommandProcessor`

**Constructor**:
```python
VoiceCommandProcessor()
```

**Enums**:

##### `CommandAction`
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

**Data Classes**:

##### `ParsedCommand`
```python
@dataclass
class ParsedCommand:
    action: CommandAction                           # The command action
    target: Optional[str] = None                    # Target element or text
    parameters: Optional[Dict[str, Any]] = None     # Additional parameters
    confidence: float = 0.0                         # Confidence score (0.0-1.0)
    original_text: str = ""                         # Original input text
    context_dependent: bool = False                 # Uses context resolution
    compound: bool = False                          # Is compound command
    sub_commands: Optional[List['ParsedCommand']] = None  # Sub-commands
    suggestions: Optional[List[str]] = None         # Suggestions if unknown
```

##### `CommandContext`
```python
@dataclass
class CommandContext:
    last_mentioned_element: Optional[str] = None
    current_page_elements: Optional[List[str]] = None
    recent_commands: Optional[List[ParsedCommand]] = None
    screen_description: Optional[str] = None
    conversation_history: Optional[List[str]] = None
```

**Methods**:

##### `is_voice_command(text: str) -> bool`
Determine if the input text contains a voice command.

**Parameters**:
- `text`: The user's input text

**Returns**: True if this appears to be a voice command, False otherwise

##### `parse_command(text: str, context: Optional[CommandContext] = None) -> ParsedCommand`
Parse natural language text into a structured command.

**Parameters**:
- `text`: The user's input text
- `context`: Optional context information for command resolution

**Returns**: ParsedCommand object with parsed information

**Example**:
```python
processor = VoiceCommandProcessor()

# Simple command
cmd = processor.parse_command("click the login button")
print(f"Action: {cmd.action.value}")  # "click"
print(f"Target: {cmd.target}")        # "login button"
print(f"Confidence: {cmd.confidence}") # 0.9

# Context-dependent command
processor.update_context(mentioned_element="search box")
cmd = processor.parse_command("type hello world in it")
print(f"Target: {cmd.target}")        # "search box"
print(f"Context: {cmd.context_dependent}")  # True

# Compound command
cmd = processor.parse_command("scroll down and read the first paragraph")
print(f"Compound: {cmd.compound}")    # True
print(f"Sub-commands: {len(cmd.sub_commands)}")  # 2
```

##### `update_context(...) -> None`
Update the command context with new information.

**Parameters**:
```python
update_context(
    screen_description: str = None,
    mentioned_element: str = None,
    recent_command: ParsedCommand = None,
    conversation_history: List[str] = None
)
```

**Example**:
```python
# Update context after screen analysis
processor.update_context(
    screen_description=vision_result,
    mentioned_element="submit button"
)

# Update after command execution
processor.update_context(
    recent_command=executed_command
)
```

##### `get_command_help() -> Dict[str, List[str]]`
Get help information about supported commands.

**Returns**: Dictionary mapping command types to example commands

**Example**:
```python
help_info = processor.get_command_help()
for category, examples in help_info.items():
    print(f"{category}:")
    for example in examples:
        print(f"  - {example}")
```

##### `format_command_for_execution(command: ParsedCommand) -> Dict[str, Any]`
Format a parsed command for execution by the action system.

**Parameters**:
- `command`: The parsed command

**Returns**: Dictionary formatted for execution

**Example**:
```python
cmd = processor.parse_command("click the menu button")
execution_format = processor.format_command_for_execution(cmd)

# execution_format will be:
{
    "type": "command",
    "action": "click",
    "target": "menu button",
    "parameters": {},
    "confidence": 0.9,
    "context_dependent": False,
    "original_text": "click the menu button"
}
```



## Vision System Debugging

### Common Vision System Issues

#### 1. Vision API Returns Deflection Responses

**Symptoms**:
- Responses like "I have limitations" or "I cannot see"
- Generic responses instead of actual screen descriptions

**Diagnosis**:
```python
from backend.app.error_handler import error_handler

# Check if response is a deflection
if error_handler.is_deflection_response(vision_result):
    logger.warning("Deflection response detected")
```

**Solutions**:
- Check system instruction for conflicting guidance
- Verify screen frame quality and size
- Ensure proper focus parameter is set
- Review Gemini API model version compatibility

#### 2. Authentication Errors (401)

**Symptoms**:
- "Invalid API key" errors
- 401 Unauthorized responses

**Diagnosis**:
```bash
# Check if API key is set
echo $GOOGLE_API_KEY

# Test API key validity
curl -H "Authorization: Bearer $GOOGLE_API_KEY" \
  https://generativelanguage.googleapis.com/v1/models
```

**Solutions**:
1. Verify `GOOGLE_API_KEY` in `backend/.env`
2. Ensure API key has Gemini API access enabled
3. Check API key hasn't expired
4. Verify no extra whitespace in API key

#### 3. Rate Limiting (429)

**Symptoms**:
- "Rate limit exceeded" errors
- 429 Too Many Requests responses

**Diagnosis**:
```python
# Check error statistics
stats = error_handler.get_error_statistics()
rate_limit_errors = stats['categories'].get('rate_limit', 0)
print(f"Rate limit errors: {rate_limit_errors}")
```

**Solutions**:
1. Implement request throttling
2. Increase cache hit rate to reduce API calls
3. Upgrade API quota if needed
4. Use exponential backoff (automatically handled by error handler)

#### 4. Slow Vision Response Times

**Symptoms**:
- Vision analysis takes > 3 seconds
- Performance alerts for slow responses

**Diagnosis**:
```python
# Check performance metrics
monitor = get_performance_monitor()
stats = monitor.get_performance_stats()

print(f"Average response time: {stats['vision_metrics']['avg_response_time']}s")
print(f"P95 response time: {stats['vision_metrics']['p95_response_time']}s")
print(f"Slow responses: {stats['vision_metrics']['slow_responses']}")
```

**Solutions**:
1. Optimize frame size (compress images)
2. Increase cache TTL for similar frames
3. Use regional API endpoints closer to your location
4. Check network latency
5. Consider using lower resolution frames

#### 5. Frame Processing Errors

**Symptoms**:
- "Frame processing error" messages
- Invalid frame data errors

**Diagnosis**:
```python
# Validate frame data
import base64

try:
    frame_bytes = base64.b64decode(frame_data)
    print(f"Frame size: {len(frame_bytes)} bytes")
    
    # Check if it's valid image data
    from PIL import Image
    import io
    img = Image.open(io.BytesIO(frame_bytes))
    print(f"Image format: {img.format}, Size: {img.size}")
except Exception as e:
    print(f"Frame validation error: {e}")
```

**Solutions**:
1. Verify screen capture is working properly
2. Check frame encoding (should be base64 JPEG)
3. Ensure frame size is within API limits
4. Validate frame data before sending to API

### Debugging Tools

#### Enable Debug Logging

```python
# In backend/app/main.py or your module
import logging

# Set logging level to DEBUG
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Enable debug logging for specific modules
logging.getLogger('backend.app.error_handler').setLevel(logging.DEBUG)
logging.getLogger('backend.app.performance_monitor').setLevel(logging.DEBUG)
```

#### Vision System Test Script

Create `backend/test_vision_debug.py`:

```python
import asyncio
import base64
import logging
from backend.app.error_handler import error_handler
from backend.app.performance_monitor import get_performance_monitor

logging.basicConfig(level=logging.DEBUG)

async def test_vision_system():
    """Test vision system with debug output."""
    monitor = get_performance_monitor()
    
    # Load test frame
    with open('test_frame.jpg', 'rb') as f:
        frame_data = base64.b64encode(f.read()).decode('utf-8')
    
    print(f"Frame size: {len(frame_data)} bytes")
    
    # Test vision analysis with monitoring
    try:
        result = await monitor.monitor_vision_call(
            vision_api.analyze_screen,
            frame_data,
            focus="full"
        )
        
        print(f"Result: {result}")
        
        # Check for deflection
        if error_handler.is_deflection_response(result):
            print("WARNING: Deflection response detected!")
        
    except Exception as e:
        message = error_handler.handle_vision_error(
            error=e,
            frame_hash="test",
            frame_size=len(frame_data)
        )
        print(f"Error: {message}")
    
    # Print statistics
    stats = monitor.get_performance_stats()
    print(f"\nPerformance Stats:")
    print(f"  Response time: {stats['vision_metrics']['avg_response_time']}s")
    print(f"  Success rate: {stats['vision_metrics']['success_rate']}%")

if __name__ == "__main__":
    asyncio.run(test_vision_system())
```

#### API Request/Response Logging

```python
# Enable detailed API logging
from backend.app.error_handler import error_handler

# Log API request
request_details = error_handler.log_api_request(
    endpoint="https://generativelanguage.googleapis.com/v1/models/gemini-pro-vision:generateContent",
    method="POST",
    headers={"Content-Type": "application/json"},
    payload_size=len(frame_data),
    frame_hash=frame_hash,
    session_id=session_id
)

# Make API call
try:
    response = await api_call()
    
    # Log successful response
    error_handler.log_api_response(
        request_details=request_details,
        status_code=200,
        response_size=len(response),
        response_time_ms=response_time
    )
except Exception as e:
    # Log failed response
    error_handler.log_api_response(
        request_details=request_details,
        error=e
    )
```

### Vision System Monitoring Dashboard

Create a monitoring endpoint to view vision system health:

```python
# In backend/app/main.py
from fastapi import FastAPI
from backend.app.performance_monitor import get_performance_monitor
from backend.app.error_handler import error_handler

@app.get("/api/vision/health")
async def vision_health():
    """Get vision system health metrics."""
    monitor = get_performance_monitor()
    stats = monitor.get_performance_stats()
    error_stats = error_handler.get_error_statistics()
    
    return {
        "status": "healthy" if stats['vision_metrics']['success_rate'] > 95 else "degraded",
        "performance": stats,
        "errors": error_stats,
        "recommendations": _generate_recommendations(stats, error_stats)
    }

def _generate_recommendations(stats, error_stats):
    """Generate recommendations based on metrics."""
    recommendations = []
    
    if stats['vision_metrics']['avg_response_time'] > 2.0:
        recommendations.append("Consider optimizing frame size or caching")
    
    if stats['cache_metrics']['hit_rate'] < 70:
        recommendations.append("Increase cache TTL to improve hit rate")
    
    if error_stats['error_rate'] > 1.0:
        recommendations.append("High error rate detected - check API status")
    
    return recommendations
```

### Troubleshooting Checklist

When debugging vision system issues, follow this checklist:

- [ ] **API Key**: Verify `GOOGLE_API_KEY` is set and valid
- [ ] **Network**: Check network connectivity to googleapis.com
- [ ] **Frame Quality**: Validate frame data is valid JPEG/PNG
- [ ] **Frame Size**: Ensure frame size is within API limits (< 4MB)
- [ ] **Rate Limits**: Check if hitting API rate limits
- [ ] **System Instruction**: Review system instruction for conflicts
- [ ] **Logging**: Enable DEBUG logging for detailed output
- [ ] **Performance**: Check response times and success rates
- [ ] **Cache**: Verify cache is working and hit rate is > 70%
- [ ] **Error Patterns**: Review error statistics for patterns

## Performance Monitoring

### Setting Up Performance Monitoring

#### 1. Initialize Performance Monitor

```python
# In backend/app/main.py
from backend.app.performance_monitor import get_performance_monitor

# Initialize on startup
@app.on_event("startup")
async def startup_event():
    monitor = get_performance_monitor()
    logger.info("Performance monitor initialized")
```

#### 2. Monitor Vision API Calls

```python
from backend.app.performance_monitor import get_performance_monitor

async def analyze_screen(frame_data: str, focus: str = "full"):
    """Analyze screen with performance monitoring."""
    monitor = get_performance_monitor()
    
    # Wrap vision API call with monitoring
    result = await monitor.monitor_vision_call(
        vision_api.analyze,
        frame_data,
        focus=focus
    )
    
    return result
```

#### 3. Monitor Action Execution

```python
async def execute_action(action: dict):
    """Execute action with performance monitoring."""
    monitor = get_performance_monitor()
    
    try:
        result = await action_executor.execute(action)
        monitor.record_action_result(success=True)
        return result
    except Exception as e:
        monitor.record_action_result(success=False)
        raise
```

#### 4. Monitor Cache Operations

```python
from backend.app.performance_monitor import get_performance_monitor

class VisionCache:
    def __init__(self):
        self.cache = {}
        self.monitor = get_performance_monitor()
    
    def get(self, key: str):
        if key in self.cache:
            self.monitor.record_cache_hit()
            return self.cache[key]
        else:
            self.monitor.record_cache_miss()
            return None
    
    def set(self, key: str, value: any):
        self.cache[key] = value
```

### Performance Metrics Endpoints

#### Health Check Endpoint

```python
@app.get("/api/health")
async def health_check():
    """Comprehensive health check with performance metrics."""
    monitor = get_performance_monitor()
    stats = monitor.get_performance_stats()
    
    # Determine overall health status
    is_healthy = (
        stats['vision_metrics']['success_rate'] > 95 and
        stats['vision_metrics']['avg_response_time'] < 2.0 and
        stats['cache_metrics']['hit_rate'] > 70
    )
    
    return {
        "status": "healthy" if is_healthy else "degraded",
        "timestamp": time.time(),
        "metrics": stats,
        "thresholds": {
            "vision_response_time": "< 2.0s",
            "vision_success_rate": "> 95%",
            "cache_hit_rate": "> 70%"
        }
    }
```

#### Performance Dashboard Endpoint

```python
@app.get("/api/performance/dashboard")
async def performance_dashboard():
    """Get performance dashboard data."""
    monitor = get_performance_monitor()
    stats = monitor.get_performance_stats()
    error_stats = error_handler.get_error_statistics()
    
    return {
        "vision": {
            "avg_response_time": stats['vision_metrics']['avg_response_time'],
            "p95_response_time": stats['vision_metrics']['p95_response_time'],
            "success_rate": stats['vision_metrics']['success_rate'],
            "total_calls": stats['vision_metrics']['total_calls'],
            "slow_responses": stats['vision_metrics']['slow_responses']
        },
        "actions": {
            "total": stats['action_metrics']['total_actions'],
            "success_rate": stats['action_metrics']['success_rate']
        },
        "cache": {
            "hit_rate": stats['cache_metrics']['hit_rate'],
            "total_operations": stats['cache_metrics']['total_operations']
        },
        "errors": {
            "total": error_stats['total_errors'],
            "rate": error_stats['error_rate'],
            "by_category": error_stats['categories']
        },
        "alerts": stats['alerts']
    }
```

### Performance Alerts

#### Configure Alert Thresholds

```python
# In backend/app/config.py
PERFORMANCE_THRESHOLDS = {
    "vision_response_time": 2.0,      # seconds
    "vision_success_rate": 95.0,      # percentage
    "cache_hit_rate": 70.0,           # percentage
    "slow_response_threshold": 3.0,   # seconds
    "error_rate": 1.0                 # errors per minute
}
```

#### Alert Notification System

```python
from backend.app.performance_monitor import get_performance_monitor

async def check_performance_alerts():
    """Check for performance alerts and notify if needed."""
    monitor = get_performance_monitor()
    stats = monitor.get_performance_stats()
    
    alerts = stats['alerts']
    
    if alerts:
        # Log alerts
        for alert in alerts:
            logger.warning(f"Performance Alert [{alert['severity']}]: {alert['message']}")
        
        # Send notifications (email, Slack, etc.)
        await send_alert_notifications(alerts)
    
    return alerts

# Run periodic alert checks
@app.on_event("startup")
async def start_alert_monitoring():
    async def alert_loop():
        while True:
            await check_performance_alerts()
            await asyncio.sleep(60)  # Check every minute
    
    asyncio.create_task(alert_loop())
```

### Performance Optimization Tips

#### 1. Optimize Frame Size

```python
from PIL import Image
import io
import base64

def optimize_frame(frame_data: str, max_size: int = 1024) -> str:
    """Optimize frame size while maintaining quality."""
    # Decode base64
    frame_bytes = base64.b64decode(frame_data)
    
    # Open image
    img = Image.open(io.BytesIO(frame_bytes))
    
    # Resize if too large
    if max(img.size) > max_size:
        ratio = max_size / max(img.size)
        new_size = tuple(int(dim * ratio) for dim in img.size)
        img = img.resize(new_size, Image.LANCZOS)
    
    # Compress as JPEG
    output = io.BytesIO()
    img.save(output, format='JPEG', quality=85, optimize=True)
    
    # Encode back to base64
    return base64.b64encode(output.getvalue()).decode('utf-8')
```

#### 2. Implement Intelligent Caching

```python
import hashlib
import time
from typing import Optional, Tuple

class IntelligentVisionCache:
    def __init__(self, ttl: int = 30, max_size: int = 100):
        self.cache = {}
        self.ttl = ttl
        self.max_size = max_size
        self.monitor = get_performance_monitor()
    
    def _compute_hash(self, frame_data: str) -> str:
        """Compute hash of frame data."""
        return hashlib.md5(frame_data.encode()).hexdigest()
    
    def get(self, frame_data: str) -> Optional[str]:
        """Get cached result if available and not expired."""
        key = self._compute_hash(frame_data)
        
        if key in self.cache:
            result, timestamp = self.cache[key]
            
            # Check if expired
            if time.time() - timestamp < self.ttl:
                self.monitor.record_cache_hit()
                return result
            else:
                # Remove expired entry
                del self.cache[key]
        
        self.monitor.record_cache_miss()
        return None
    
    def set(self, frame_data: str, result: str):
        """Cache result with timestamp."""
        key = self._compute_hash(frame_data)
        
        # Implement LRU eviction if cache is full
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][1])
            del self.cache[oldest_key]
        
        self.cache[key] = (result, time.time())
```

#### 3. Batch API Requests

```python
async def batch_vision_analysis(frames: List[str]) -> List[str]:
    """Batch multiple vision analysis requests."""
    monitor = get_performance_monitor()
    
    # Process frames in parallel with rate limiting
    semaphore = asyncio.Semaphore(5)  # Max 5 concurrent requests
    
    async def analyze_with_semaphore(frame):
        async with semaphore:
            return await monitor.monitor_vision_call(
                vision_api.analyze,
                frame
            )
    
    results = await asyncio.gather(*[
        analyze_with_semaphore(frame) for frame in frames
    ])
    
    return results
```

### Performance Monitoring Best Practices

1. **Monitor Continuously**: Set up continuous monitoring with alerts
2. **Track Trends**: Monitor metrics over time to identify degradation
3. **Set Realistic Thresholds**: Base thresholds on actual usage patterns
4. **Optimize Proactively**: Address performance issues before they impact users
5. **Cache Aggressively**: Use caching to reduce API calls and improve response times
6. **Log Comprehensively**: Enable detailed logging for debugging
7. **Test Under Load**: Regularly test system under realistic load conditions
8. **Review Regularly**: Review performance metrics and alerts weekly



## Development Workflow

### Setting Up Development Environment

#### 1. Clone Repository

```bash
git clone <repository-url>
cd spectra
```

#### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env

# Add your API keys
echo "GOOGLE_API_KEY=your_api_key_here" >> .env
```

#### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Create .env file
cp .env.example .env
```

#### 4. Browser Extension Setup

```bash
cd extension

# Load extension in Chrome
# 1. Open chrome://extensions/
# 2. Enable "Developer mode"
# 3. Click "Load unpacked"
# 4. Select the extension directory
```

### Running the Development Server

#### Start Backend

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Start Frontend

```bash
cd frontend
npm run dev
```

#### Access Application

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Code Style and Linting

#### Python (Backend)

```bash
# Install development dependencies
pip install black flake8 mypy pytest

# Format code
black backend/app

# Lint code
flake8 backend/app

# Type checking
mypy backend/app
```

#### TypeScript (Frontend)

```bash
# Lint code
npm run lint

# Format code
npm run format

# Type checking
npm run type-check
```

### Git Workflow

#### Branch Naming Convention

- Feature: `feature/description`
- Bugfix: `bugfix/description`
- Hotfix: `hotfix/description`
- Enhancement: `enhancement/description`

#### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Example**:
```
feat(vision): Add intelligent caching for vision API

Implement LRU cache with adaptive TTL to reduce API calls
and improve response times. Cache hit rate improved from
45% to 78%.

Closes #123
```

### Adding New Features

#### 1. Create Feature Branch

```bash
git checkout -b feature/new-feature
```

#### 2. Implement Feature

Follow the component structure:

```
backend/app/
├── new_feature.py          # Main implementation
├── tests/
│   └── test_new_feature.py # Unit tests
└── docs/
    └── NEW_FEATURE.md      # Documentation
```

#### 3. Write Tests

```python
# backend/tests/test_new_feature.py
import pytest
from backend.app.new_feature import NewFeature

def test_new_feature_basic():
    """Test basic functionality."""
    feature = NewFeature()
    result = feature.process("input")
    assert result == "expected_output"

@pytest.mark.asyncio
async def test_new_feature_async():
    """Test async functionality."""
    feature = NewFeature()
    result = await feature.process_async("input")
    assert result is not None
```

#### 4. Update Documentation

Add API documentation to this guide and create feature-specific docs if needed.

#### 5. Submit Pull Request

```bash
git add .
git commit -m "feat(scope): description"
git push origin feature/new-feature
```

Create PR with:
- Clear description of changes
- Link to related issues
- Test results
- Screenshots/demos if applicable

## Testing

### Unit Tests

#### Running Unit Tests

```bash
# Backend tests
cd backend
pytest

# With coverage
pytest --cov=app --cov-report=html

# Specific test file
pytest tests/test_performance_monitor.py

# Specific test
pytest tests/test_performance_monitor.py::test_monitor_vision_call
```

#### Writing Unit Tests

```python
# backend/tests/test_example.py
import pytest
from backend.app.example import ExampleClass

@pytest.fixture
def example_instance():
    """Fixture for ExampleClass instance."""
    return ExampleClass()

def test_basic_functionality(example_instance):
    """Test basic functionality."""
    result = example_instance.method("input")
    assert result == "expected"

@pytest.mark.asyncio
async def test_async_functionality(example_instance):
    """Test async functionality."""
    result = await example_instance.async_method("input")
    assert result is not None

def test_error_handling(example_instance):
    """Test error handling."""
    with pytest.raises(ValueError):
        example_instance.method(None)
```

### Integration Tests

#### Running Integration Tests

```bash
# Backend integration tests
cd backend
pytest tests/integration/

# Frontend integration tests
cd frontend
npm run test:integration
```

#### Writing Integration Tests

```python
# backend/tests/integration/test_vision_pipeline.py
import pytest
from backend.app.performance_monitor import get_performance_monitor
from backend.app.error_handler import error_handler

@pytest.mark.integration
@pytest.mark.asyncio
async def test_vision_pipeline_end_to_end():
    """Test complete vision analysis pipeline."""
    monitor = get_performance_monitor()
    
    # Load test frame
    frame_data = load_test_frame()
    
    # Analyze with monitoring
    result = await monitor.monitor_vision_call(
        vision_api.analyze,
        frame_data
    )
    
    # Verify result
    assert result is not None
    assert not error_handler.is_deflection_response(result)
    
    # Check performance
    stats = monitor.get_performance_stats()
    assert stats['vision_metrics']['avg_response_time'] < 3.0
```

### Property-Based Tests

#### Running Property-Based Tests

```bash
cd backend
pytest tests/property/ --hypothesis-show-statistics
```

#### Writing Property-Based Tests

```python
# backend/tests/property/test_voice_commands.py
from hypothesis import given, strategies as st
from backend.app.voice_command_processor import VoiceCommandProcessor

processor = VoiceCommandProcessor()

@given(st.text(min_size=1, max_size=100))
def test_parse_command_never_crashes(text):
    """Property: parse_command should never crash on any input."""
    try:
        result = processor.parse_command(text)
        assert result is not None
        assert hasattr(result, 'action')
    except Exception as e:
        pytest.fail(f"parse_command crashed with: {e}")

@given(
    st.sampled_from(['click', 'press', 'tap', 'select']),
    st.text(min_size=1, max_size=50)
)
def test_click_command_variations(action_word, target):
    """Property: All click variations should be recognized."""
    command = f"{action_word} the {target}"
    result = processor.parse_command(command)
    assert result.action.value == 'click'
    assert target in result.target
```

### Accessibility Tests

#### Screen Reader Testing

```bash
# Install screen reader testing tools
npm install --save-dev @testing-library/react
npm install --save-dev jest-axe

# Run accessibility tests
npm run test:a11y
```

#### Writing Accessibility Tests

```typescript
// frontend/tests/accessibility.test.ts
import { render } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import App from '../src/App';

expect.extend(toHaveNoViolations);

describe('Accessibility', () => {
  it('should have no accessibility violations', async () => {
    const { container } = render(<App />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('should support keyboard navigation', () => {
    const { getByRole } = render(<App />);
    const button = getByRole('button', { name: /start/i });
    
    button.focus();
    expect(document.activeElement).toBe(button);
  });
});
```

### Test Coverage

#### Generate Coverage Reports

```bash
# Backend coverage
cd backend
pytest --cov=app --cov-report=html --cov-report=term

# Frontend coverage
cd frontend
npm run test:coverage
```

#### Coverage Targets

- Overall coverage: > 80%
- Core components: > 90%
- Critical paths: 100%

## Deployment

### Production Deployment

#### 1. Build Frontend

```bash
cd frontend
npm run build

# Output will be in frontend/dist/
```

#### 2. Prepare Backend

```bash
cd backend

# Install production dependencies
pip install -r requirements.txt

# Set production environment variables
export ENVIRONMENT=production
export GOOGLE_API_KEY=your_production_key
```

#### 3. Deploy with Docker

```bash
# Build Docker images
docker-compose build

# Start services
docker-compose up -d

# Check status
docker-compose ps
```

#### 4. Deploy to Cloud (AWS Example)

```bash
# Using Terraform
cd infra
terraform init
terraform plan
terraform apply

# Or using deployment script
./infra/deploy.sh production
```

### Environment Configuration

#### Development

```bash
# backend/.env
ENVIRONMENT=development
GOOGLE_API_KEY=dev_api_key
LOG_LEVEL=DEBUG
CORS_ORIGINS=http://localhost:5173
```

#### Staging

```bash
# backend/.env
ENVIRONMENT=staging
GOOGLE_API_KEY=staging_api_key
LOG_LEVEL=INFO
CORS_ORIGINS=https://staging.spectra.app
```

#### Production

```bash
# backend/.env
ENVIRONMENT=production
GOOGLE_API_KEY=prod_api_key
LOG_LEVEL=WARNING
CORS_ORIGINS=https://spectra.app
SENTRY_DSN=your_sentry_dsn
```

### Monitoring and Logging

#### Application Monitoring

```python
# Configure Sentry for error tracking
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    integrations=[FastApiIntegration()],
    environment=os.getenv("ENVIRONMENT"),
    traces_sample_rate=0.1
)
```

#### Performance Monitoring

```python
# Add performance monitoring endpoint
@app.get("/api/metrics")
async def metrics():
    """Prometheus-compatible metrics endpoint."""
    monitor = get_performance_monitor()
    stats = monitor.get_performance_stats()
    
    return {
        "vision_response_time_seconds": stats['vision_metrics']['avg_response_time'],
        "vision_success_rate": stats['vision_metrics']['success_rate'] / 100,
        "cache_hit_rate": stats['cache_metrics']['hit_rate'] / 100,
        "total_vision_calls": stats['vision_metrics']['total_calls']
    }
```

#### Log Aggregation

```python
# Configure structured logging
import logging
import json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName
        }
        return json.dumps(log_data)

# Apply formatter
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logging.root.addHandler(handler)
```

### Health Checks

#### Kubernetes Health Probes

```yaml
# kubernetes/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: spectra-backend
spec:
  template:
    spec:
      containers:
      - name: backend
        image: spectra-backend:latest
        livenessProbe:
          httpGet:
            path: /api/health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

#### Health Check Endpoint

```python
@app.get("/api/health")
async def health_check():
    """Comprehensive health check."""
    monitor = get_performance_monitor()
    stats = monitor.get_performance_stats()
    
    # Check critical components
    checks = {
        "api": "healthy",
        "vision_system": "healthy" if stats['vision_metrics']['success_rate'] > 95 else "degraded",
        "cache": "healthy" if stats['cache_metrics']['hit_rate'] > 70 else "degraded",
        "database": await check_database_health()
    }
    
    overall_status = "healthy" if all(v == "healthy" for v in checks.values()) else "degraded"
    
    return {
        "status": overall_status,
        "timestamp": time.time(),
        "checks": checks,
        "version": os.getenv("APP_VERSION", "unknown")
    }
```

### Rollback Procedures

#### Quick Rollback

```bash
# Using Docker Compose
docker-compose down
docker-compose up -d --scale backend=0
docker-compose up -d --scale backend=1

# Using Kubernetes
kubectl rollout undo deployment/spectra-backend

# Using Terraform
terraform apply -var="app_version=previous_version"
```

#### Database Rollback

```bash
# Run database migration rollback
cd backend
alembic downgrade -1

# Or restore from backup
./scripts/restore_database.sh backup_timestamp
```

### Backup and Recovery

#### Database Backups

```bash
# Automated daily backups
0 2 * * * /usr/local/bin/backup_database.sh

# Manual backup
./scripts/backup_database.sh
```

#### Configuration Backups

```bash
# Backup environment configuration
tar -czf config_backup_$(date +%Y%m%d).tar.gz backend/.env frontend/.env

# Backup to S3
aws s3 cp config_backup_*.tar.gz s3://spectra-backups/config/
```

## Additional Resources

### Documentation

- [Accessibility Quick Start](./ACCESSIBILITY_QUICK_START.md)
- [Voice Commands Reference](./VOICE_COMMANDS_REFERENCE.md)
- [Troubleshooting Guide](./TROUBLESHOOTING.md)
- [API Documentation](http://localhost:8000/docs)

### External Resources

- [Gemini API Documentation](https://ai.google.dev/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)

### Community

- GitHub Issues: Report bugs and request features
- Discussions: Ask questions and share ideas
- Contributing: See CONTRIBUTING.md for guidelines

### Support

For technical support or questions:
- Email: support@spectra.app
- Documentation: https://docs.spectra.app
- Community Forum: https://community.spectra.app

---

**Last Updated**: 2024
**Version**: 1.0.0
**Maintainers**: Spectra Development Team
