# Harness Agent

Базовый harness для агентов: LiteLLM как LLM-шлюз, сменные UI/channel connectors, guardrails, tools, skills, cache, sessions, memory, метрики и профиль агента в YAML.

## Идея

Новый агент создается как маленькая директория:

```text
agents/my_agent/
  agent.yaml
  prompts/system.md
```

В `agent.yaml` выбираются модель, guardrails, tools и skills. Код harness остается общим.
Там же выбираются UI/connectors: по дефолту Telegram, но можно подключить console, Slack, web, API или любой другой адаптер.

## Быстрый старт

```bash
uv sync --extra dev
cp .env.example .env
export OPENAI_API_KEY=...
uv run harness-agent run --agent agents/example/agent.yaml "Найди 3 факта про LiteLLM"
```

Локальный интерактивный режим без Telegram:

```bash
uv run harness-agent serve --agent agents/example/agent.yaml --channel console
```

Telegram connector:

```bash
uv sync --extra telegram
export TELEGRAM_BOT_TOKEN=...
export TELEGRAM_THINKING_MESSAGE=Думаю...
uv run harness-agent serve --agent agents/example/agent.yaml
```

Когда Telegram-бот получает сообщение, он сразу отправляет pending-сообщение и затем редактирует его на финальный ответ. Пустой `TELEGRAM_THINKING_MESSAGE` отключает это поведение.

Для веб-поиска можно подключить один из провайдеров:

```bash
export BRAVE_SEARCH_API_KEY=...
# или
export TAVILY_API_KEY=...
```

Если ключи не заданы, `web_search` использует DuckDuckGo fallback без ключа. Brave/Tavily остаются предпочтительными для более стабильного production-поиска.

## Model Config

Модель выбирается в `agent.yaml`:

```yaml
model: openai/gpt-5
```

Ключи и endpoint задаются в `.env`, а не в `agent.yaml`. Для обычных провайдеров достаточно provider-specific ключей:

```bash
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
```

Для OpenAI-compatible gateway/proxy можно задать request-level override:

```bash
LITELLM_API_KEY=...
LITELLM_API_BASE=https://your-gateway.example/v1
LITELLM_MODEL=openai/gpt-5
```

`LITELLM_MODEL` переопределяет модель из `agent.yaml`, чтобы можно было менять модель без правки профиля агента.

## Что внутри

- `harness_agent.agent.AgentRunner` - основной loop с tool calls.
- `harness_agent.llm.LiteLLMChatClient` - тонкий адаптер над LiteLLM.
- `harness_agent.channels` - сменные UI/connectors, по умолчанию `telegram`.
- `harness_agent.guardrails` - registry проверок входа, tool calls и финального ответа.
- `harness_agent.tools` - registry и базовые tools.
- `harness_agent.skills` - декларативные расширения, которые добавляют инструкции и tools.
- `harness_agent.cache` - сменный cache store для tool results.
- `harness_agent.sessions` - сменный store для истории конкретного чата.
- `harness_agent.memory` - сменный memory store для долговременного контекста с policy перед записью.
- `harness_agent.context.ContextBuilder` - сбор system prompt, memory и session history с budget.
- `harness_agent.evals` - YAML eval cases и runner.
- `harness_agent.observability` - trace/span events поверх JSONL метрик.
- `harness_agent.errors` - типизированная модель ошибок.
- `harness_agent.scheduler` - отложенные задачи и tool `schedule_task`.
- `harness_agent.tools.ToolExecutor` - единое выполнение tools с cache, guardrails, observability и permissions.
- built-in `current_time` tool для локального времени в IANA timezone.
- `harness_agent.metrics.JsonlMetricsSink` - события запусков в JSONL.

## Evals

```bash
uv run harness-agent eval --agent agents/example/agent.yaml --cases agents/example/evals/smoke.yaml
```

## Doctor

Проверить agent config и runtime prerequisites:

```bash
uv run harness-agent doctor --agent agents/example/agent.yaml
```

`doctor` проверяет unknown extensions, ключи для выбранной модели, channel env и writable storage paths.

## Tool Permissions

Каждый tool имеет `risk_level`:

- `safe`
- `read_only`
- `write`
- `external_side_effect`

Agent profile явно разрешает уровни риска:

```yaml
allowed_tool_risk_levels:
  - safe
  - read_only
  - write
```

Если tool включен, но его `risk_level` не разрешен, `ToolExecutor` заблокирует вызов, а `doctor` покажет config error.

## Filesystem Tool

`filesystem` умеет `read`, `write`, `append`, `mkdir`, `list`, но только внутри `FILE_WORKSPACE_ROOT`:

```bash
FILE_WORKSPACE_ROOT=agent_workspace
```

Пути должны быть относительными. Попытки выйти через `..` или абсолютный путь наружу блокируются.

По умолчанию для пользовательских файлов создана папка `agent_workspace/`.

## Scheduler

Агент может использовать tool `schedule_task`, чтобы сохранить prompt на будущий запуск. Локальные задачи лежат в `runs/scheduled_tasks.json`.

```bash
uv run harness-agent tasks list
uv run harness-agent tasks run-due --agent agents/example/agent.yaml
```

При `serve` scheduler loop запускается вместе с агентом и периодически выполняет due-задачи. Если задача была создана из активного channel, результат отправляется обратно в тот же `conversation_id`.

## Docker Compose

```bash
docker compose up --build
```

Compose использует `.env`, монтирует `./agents` и `./runs`, поэтому профили агентов и локальные stores сохраняются на хосте.

## Создание нового агента

```bash
uv run harness-agent new-agent my_agent
```

Дальше:

1. Измените `agents/my_agent/prompts/system.md`.
2. Выберите модель в `agent.yaml`, например `openai/gpt-4o-mini`, `anthropic/claude-3-5-sonnet-20241022` или любой LiteLLM-compatible id.
3. Включите нужные tools/skills.
4. Включите нужные channels, например `telegram`, `console` или свой connector.
5. Включите нужные guardrails или зарегистрируйте свои в `GuardrailRegistry`.
6. Выберите cache/session/memory backend, по умолчанию `local_json`, `local_json`, `local_jsonl`.
