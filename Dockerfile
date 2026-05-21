FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY agents ./agents

RUN uv sync --extra telegram --no-dev

ENV PYTHONUNBUFFERED=1

CMD ["uv", "run", "harness-agent", "serve", "--agent", "agents/example/agent.yaml"]
