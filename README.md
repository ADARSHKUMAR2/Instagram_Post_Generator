# Insta Posts (InstaAgent)

AI-powered Instagram post generator with a Streamlit UI. An OpenAI Agents workflow pulls live weather and news via MCP servers, drafts a caption and image prompt, generates a preview image through Pollinations.ai, and can publish directly to Instagram through the Meta Graph API.

## Architecture

```
┌──────────────────┐  POST /api/generate-post   ┌──────────────────┐
│  Streamlit UI    │ ─────────────────────────► │  FastAPI Backend │
│  :8501           │  POST /api/publish-post    │  (brain) :8000   │
└──────────────────┘                            └────────┬─────────┘
                                                         │
                         ┌───────────────────────────────┼───────────────────────────────┐
                         ▼                               ▼                               ▼
                ┌─────────────────┐            ┌─────────────────┐            ┌─────────────────┐
                │ InstaCreator    │            │ Pollinations.ai │            │ Meta Graph API  │
                │ Agent + MCPs    │            │ (FLUX preview)  │            │ (publish feed)  │
                └────────┬────────┘            └─────────────────┘            └─────────────────┘
                         │
            ┌────────────┴────────────┐
            ▼                         ▼
   ┌─────────────────┐       ┌─────────────────┐
   │ weather-mcp     │       │ news-mcp        │
   │ :8001 /sse      │       │ :8002 /sse      │
   └─────────────────┘       └─────────────────┘
            │                         │
            └──────── GitHub Models API (gpt-4o-mini) ────────┘
```

| Service | Port | Role |
|---------|------|------|
| **frontend** | 8501 | Streamlit — prompt, preview caption/image, publish button |
| **brain** | 8000 | FastAPI — agent orchestration, image URL, Instagram publish |
| **weather-mcp** | 8001 | MCP tool: weather by city |
| **news-mcp** | 8002 | MCP tool: headlines via Google News RSS |

## Prerequisites

- Python 3.12+ and [uv](https://docs.astral.sh/uv/) (local development)
- [Docker](https://docs.docker.com/get-docker/) and Docker Compose (recommended)
- [GitHub personal access token](https://github.com/settings/tokens) with **GitHub Models** access
- **Instagram publishing (optional):** Meta Developer app, Instagram Business/Creator account linked to a Facebook Page, and a long-lived access token with `instagram_content_publish` permission

## Environment variables

Create `shared/.env` (loaded by Docker Compose and `python-dotenv`):

```env
# LLM (required for generation)
GITHUB_TOKEN=ghp_your_github_models_token
OPENAI_API_KEY=sk_optional_if_you_switch_providers

# Instagram publish (optional — required only for /api/publish-post)
IG_ACCOUNT_ID=your_instagram_business_account_id
IG_ACCESS_TOKEN=your_meta_graph_api_access_token
```

| Variable | Used for |
|----------|----------|
| `GITHUB_TOKEN` | GitHub Models inference (`gpt-4o-mini`) |
| `OPENAI_API_KEY` | Reserved if you switch providers in `shared/config.py` |
| `IG_ACCOUNT_ID` | Instagram Business account ID for Graph API |
| `IG_ACCESS_TOKEN` | Meta access token with publish permissions |

Generation works without Instagram credentials. Publishing returns `500` if `IG_ACCOUNT_ID` or `IG_ACCESS_TOKEN` is missing.

## Run with Docker (recommended)

From the project root:

```bash
docker compose -f infrastructure/docker-compose.yml up --build
```

Or from `infrastructure/`:

```bash
cd infrastructure && docker compose up --build
```

| URL | Description |
|-----|-------------|
| http://localhost:8501 | Streamlit UI |
| http://localhost:8000 | Backend API |
| http://localhost:8000/docs | OpenAPI docs |
| http://localhost:8001/status | Weather MCP health |
| http://localhost:8002/status | News MCP health |

Inside Compose, the UI calls `http://brain:8000`. MCP URLs in `shared/config.py` use Docker service hostnames (`weather-mcp`, `news-mcp`).

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

In `frontend/main_ui.py`, set both URLs to localhost:

```python
API_URL = "http://localhost:8000/api/generate-post"
PUBLISH_URL = "http://localhost:8000/api/publish-post"
```

Then:

```bash
uv run streamlit run frontend/main_ui.py
```

### Test the agent only

With MCP servers running and `localhost` in config:

```bash
uv run python -m agent.agent_handler
```

## Usage flow

1. Enter a prompt in the Streamlit UI (e.g. weather update, news roundup, sports headline).
2. Click **Generate Post** — the agent fetches MCP data and returns a caption + image prompt.
3. Review the caption and Pollinations-generated preview image.
4. Click **Approve & Publish to Instagram** — the backend creates a media container and publishes via the Meta Graph API.

The UI keeps generated content in Streamlit session state so the preview persists until you publish or refresh.

## API

### `POST /api/generate-post`

Generates caption, image prompt, and a Pollinations preview URL.

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

### `POST /api/publish-post`

Publishes an approved post to the connected Instagram Business account.

**Request**

```json
{
  "image_url": "https://image.pollinations.ai/prompt/...",
  "caption": "Your Instagram caption here."
}
```

**Response**

```json
{
  "status": "success",
  "message": "Post published successfully!",
  "ig_post_id": "178414..."
}
```

**Example**

```bash
curl -X POST http://localhost:8000/api/publish-post \
  -H "Content-Type: application/json" \
  -d '{"image_url": "https://example.com/image.jpg", "caption": "Hello from InstaAgent!"}'
```

Publishing uses Instagram Graph API v19.0 (`/media` → `/media_publish`). The `image_url` must be publicly reachable by Meta's servers.

## Project structure

```
Insta_posts/
├── frontend/
│   ├── main_ui.py              # Streamlit UI (generate + publish)
│   └── requirements.txt        # UI-only deps (Docker frontend image)
├── backend/
│   └── api.py                  # FastAPI: generate, publish, image URL
├── agent/
│   ├── agent_handler.py        # Agent, MCP clients, Runner
│   ├── schemas.py              # PostRequest, InstaPost, PublishRequest, PostResponse
│   └── prompts/
│       └── insta_persona.py    # InstaCreator system prompt
├── shared/
│   └── config.py               # MCP URLs, GitHub Models + Instagram credentials
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
| UI: “Could not connect to the Brain API” | Run `docker compose up`; confirm **brain** is healthy on port 8000. |
| `ModuleNotFoundError: No module named 'shared'` | Run backend/agent commands from the **project root**; use `python -m agent.agent_handler`. |
| MCP connection errors locally | Set `BASE_*_URL` to `localhost` and ensure MCP processes are running. |
| MCP connection errors in Docker | Use Compose as-is; do not use `localhost` in `shared/config.py` inside containers. |
| `500` on `/api/generate-post` | Verify `GITHUB_TOKEN` in `shared/.env` and that both MCP services are up. |
| `Missing Instagram API credentials` | Set `IG_ACCOUNT_ID` and `IG_ACCESS_TOKEN` in `shared/.env`. |
| Publish fails at container creation | Ensure `image_url` is public HTTPS; Meta must fetch the image server-side. |
| Image slow or fails in UI | Pollinations generates on first request; use the direct link fallback in the UI. |

## Roadmap

- Additional MCP servers (sports, facts, publish) sketched in config but not wired up
- Replace mock weather with a live API (e.g. OpenWeatherMap)
- Optional Replicate / other image backends (`Config.image_model` is reserved)

## License

Add a license file if you plan to open-source or distribute this project.
