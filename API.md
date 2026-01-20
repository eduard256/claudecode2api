# Claude Code API Gateway

HTTP API for Claude Code CLI with SSE streaming.

## Authentication

All endpoints require Basic Auth:
```
Authorization: Basic base64(user:password)
```

---

## Endpoints

### POST /chat

Start Claude Code session with SSE streaming.

**Request:**
```json
{
  "prompt": "string (required)",
  "cwd": "string (required)",
  "model": "string (default: sonnet)",
  "session_id": "string (optional, to continue session)",
  "system_prompt": "string (optional)",
  "tools": ["string"] (optional),
  "allowed_tools": ["string"] (optional),
  "mcp_config": ["string"] (optional)
}
```

**Response:** SSE stream with `event: message` and `event: done`

---

### DELETE /chat/{process_id}

Cancel running request.

**Response:**
```json
{"status": "cancelled", "process_id": "uuid"}
```

---

### GET /processes

List active processes.

**Response:**
```json
{
  "processes": [
    {
      "process_id": "uuid",
      "cwd": "/path",
      "model": "sonnet",
      "started_at": "2026-01-20T13:08:15.973884",
      "session_id": "uuid"
    }
  ],
  "count": 1
}
```

---

### GET /health

Health check (no auth required).

**Response:**
```json
{
  "status": "ok",
  "claude_path": "/home/user/.local/bin/claude",
  "claude_version": "2.0.65 (Claude Code)"
}
```

---

## SSE Event Types

### 1. system (init)

First event with session info.

```
event: message
data: {"type":"system","subtype":"init","cwd":"/home/user/project","session_id":"e4afa2a6-1d3b-4693-b576-a89b12f0324e","tools":["Task","TaskOutput","Bash","Glob","Grep","Read","Edit","Write","NotebookEdit","WebFetch","TodoWrite","WebSearch","KillShell","EnterPlanMode","ExitPlanMode"],"mcp_servers":[],"model":"claude-sonnet-4-5-20250929","permissionMode":"bypassPermissions"}
```

### 2. assistant (text)

AI text response.

```
event: message
data: {"type":"assistant","message":{"model":"claude-sonnet-4-5-20250929","id":"msg_01VTX1AxBM8XAVuBt3jFkpJt","type":"message","role":"assistant","content":[{"type":"text","text":"I'll help you with that."}],"stop_reason":null,"usage":{"input_tokens":3,"output_tokens":8}},"session_id":"e4afa2a6-1d3b-4693-b576-a89b12f0324e"}
```

### 3. assistant (tool_use)

AI requests tool execution.

```
event: message
data: {"type":"assistant","message":{"model":"claude-sonnet-4-5-20250929","id":"msg_01VTX1AxBM8XAVuBt3jFkpJt","type":"message","role":"assistant","content":[{"type":"tool_use","id":"toolu_01AuvtW27uNVuyJ6zBwta4Q4","name":"Bash","input":{"command":"git status","description":"Show git status"}}],"stop_reason":null,"usage":{"input_tokens":3,"output_tokens":12}},"session_id":"e4afa2a6-1d3b-4693-b576-a89b12f0324e"}
```

### 4. user (tool_result)

Tool execution result.

```
event: message
data: {"type":"user","message":{"role":"user","content":[{"tool_use_id":"toolu_01AuvtW27uNVuyJ6zBwta4Q4","type":"tool_result","content":"On branch main\nYour branch is up to date.","is_error":false}]},"session_id":"e4afa2a6-1d3b-4693-b576-a89b12f0324e","tool_use_result":{"stdout":"On branch main\nYour branch is up to date.","stderr":"","interrupted":false,"isImage":false}}
```

### 5. result

Final result with usage and cost.

```
event: message
data: {"type":"result","subtype":"success","is_error":false,"duration_ms":10603,"duration_api_ms":21863,"num_turns":4,"result":"Task completed successfully.","session_id":"e4afa2a6-1d3b-4693-b576-a89b12f0324e","total_cost_usd":0.045239,"usage":{"input_tokens":168,"cache_creation_input_tokens":3883,"cache_read_input_tokens":31251,"output_tokens":452},"permission_denials":[]}
```

