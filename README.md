# Claude Code API Gateway

API gateway for Claude Code CLI with SSE streaming, parallel requests support, and full JSON output proxying.

## Features

- SSE streaming raw JSON without modifications
- Multiple parallel requests support
- Session management (new/continue via session_id)
- Request cancellation
- **Permission restrictions** — limit tools and commands
- Support for all Claude Code CLI parameters
- MCP servers support
- Basic Auth authentication
- Auto-detection of Claude Code path
- Systemd autostart

## Quick Start

**One-line installation** (works on clean Ubuntu/Debian/CentOS/Fedora):

```bash
curl -fsSL https://raw.githubusercontent.com/eduard256/claudecode2api/main/install.sh | bash
```

This will:
- Update system and install all dependencies
- Install Claude Code CLI automatically
- Clone the repository to `~/claudecode2api`
- Set up Python virtual environment
- Configure credentials interactively
- Install and start systemd service
- Set up auto-start on boot

**To update an existing installation:**

```bash
curl -fsSL https://raw.githubusercontent.com/eduard256/claudecode2api/main/install.sh | bash
```

The script automatically detects and updates existing installations.

## Configuration

Copy `.env.example` to `.env` and configure:

```env
# Server
HOST=0.0.0.0
PORT=9876

# Authentication (REQUIRED)
AUTH_USER=admin
AUTH_PASSWORD=your-secure-password

# Claude Code (auto-detected if not set)
# CLAUDE_PATH=/home/user/.local/bin/claude

# Logging
LOG_LEVEL=DEBUG
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check (no auth) |
| POST | `/chat` | Start Claude Code with SSE streaming |
| DELETE | `/chat/{process_id}` | Cancel running request |
| GET | `/processes` | List active processes |

### POST /chat

Start Claude Code session with SSE streaming.

```bash
curl -X POST http://localhost:9876/chat \
  -u admin:password \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Create hello.txt with Hello World",
    "cwd": "/home/user/projects/myapp"
  }'
```

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `prompt` | string | Yes | User prompt |
| `cwd` | string | Yes | Working directory |
| `model` | string | No | Model (sonnet, opus, haiku) |
| `session_id` | string | No | Session ID to continue |
| `system_prompt` | string | No | Replace system prompt |
| `append_system_prompt` | string | No | Append to system prompt |
| `tools` | string[] | No | Whitelist of visible tools |
| `allowed_tools` | string[] | No | Auto-approved tool patterns |
| `disallowed_tools` | string[] | No | Blocked tools |
| `mcp_config` | string[] | No | MCP server configs |

**Response:** SSE Stream

```
event: message
data: {"type":"system","subtype":"init","session_id":"uuid",...}

event: message
data: {"type":"assistant","message":{"content":[{"type":"text","text":"..."}]}}

event: message
data: {"type":"result","subtype":"success","result":"...","total_cost_usd":0.01}

event: done
data: {"process_id":"uuid"}
```

## Permission Modes

### Full Access (default)

Without `tools` or `allowed_tools`, runs with full permissions:

```json
{
  "prompt": "Run any command",
  "cwd": "/project"
}
```

### Restricted Mode

With `tools` or `allowed_tools`, runs in restricted mode:

```json
{
  "prompt": "Check git status",
  "cwd": "/project",
  "tools": ["Bash"],
  "allowed_tools": ["Bash(git:*)"]
}
```

This allows only `git` commands. Other commands like `rm`, `curl` will be blocked.

**Examples:**

```json
// Only git commands
{"tools": ["Bash"], "allowed_tools": ["Bash(git:*)"]}

// Only specific script
{"tools": ["Bash"], "allowed_tools": ["Bash(/path/to/script.py:*)"]}

// Read-only (no Bash)
{"tools": ["Read", "Glob", "Grep"], "allowed_tools": ["Read", "Glob", "Grep"]}

// Only MCP tools
{"tools": [], "allowed_tools": ["mcp__wildberries__wb_search"]}
```

See [PERMISSIONS.md](PERMISSIONS.md) for detailed documentation.

## Session Management

1. First request returns `session_id` in `type: system` message
2. Pass `session_id` to continue conversation:

```json
{
  "prompt": "What files did you create?",
  "cwd": "/project",
  "session_id": "previous-session-id"
}
```

## Usage Examples

### Python

```python
import requests
import json

url = "http://localhost:9876/chat"
auth = ("admin", "password")

response = requests.post(
    url,
    auth=auth,
    json={
        "prompt": "List files in current directory",
        "cwd": "/home/user/projects"
    },
    stream=True
)

for line in response.iter_lines():
    if line:
        line = line.decode("utf-8")
        if line.startswith("data: "):
            data = json.loads(line[6:])
            print(data)
```

### JavaScript

```javascript
const response = await fetch("http://localhost:9876/chat", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "Authorization": "Basic " + btoa("admin:password")
  },
  body: JSON.stringify({
    prompt: "List files",
    cwd: "/home/user/projects"
  })
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  const lines = decoder.decode(value).split("\n");
  for (const line of lines) {
    if (line.startsWith("data: ")) {
      const data = JSON.parse(line.slice(6));
      console.log(data);
    }
  }
}
```

### cURL

```bash
curl -N -X POST http://localhost:9876/chat \
  -u admin:password \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello", "cwd": "/tmp"}'
```

## Systemd

```bash
# Status
sudo systemctl status claudecode2api

# Start/Stop/Restart
sudo systemctl start claudecode2api
sudo systemctl stop claudecode2api
sudo systemctl restart claudecode2api

# Logs
sudo journalctl -u claudecode2api -f
```

## Development

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run in development mode
uvicorn app.main:app --reload --host 0.0.0.0 --port 9876
```

## Documentation

- [API.md](API.md) — Full API reference with examples
- [PERMISSIONS.md](PERMISSIONS.md) — Tool and command restrictions guide
- Swagger UI: http://localhost:9876/docs
- ReDoc: http://localhost:9876/redoc

## License

MIT
