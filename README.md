# Insta Posts (InstaAgent)

AI-powered Instagram post generator with a Streamlit UI. An OpenAI Agents workflow connects to MCP (Model Context Protocol) servers for live weather and news, produces a structured caption and image prompt, and returns a Pollinations.ai image URL for a 1024×1024 preview.

## Architecture

```
┌──────────────────┐   POST /api/generate-post    ┌──────────────────┐
│  Streamlit UI    │ ───────────────────────────► │  FastAPI Backend │
│  frontend        │         (brain)              │  backend/api.py  │
│  :8501           │                              └────────┬─────────┘
└──────────────────┘                                       │
                                                           ▼
                                                  ┌──────────────────┐
                                                  │  InstaCreator    │
                                                  │  Agent (Runner)  │
                                                  │  agent_handler   │
                                                  └────────┬─────────┘
                                     ┌────────────────────┼────────────────────┐
                                     ▼                    ▼                    │
                            ┌────────────────┐   ┌────────────────┐            │
                            │ weather-mcp    │   │ news-mcp       │            │
                            │ :8001 /sse     │   │ :8002 /sse     │            │
                            │ fetch_weather  │   │ fetch_news     │            │
                            └────────────────┘   └────────────────┘            │
                                                                               │
                            GitHub Models API (gpt-4o-mini) ◄──────────────────┘
                            Pollinations.ai (FLUX) for image URL ◄── backend
```

| Service | Port | Role |
|---------|------|------|
| **frontend** | 8501 | Streamlit app — prompt input, caption, image preview |
| **brain** | 8000 | FastAPI API — agent orchestration + image URL |
| **weather-mcp** | 8001 | MCP tool: weather by city |
| **news-mcp** | 8002 | MCP tool: headlines via Google News RSS |

## Prerequisites

- Python 3.12+ and [uv](https://docs.astral.sh/uv/) (local development)
- [Docker](https://docs.docker.com/get-docker/) and Docker Compose (recommended)
- [GitHub personal access token](https://github.com/settings/tokens) with **GitHub Models** access

## Environment variables

Create `shared/.env` (loaded by Docker Compose and `python-dotenv`):

```env
GITHUB_TOKEN=ghp_your_github_models_token
OPENAI_API_KEY=sk_optional_if_you_switch_providers
```

The agent uses `GITHUB_TOKEN` against `https://models.inference.ai.azure.com` with `gpt-4o-mini`. Adjust model and client settings in `shared/config.py`.

## Run with Docker (recommended)

From the project root:

```bash
docker compose -f infrastructure/docker-compose.yml up --build
```

| URL | Description |
|-----|-------------|
| http://localhost:8501 | Streamlit UI |
| http://localhost:8000 | Backend API |
| http://localhost:8000/docs | OpenAPI docs |
| http://localhost:8001/status | Weather MCP health |
| http://localhost:8002/status | News MCP health |

The UI calls `http://brain:8000/api/generate-post` inside the Compose network. MCP URLs in `shared/config.py` use Docker service hostnames (`weather-mcp`, `news-mcp`).

Stop the stack:

```bash
docker compose -f infrastructure/docker-compose.yml down
```

## Run locally (without Docker)

MCP hostnames in `shared/config.py` default to Docker service names. For local runs, temporarily set:

```python
BASE_WEATHER_URL = "localhost"
BASE_NEWS_URL = "localhost"
```

### 1. Install dependencies

```bash
uv sync
```

### 2. Start MCP servers (two terminals)

```bash
cd mcp_servers/weather_mcp && uv run python weather_server.py
```

```bash
cd mcp_servers/news_mcp && uv run python news_server.py
```

### 3. Start the backend

From the project root:

```bash
uv run uvicorn backend.api:app --reload --host 0.0.0.0 --port 8000
```

### 4. Start the Streamlit UI

In `frontend/main_ui.py`, set `API_URL` to `http://localhost:8000/api/generate-post`, then:

```bash
uv run streamlit run frontend/main_ui.py
```

### Test the agent only

With MCP servers running and `localhost` in config:

```bash
uv run python -m agent.agent_handler
```

## API

### `POST /api/generate-post`

**Request**

```json
{
  "prompt": "Create a weather post for Meerut today."
}
```

**Response**

```json
{
  "status": "success",
  "content": {
    "caption": "☀️ ...",
    "image_prompt": "A vibrant summer scene..."
  },
  "image_url": "https://image.pollinations.ai/prompt/...?width=1024&height=1024&model=flux&nologo=true"
}
```

**Example**

```bash
curl -X POST http://localhost:8000/api/generate-post \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Summarize the latest AI news for an Instagram story."}'
```

The agent returns structured `InstaPost` output (`caption`, `image_prompt`). The backend builds a Pollinations.ai FLUX image URL from `image_prompt` (no separate image API key required for previews).

## Project structure

```
Insta_posts/
├── frontend/
│   ├── main_ui.py              # Streamlit UI
│   └── requirements.txt        # UI-only deps (Docker frontend image)
├── backend/
│   └── api.py                  # FastAPI + image URL generation
├── agent/
│   ├── agent_handler.py        # Agent, MCP clients, Runner
│   ├── schemas.py              # PostRequest, InstaPost, PostResponse
│   └── prompts/
│       └── insta_persona.py    # InstaCreator system prompt
├── shared/
│   └── config.py               # MCP URLs, GitHub Models client
├── mcp_servers/
│   ├── weather_mcp/            # Weather MCP (8001)
│   └── news_mcp/               # News MCP (8002)
├── infrastructure/
│   ├── docker-compose.yml
│   ├── Dockerfile.backend
│   ├── Dockerfile.mcp
│   └── Dockerfile.frontend
├── pyproject.toml
└── uv.lock
```

## MCP tools

| Server | Tool | Description |
|--------|------|-------------|
| Weather | `fetch_weather(city)` | Weather for a city (mock data: Meerut, London, New York) |
| News | `fetch_news(category)` | Top 5 Google News RSS headlines for a topic or category |

## Troubleshooting

| Issue | What to check |
|-------|----------------|
| UI: “Could not connect to the Brain API” | Run `docker compose ... up`; confirm **brain** is healthy on port 8000. |
| `ModuleNotFoundError: No module named 'shared'` | Run backend/agent commands from the **project root**; use `python -m agent.agent_handler`. |
| MCP connection errors locally | Set `BASE_*_URL` to `localhost` and ensure MCP processes are running. |
| MCP connection errors in Docker | Use Compose as-is; do not use `localhost` in `shared/config.py` inside containers. |
| `500` on `/api/generate-post` | Verify `GITHUB_TOKEN` in `shared/.env` and that both MCP services are up. |
| Image slow or fails in UI | Pollinations generates on first request; use the fallback link in the UI if the preview times out. |

## Roadmap

- Additional MCP servers (sports, facts, publish) sketched in config but not wired up
- Replace mock weather with a live API (e.g. OpenWeatherMap)
- Optional Replicate / other image backends (`Config.image_model` is reserved)

## License

Add a license file if you plan to open-source or distribute this project.