### 6. done

Stream end with process_id.

```
event: done
data: {"process_id": "71164038-07c1-4e66-b935-85d053abd0b2"}
```

---

## Tool Results Format

### Bash

```json
{
  "tool_use_result": {
    "stdout": "command output",
    "stderr": "",
    "interrupted": false,
    "isImage": false
  }
}
```

**Permission denied:**
```json
{
  "tool_use_result": "Error: Permission to use Bash has been auto-denied in dontAsk mode."
}
```

### Read

```json
{
  "tool_use_result": {
    "type": "text",
    "file": {
      "filePath": "/path/to/file.txt",
      "content": "file content here",
      "numLines": 10,
      "startLine": 1,
      "totalLines": 10
    }
  }
}
```

### Write

```json
{
  "tool_use_result": {
    "type": "create",
    "filePath": "/tmp/newfile.txt",
    "content": "Hello API",
    "structuredPatch": [],
    "originalFile": null
  }
}
```

### Edit

```json
{
  "tool_use_result": {
    "filePath": "/tmp/file.txt",
    "oldString": "Hello",
    "newString": "Goodbye",
    "originalFile": "Hello API",
    "structuredPatch": [
      {
        "oldStart": 1,
        "oldLines": 1,
        "newStart": 1,
        "newLines": 1,
        "lines": ["-Hello API", "+Goodbye API"]
      }
    ],
    "replaceAll": false
  }
}
```

### Glob

```json
{
  "tool_use_result": {
    "filenames": [
      "/project/app/__init__.py",
      "/project/app/main.py",
      "/project/app/config.py"
    ],
    "durationMs": 390,
    "numFiles": 11,
    "truncated": false
  }
}
```

### Grep

```json
{
  "tool_use_result": {
    "mode": "content",
    "content": "15:def build_command(request):\n112:async def run_claude(request):",
    "numLines": 2,
    "numFiles": 0,
    "filenames": []
  }
}
```

---

## Permission Modes

### Full Access (default)

If `tools` and `allowed_tools` are not specified, runs with `--dangerously-skip-permissions`:

```json
{
  "prompt": "Run any command",
  "cwd": "/project"
}
```

Response shows `"permissionMode":"bypassPermissions"` and all tools available.

### Restricted Mode

If `tools` OR `allowed_tools` specified, runs WITHOUT `--dangerously-skip-permissions`:

```json
{
  "prompt": "Run git status",
  "cwd": "/project",
  "tools": ["Bash"],
  "allowed_tools": ["Bash(git:*)"]
}
```

Response shows `"permissionMode":"dontAsk"` and only specified tools.

**Blocked command example:**
```
event: message
data: {"type":"user","message":{"role":"user","content":[{"type":"tool_result","content":"Permission to use Bash has been auto-denied in dontAsk mode.","is_error":true,"tool_use_id":"toolu_01PM2LZvqqA6mXGvbcwn3pG2"}]},"tool_use_result":"Error: Permission to use Bash has been auto-denied in dontAsk mode."}
```

---

## Session Management

### Create Session

First request creates new session:

```bash
curl -X POST http://localhost:9876/chat \
  -u 'user:pass' \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Remember: SECRET=abc123", "cwd": "/tmp"}'
```

Get `session_id` from response: `"session_id":"f6105324-228c-4b36-8b77-511cf03cd04f"`

### Continue Session

Use `session_id` to continue conversation:

```bash
curl -X POST http://localhost:9876/chat \
  -u 'user:pass' \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "What SECRET did I tell you?",
    "cwd": "/tmp",
    "session_id": "f6105324-228c-4b36-8b77-511cf03cd04f"
  }'
```

Response: `"result":"You told me: SECRET=abc123"`

---

## Complete Examples

### Example 1: Simple Command

**Request:**
```bash
curl -X POST http://localhost:9876/chat \
  -u 'admin:password' \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Run: echo hello", "cwd": "/tmp"}'
```

