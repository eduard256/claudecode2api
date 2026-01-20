# Claude Code Permission Restrictions

Guide for restricting Claude Code tools and commands via API and CLI flags.

## API Usage

### Default Behavior (Full Access)

If `tools` and `allowed_tools` are not specified, Claude runs with `--dangerously-skip-permissions`:

```json
{
  "prompt": "Hello",
  "cwd": "/tmp"
}
```

### Restricted Mode

If `tools` OR `allowed_tools` are specified, Claude runs WITHOUT `--dangerously-skip-permissions`:

```json
{
  "prompt": "Search for sneakers",
  "cwd": "/home/user/shop",
  "tools": ["Bash", "mcp__wildberries__wb_search"],
  "allowed_tools": ["Bash(git:*)", "mcp__wildberries__wb_search"]
}
```

### API Fields

| Field | Description |
|-------|-------------|
| `tools` | Whitelist of available tools. Only these are visible to AI. |
| `allowed_tools` | Patterns for auto-approved commands (others blocked in `dontAsk` mode). |
| `disallowed_tools` | Tools completely removed from AI context. |

### Examples

**Only git commands:**
```json
{
  "prompt": "Check git status",
  "cwd": "/project",
  "tools": ["Bash"],
  "allowed_tools": ["Bash(git:*)"]
}
```

**Only specific script:**
```json
{
  "prompt": "Send telegram message 'Hello!'",
  "cwd": "/project",
  "tools": ["Bash"],
  "allowed_tools": ["Bash(/home/user/bot/venv/bin/python3 /home/user/bot/send.py:*)"]
}
```

**Only MCP tools:**
```json
{
  "prompt": "Search for Nike sneakers",
  "cwd": "/home/user/shop",
  "tools": [],
  "allowed_tools": ["mcp__wildberries__wb_search", "mcp__ozon__ozon_search"]
}
```

**Mixed: read files + git + one MCP tool:**
```json
{
  "prompt": "Review code and search products",
  "cwd": "/project",
  "tools": ["Read", "Glob", "Grep", "Bash", "mcp__wildberries__wb_search"],
  "allowed_tools": ["Read", "Glob", "Grep", "Bash(git:*)", "mcp__wildberries__wb_search"]
}
```

---

## CLI Reference

### Key Flags

| Flag | Purpose |
|------|---------|
| `--tools "Tool1,Tool2"` | Whitelist of available tools (disables all others) |
| `--allowed-tools "Pattern"` | Commands that execute without permission prompt |
| `--disallowed-tools "Pattern"` | Commands completely removed from context |
| `--dangerously-skip-permissions` | Bypass ALL permission checks (unsafe) |

### Restricting to Single Command

```bash
claude -p "Send message to telegram" \
  --tools "Bash" \
  --allowed-tools "Bash(/home/user/bot/venv/bin/python3 /home/user/bot/send.py:*)" \
  --output-format stream-json \
  --verbose
```

**Result:**
- ✅ `/home/user/bot/venv/bin/python3 /home/user/bot/send.py "any args"` — executes
- ❌ `rm -rf /`, `curl`, `wget`, etc. — blocked
- ⚠️ `ls`, `cat`, `pwd` — allowed (Claude auto-permits read-only commands)

### Pattern Syntax

**Prefix Matching (`:*`):**
```bash
--allowed-tools "Bash(git:*)"        # git status, git commit, git push...
--allowed-tools "Bash(npm run:*)"    # npm run test, npm run build...
```

**Exact Match:**
```bash
--allowed-tools "Bash(npm install)"  # Only exact "npm install"
```

**Tool without pattern (all uses allowed):**
```bash
--allowed-tools "Write"              # All Write operations allowed
--allowed-tools "mcp__ozon__ozon_search"  # All calls to this MCP tool
```

---

## Important Notes

### tools vs allowed_tools

| Field | What it does |
|-------|--------------|
| `tools` | What tools AI **sees** (others don't exist for it) |
| `allowed_tools` | What tools/commands AI **can execute** without blocking |

**Example:**
```json
{
  "tools": ["Bash", "Write"],
  "allowed_tools": ["Bash(git:*)"]
}
```
- AI sees: `Bash`, `Write`
- AI can execute: only `git` commands
- `Write` is visible but blocked (not in `allowed_tools`)
- `rm`, `curl` blocked (not matching `git:*` pattern)

### Read-Only Commands

Claude Code automatically allows some read-only bash commands (`ls`, `cat`, `pwd`) even without explicit permission. To block these too, use `--disallowed-tools`.

### Security Limitations

⚠️ Bash patterns can be bypassed via shell features (flag reordering, variables, redirects). Do NOT rely on patterns as a security boundary for untrusted input. For maximum security, use containers or sandboxes.

---

## References

- [Claude Code Settings](https://code.claude.com/docs/en/settings)
- [Permission Configuration](https://platform.claude.com/docs/en/agent-sdk/permissions)
- [GitHub Issue #12232](https://github.com/anthropics/claude-code/issues/12232)
