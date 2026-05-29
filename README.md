# Insta Posts (InstaAgent)

AI-powered Instagram post generator. An OpenAI Agents workflow connects to MCP (Model Context Protocol) servers over SSE to fetch live weather and news, then drafts an emoji-rich caption and a DALL·E image prompt as JSON.

## Architecture

```
┌─────────────┐     POST /api/generate-post      ┌──────────────────┐
│   Client    │ ───────────────────────────────► │  FastAPI Backend │
│  (or curl)  │         port 8000                │  backend/api.py  │
└─────────────┘                                  └────────┬─────────┘
                                                          │
                                                          ▼
                                                 ┌──────────────────┐
                                                 │  InstaCreator    │
                                                 │  Agent (Runner)  │
                                                 │  agent_handler   │
                                                 └────────┬─────────┘
                                    ┌────────────────────┼────────────────────┐
                                    ▼                    ▼                    │
                           ┌────────────────┐   ┌────────────────┐            │
                           │ Weather MCP    │   │ News MCP       │            │
                           │ :8001 /sse     │   │ :8002 /sse     │            │
                           │ fetch_weather  │   │ fetch_news     │            │
                           └────────────────┘   └────────────────┘            │
                                                                                │
                                                 GitHub Models API              │
                                                 (gpt-4o-mini) ◄────────────────┘
```

| Component | Port | Role |
|-----------|------|------|
| Backend API | 8000 | HTTP entry point; validates requests and runs the agent |
| Weather MCP | 8001 | Tool: current weather by city (mock data; OpenWeatherMap-ready) |
| News MCP | 8002 | Tool: top headlines via Google News RSS |

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- A [GitHub personal access token](https://github.com/settings/tokens) with access to **GitHub Models** (used as the LLM API key)

## Setup

1. Clone the repository and enter the project root:

   ```bash
   git clone https://github.com/ADARSHKUMAR2/Instagram_Post_Generator.git
   cd Insta_posts
   ```

2. Install dependencies:

   ```bash
   uv sync
   ```

3. Create a `.env` file in the project root (see `.gitignore`):

   ```env
   GITHUB_TOKEN=ghp_your_github_models_token
   OPENAI_API_KEY=sk_optional_if_you_switch_models
   ```

   The agent uses `GITHUB_TOKEN` with the GitHub Models inference endpoint (`https://models.inference.ai.azure.com`) and `gpt-4o-mini` by default. See `shared/config.py` to change the model or provider.

## Running the stack

All three services must be running before you call the API or run the agent standalone.

**Terminal 1 — Weather MCP**

```bash
cd mcp_servers/weather_mcp
uv run python weather_server.py
```

Health check: http://localhost:8001/status

**Terminal 2 — News MCP**

```bash
cd mcp_servers/news_mcp
uv run python news_server.py
```

Health check: http://localhost:8002/status

**Terminal 3 — Backend API**

From the project root:

```bash
uv run python backend/api.py
```

Or:

```bash
uv run uvicorn backend.api:app --reload --host 0.0.0.0 --port 8000
```

- Landing: http://localhost:8000/
- Interactive docs: http://localhost:8000/docs

### Test the agent without the API

With both MCP servers up, from the project root:

```bash
uv run python -m agent.agent_handler
```

This runs a built-in sample prompt (`Create a weather update post for Meerut today.`).

## API

**`POST /api/generate-post`**

Request body:

```json
{
  "category_request": "Create a weather post for Meerut today."
}
```

Example:

```bash
curl -X POST http://localhost:8000/api/generate-post \
  -H "Content-Type: application/json" \
  -d '{"category_request": "Summarize the latest AI news for an Instagram story."}'
```

Response:

```json
{
  "status": "success",
  "content": "{ \"caption\": \"...\", \"image_prompt\": \"...\" }"
}
```

The agent is instructed to return JSON with `caption` and `image_prompt` keys (see `agent/prompts/insta_persona.py`).

## Project structure

```
Insta_posts/
├── backend/
│   └── api.py                 # FastAPI app and /api/generate-post
├── agent/
│   ├── agent_handler.py       # Agent + MCP connections + Runner
│   ├── schemas.py             # PostRequest / PostResponse
│   └── prompts/
│       └── insta_persona.py   # System instructions for InstaCreator
├── shared/
│   └── config.py              # MCP URLs, model, API clients
├── mcp_servers/
│   ├── weather_mcp/           # Weather tools (port 8001)
│   └── news_mcp/              # News RSS tools (port 8002)
├── pyproject.toml
└── uv.lock
```

## MCP tools

| Server | Tool | Description |
|--------|------|-------------|
| Weather | `fetch_weather(city)` | Weather string for a city (mock DB: Meerut, London, New York) |
| News | `fetch_news(category)` | Top 5 Google News RSS headlines for a topic |

MCP SSE endpoints are configured in `shared/config.py`:

- Weather: `http://localhost:8001/sse`
- News: `http://localhost:8002/sse`

If the agent fails to connect, confirm both MCP processes are running and that URLs in config match the running servers.

## Troubleshooting

| Issue | What to check |
|-------|----------------|
| `ModuleNotFoundError: No module named 'shared'` | Run commands from the **project root** and use `python -m agent.agent_handler`, not `python agent/agent_handler.py`. |
| MCP connection / HTTP 307 or 404 | MCP servers must be started from their own directories (`mcp_servers/weather_mcp`, `mcp_servers/news_mcp`). |
| `500` from `/api/generate-post` | Weather and News MCP must be up; verify `GITHUB_TOKEN` is set. |
| Empty or generic news | RSS fetch needs network access; category strings are passed to Google News search. |

## Roadmap

`shared/config.py` defines placeholders for additional MCP servers (sports, facts, publish) that are not implemented yet. Weather data is mocked and intended to be swapped for a real API (e.g. OpenWeatherMap).

## License

Add a license file if you plan to open-source or distribute this project.