**Response:**
```
event: message
data: {"type":"system","subtype":"init","cwd":"/tmp","session_id":"04645110-dd58-4e1a-8e76-ac8e17739a4c","tools":["Task","TaskOutput","Bash","Glob","Grep","Read","Edit","Write","NotebookEdit","WebFetch","TodoWrite","WebSearch","KillShell","EnterPlanMode","ExitPlanMode"],"mcp_servers":[],"model":"claude-sonnet-4-5-20250929","permissionMode":"bypassPermissions"}

event: message
data: {"type":"assistant","message":{"model":"claude-sonnet-4-5-20250929","id":"msg_01Rx1ZQc7MZsMDGAhQaSEUKq","type":"message","role":"assistant","content":[{"type":"tool_use","id":"toolu_01Xu7ZYsfXmec8mTHoraaKa2","name":"Bash","input":{"command":"echo hello","description":"Echo hello"}}],"usage":{"input_tokens":2,"output_tokens":8}},"session_id":"04645110-dd58-4e1a-8e76-ac8e17739a4c"}

event: message
data: {"type":"user","message":{"role":"user","content":[{"tool_use_id":"toolu_01Xu7ZYsfXmec8mTHoraaKa2","type":"tool_result","content":"hello","is_error":false}]},"session_id":"04645110-dd58-4e1a-8e76-ac8e17739a4c","tool_use_result":{"stdout":"hello","stderr":"","interrupted":false,"isImage":false}}

event: message
data: {"type":"assistant","message":{"model":"claude-sonnet-4-5-20250929","id":"msg_01ELVZtuma8KVymGTaySmQHC","type":"message","role":"assistant","content":[{"type":"text","text":"Done. Output: hello"}],"usage":{"input_tokens":5,"output_tokens":6}},"session_id":"04645110-dd58-4e1a-8e76-ac8e17739a4c"}

event: message
data: {"type":"result","subtype":"success","is_error":false,"duration_ms":4392,"num_turns":2,"result":"Done. Output: hello","session_id":"04645110-dd58-4e1a-8e76-ac8e17739a4c","total_cost_usd":0.0151475,"usage":{"input_tokens":7,"output_tokens":107},"permission_denials":[]}

event: done
data: {"process_id": "f8f32cfd-e0df-44bd-9259-f1ead31cc54e"}
```

### Example 2: Restricted Mode (git only)

**Request:**
```bash
curl -X POST http://localhost:9876/chat \
  -u 'admin:password' \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Run: 1) git status 2) rm /tmp/file",
    "cwd": "/project",
    "tools": ["Bash"],
    "allowed_tools": ["Bash(git:*)"]
  }'
```

**Response:**
```
event: message
data: {"type":"system","subtype":"init","cwd":"/project","session_id":"5f98ac25-442f-43c4-a5e3-2ac2ed07f1a3","tools":["Bash"],"mcp_servers":[],"model":"claude-sonnet-4-5-20250929","permissionMode":"dontAsk"}

event: message
data: {"type":"assistant","message":{"content":[{"type":"tool_use","id":"toolu_01QXXwSZtzdsoMfU4UJs2nuf","name":"Bash","input":{"command":"git status"}}]},"session_id":"5f98ac25-442f-43c4-a5e3-2ac2ed07f1a3"}

event: message
data: {"type":"user","message":{"content":[{"tool_use_id":"toolu_01QXXwSZtzdsoMfU4UJs2nuf","type":"tool_result","content":"On branch main\nYour branch is up to date.","is_error":false}]},"tool_use_result":{"stdout":"On branch main\nYour branch is up to date.","stderr":"","interrupted":false,"isImage":false}}

event: message
data: {"type":"assistant","message":{"content":[{"type":"tool_use","id":"toolu_01PM2LZvqqA6mXGvbcwn3pG2","name":"Bash","input":{"command":"rm /tmp/file"}}]},"session_id":"5f98ac25-442f-43c4-a5e3-2ac2ed07f1a3"}

event: message
data: {"type":"user","message":{"content":[{"type":"tool_result","content":"Permission to use Bash has been auto-denied in dontAsk mode.","is_error":true,"tool_use_id":"toolu_01PM2LZvqqA6mXGvbcwn3pG2"}]},"tool_use_result":"Error: Permission to use Bash has been auto-denied in dontAsk mode."}

event: message
data: {"type":"result","subtype":"success","is_error":false,"result":"Git status: on branch main. The rm command was blocked by permissions.","session_id":"5f98ac25-442f-43c4-a5e3-2ac2ed07f1a3","permission_denials":[{"tool_name":"Bash","tool_use_id":"toolu_01PM2LZvqqA6mXGvbcwn3pG2","tool_input":{"command":"rm /tmp/file"}}]}

event: done
data: {"process_id": "b91c1a5e-6cab-42ab-93db-314400e030f3"}
```

