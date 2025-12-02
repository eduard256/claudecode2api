# Claude Code API Gateway

API-шлюз для Claude Code CLI с SSE streaming, поддержкой параллельных запросов и полным проксированием JSON output.

## Возможности

- SSE streaming raw JSON без модификаций
- Поддержка множества параллельных запросов
- Управление сессиями (новые/продолжение через session_id)
- Прерывание выполнения запроса
- Поддержка всех параметров Claude Code CLI
- Basic Auth авторизация
- Автоопределение пути к Claude Code
- Systemd автозапуск

## Быстрый старт

```bash
# Клонировать репозиторий
git clone <repo-url>
cd claudecode2api

# Установка
./install.sh

# Настроить .env
nano .env

# Запустить
sudo systemctl start claudecode2api
```

## Конфигурация

Скопируйте `.env.example` в `.env` и настройте:

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

### `GET /health`

Проверка состояния сервиса.

```bash
curl http://localhost:9876/health
```

```json
{
  "status": "ok",
  "claude_path": "/home/user/.local/bin/claude",
  "claude_version": "2.0.56 (Claude Code)"
}
```

### `POST /chat`

Запуск Claude Code с SSE streaming.

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

| Поле | Тип | Обязательно | Описание |
|------|-----|-------------|----------|
| `prompt` | string | ✅ | Промпт пользователя |
| `cwd` | string | ✅ | Рабочая директория |
| `model` | string | - | Модель (sonnet, opus, haiku) |
| `session_id` | string | - | ID сессии для продолжения |
| `system_prompt` | string | - | Заменить системный промпт |
| `append_system_prompt` | string | - | Дополнить системный промпт |
| `tools` | string[] | - | Список инструментов |
| `allowed_tools` | string[] | - | Whitelist инструментов |
| `disallowed_tools` | string[] | - | Blacklist инструментов |
| `permission_mode` | string | - | Режим разрешений |
| `mcp_config` | string[] | - | MCP конфигурация |
| `add_dir` | string[] | - | Дополнительные директории |
| `debug` | bool/string | - | Режим отладки |
| `json_schema` | object | - | JSON Schema для output |
| `agents` | object | - | Custom agents |

**Response:** SSE Stream

```
event: message
data: {"type":"system","subtype":"init","session_id":"uuid-here",...}

event: message
data: {"type":"assistant","message":{"content":[{"type":"text","text":"..."}]}}

event: message
data: {"type":"result","subtype":"success",...}

event: done
data: {"process_id":"uuid-here"}
```

### `DELETE /chat/{process_id}`

Прервать выполнение процесса.

```bash
curl -X DELETE http://localhost:9876/chat/uuid-here \
  -u admin:password
```

```json
{"status": "cancelled", "process_id": "uuid-here"}
```

### `GET /processes`

Список активных процессов.

```bash
curl http://localhost:9876/processes \
  -u admin:password
```

```json
{
  "processes": [
    {
      "process_id": "uuid",
      "cwd": "/home/user/project",
      "model": "sonnet",
      "started_at": "2024-01-01T12:00:00Z",
      "session_id": "claude-session-uuid"
    }
  ],
  "count": 1
}
```

## Примеры использования

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

### cURL с SSE

```bash
curl -N -X POST http://localhost:9876/chat \
  -u admin:password \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello", "cwd": "/tmp"}'
```

## Управление сессиями

Claude Code использует session_id для сохранения контекста между запросами.

1. Первый запрос возвращает session_id в первом сообщении `type: system`
2. Для продолжения диалога передайте session_id в следующем запросе:

```json
{
  "prompt": "What files did you create?",
  "cwd": "/home/user/project",
  "session_id": "previous-session-id"
}
```

## Systemd

```bash
# Статус
sudo systemctl status claudecode2api

# Запуск
sudo systemctl start claudecode2api

# Остановка
sudo systemctl stop claudecode2api

# Перезапуск
sudo systemctl restart claudecode2api

# Логи
sudo journalctl -u claudecode2api -f
```

## Разработка

```bash
# Создать виртуальное окружение
python3 -m venv venv
source venv/bin/activate

# Установить зависимости
pip install -r requirements.txt

# Запустить в режиме разработки
uvicorn app.main:app --reload --host 0.0.0.0 --port 9876
```

## API Documentation

После запуска доступна интерактивная документация:

- Swagger UI: http://localhost:9876/docs
- ReDoc: http://localhost:9876/redoc

## Лицензия

MIT