### Example 3: MCP Tools Only

**Request:**
```bash
curl -X POST http://localhost:9876/chat \
  -u 'admin:password' \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Search for Nike sneakers",
    "cwd": "/home/user/shop",
    "tools": [],
    "allowed_tools": ["mcp__wildberries__wb_search"]
  }'
```

**Response:**
```
event: message
data: {"type":"system","subtype":"init","cwd":"/home/user/shop","session_id":"acf786a6-f316-41cb-ad19-7b49fcf1d1a9","tools":["mcp__wildberries__wb_search","mcp__wildberries__wb_product_details","mcp__ozon__ozon_search"],"mcp_servers":[{"name":"wildberries","status":"connected"},{"name":"ozon","status":"connected"}],"model":"claude-sonnet-4-5-20250929","permissionMode":"dontAsk"}

event: message
data: {"type":"assistant","message":{"content":[{"type":"tool_use","id":"toolu_01Kkr9HE4HbHPoZfEfWehybp","name":"mcp__wildberries__wb_search","input":{"query":"Nike sneakers","limit":20}}]},"session_id":"acf786a6-f316-41cb-ad19-7b49fcf1d1a9"}

event: message
data: {"type":"user","message":{"content":[{"tool_use_id":"toolu_01Kkr9HE4HbHPoZfEfWehybp","type":"tool_result","content":"[{\"id\":\"302387881\",\"name\":\"Nike Air Max\",\"price\":5931}]"}]},"session_id":"acf786a6-f316-41cb-ad19-7b49fcf1d1a9"}

event: message
data: {"type":"result","subtype":"success","result":"Found Nike sneakers: Air Max - 5931₽","session_id":"acf786a6-f316-41cb-ad19-7b49fcf1d1a9"}

event: done
data: {"process_id": "9cc62755-22b2-441a-ba16-576ea4583303"}
```

---

## Request Parameters Reference

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `prompt` | string | Yes | User message |
| `cwd` | string | Yes | Working directory |
| `model` | string | No | Model: `sonnet`, `opus`, `haiku` (default: `sonnet`) |
| `session_id` | string | No | Continue existing session |
| `system_prompt` | string | No | Replace default system prompt |
| `append_system_prompt` | string | No | Append to system prompt |
| `tools` | string[] | No | Whitelist of visible tools |
| `allowed_tools` | string[] | No | Patterns for auto-approved tools |
| `disallowed_tools` | string[] | No | Tools to completely block |
| `mcp_config` | string[] | No | MCP server configs |
| `permission_mode` | string | No | `default`, `acceptEdits`, `plan` |

---

## Available Tools

### Built-in Tools
- `Bash` — Execute shell commands
- `Read` — Read file contents
- `Write` — Create new files
- `Edit` — Edit existing files
- `Glob` — Find files by pattern
- `Grep` — Search file contents
- `WebFetch` — Fetch web pages
- `WebSearch` — Search the web
- `Task` — Spawn sub-agents
- `TodoWrite` — Manage task lists
- `NotebookEdit` — Edit Jupyter notebooks
- `EnterPlanMode` — Enter planning mode
- `ExitPlanMode` — Exit planning mode

### MCP Tools
Format: `mcp__<server>__<tool>`

Example: `mcp__wildberries__wb_search`

---

## Error Handling

### Invalid Credentials
```json
{"detail": "Invalid credentials"}
```

### Invalid Working Directory
```json
{"error": "Working directory does not exist: /invalid/path"}
```

### Process Not Found (cancel)
```json
{"error": "Process not found"}
```
