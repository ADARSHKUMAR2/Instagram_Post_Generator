# Insta Posts (InstaAgent)

AI-powered Instagram post generator with a Streamlit UI. An OpenAI Agents workflow pulls live weather and news via MCP servers, drafts captions and image prompts, generates previews through Pollinations.ai, and publishes to Instagram via the Meta Graph API. Optional pipelines pull images from Google Drive through AWS S3, queue scheduled posts, and send Discord notifications on success.

## Architecture

```
┌──────────────────┐
│  Streamlit UI    │  generate / publish / drive upload
│  :8501           │
└────────┬─────────┘
         │  HTTP
         ▼
┌──────────────────────────────────────────────────────────────────┐
│  FastAPI Backend (brain) :8000                                   │
│  ├─ InstaCreator agent (MCP → GitHub Models)                     │
│  ├─ Pollinations.ai image URLs                                   │
│  ├─ Meta Graph API publish                                       │
│  ├─ Drive → S3 → Instagram pipeline                              │
│  ├─ SQLite post queue + APScheduler (1 min interval)             │
│  └─ Discord webhook notifications                                │
└────────┬─────────────────────────────┬───────────────────────────┘
         │                             │
         ▼                             ▼
┌─────────────────┐           ┌─────────────────┐
│ weather-mcp     │           │ news-mcp        │
│ :8001 /sse      │           │ :8002 /sse      │
└─────────────────┘           └─────────────────┘
```

| Service | Port | Role |
|---------|------|------|
| **frontend** | 8501 | Streamlit — AI generation, direct publish, Google Drive publish |
| **brain** | 8000 | FastAPI — agent, publishing, queue, integrations |
| **weather-mcp** | 8001 | MCP tool: weather by city |
| **news-mcp** | 8002 | MCP tool: headlines via Google News RSS |

## Prerequisites

- Python 3.12+ and [uv](https://docs.astral.sh/uv/)
- [Docker](https://docs.docker.com/get-docker/) and Docker Compose (recommended)
- [GitHub personal access token](https://github.com/settings/tokens) with **GitHub Models** access

**Optional integrations**

| Integration | Required for |
|-------------|--------------|
| Meta Graph API (`IG_ACCOUNT_ID`, `IG_ACCESS_TOKEN`) | Publishing to Instagram |
| AWS S3 (`STORAGE_*`) | Google Drive pipeline and queued Drive posts |
| Google service account (`infrastructure/google_creds.json`) | Drive download; backend startup |
| Discord webhook (`DISCORD_WEBHOOK_URL`) | Publish success notifications |

## Environment variables

Create `shared/.env` (loaded by Docker Compose and `python-dotenv`):

```env
# LLM (required for generation)
GITHUB_TOKEN=ghp_your_github_models_token
OPENAI_API_KEY=sk_optional_if_you_switch_providers

# Instagram publish
IG_ACCOUNT_ID=your_instagram_business_account_id
IG_ACCESS_TOKEN=your_meta_graph_api_access_token

# AWS S3 handoff bucket (required for Drive pipeline)
STORAGE_BUCKET_NAME=your-instagram-handoff-bucket
STORAGE_ACCESS_KEY=your_aws_access_key
STORAGE_SECRET_KEY=your_aws_secret_key

# Discord notifications (optional)
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...

# Optional overrides
DB_PATH=/app/infrastructure/queue.db
GOOGLE_APPLICATION_CREDENTIALS=/app/infrastructure/google_creds.json
```

### Google Drive credentials

1. Create a Google Cloud service account with Drive read access.
2. Download the JSON key to `infrastructure/google_creds.json` (gitignored).
3. Share target Drive files/folders with the service account email.

Docker Compose mounts this path via `GOOGLE_APPLICATION_CREDENTIALS=/app/infrastructure/google_creds.json`.

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

MCP hostnames in `shared/config.py` default to Docker service names. For local runs, set:

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

The backend starts an APScheduler job on startup that processes the post queue every minute.

### 4. Start the Streamlit UI

In `frontend/main_ui.py`, point URLs at localhost:

```python
API_URL = "http://localhost:8000/api/generate-post"
PUBLISH_URL = "http://localhost:8000/api/publish-post"
# Also update the publish-from-drive URL to localhost
```

Then:

```bash
uv run streamlit run frontend/main_ui.py
```

### Test the agent only

```bash
uv run python -m agent.agent_handler
```

## Usage flows

### AI-generated post

1. Enter a prompt in the Streamlit UI.
2. Click **Generate Post** — agent fetches MCP data, returns caption + Pollinations preview.
3. Review the caption and image.
4. Click **Approve & Publish to Instagram**.

### Google Drive image

1. Scroll to **Publish from Google Drive** in the UI.
2. Paste a Drive share link or file ID and enter a caption.
3. Click **Publish Drive Image to Instagram**.

Backend flow: Drive download → temporary S3 upload → Meta container → publish → S3/local cleanup → Discord notification.

### Scheduled posts

Queue a post for later via the API. The background scheduler checks every minute and publishes due items.

Supported `source_type` values:

| Type | `file_id_or_url` |
|------|------------------|
| `pollinations` | Public image URL (e.g. Pollinations link) |
| `drive` | Google Drive file ID |

## API

### `POST /api/generate-post`

Generates caption, image prompt, and a Pollinations preview URL.

```json
// Request
{ "prompt": "Create a weather post for Meerut today." }

// Response
{
  "status": "success",
  "content": { "caption": "...", "image_prompt": "..." },
  "image_url": "https://image.pollinations.ai/prompt/..."
}
```

### `POST /api/publish-post`

Publishes a Pollinations or other public image URL directly to Instagram.

```json
// Request
{ "image_url": "https://...", "caption": "Your caption" }

// Response
{ "status": "success", "message": "Post published successfully!", "ig_post_id": "..." }
```

### `POST /api/publish-from-drive`

Downloads an image from Google Drive, stages it on S3, and publishes to Instagram.

```json
// Request
{ "drive_file_id": "1abc...", "caption": "Your caption" }

// Response
{
  "status": "success",
  "message": "Post pulled from Drive, processed via S3, and pushed to Instagram!",
  "ig_post_id": "..."
}
```

### `POST /api/queue-post`

Adds a post to the SQLite queue for scheduled publishing.

```json
// Request
{
  "source_type": "pollinations",
  "file_id_or_url": "https://image.pollinations.ai/prompt/...",
  "caption": "Scheduled post caption",
  "scheduled_time": "2026-05-30T09:00:00"
}

// Response
{ "status": "success", "message": "Post #1 added to the queue!" }
```

**Examples**

```bash
curl -X POST http://localhost:8000/api/generate-post \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Summarize the latest AI news."}'

curl -X POST http://localhost:8000/api/queue-post \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "pollinations",
    "file_id_or_url": "https://image.pollinations.ai/prompt/sunset",
    "caption": "Good morning!",
    "scheduled_time": "2026-05-30T09:00:00"
  }'
```

## Project structure

```
Insta_posts/
├── frontend/
│   └── main_ui.py                    # Streamlit UI
├── backend/
│   └── api.py                        # FastAPI routes + startup scheduler
├── agent/
│   ├── agent_handler.py              # InstaCreator agent + MCP clients
│   ├── schemas.py                    # Request/response models
│   └── prompts/insta_persona.py
├── shared/
│   └── config.py                     # MCP URLs, GitHub Models, Instagram creds
├── mcp_servers/
│   ├── weather_mcp/                  # Port 8001
│   └── news_mcp/                     # Port 8002
├── infrastructure/
│   ├── docker-compose.yml
│   ├── Dockerfile.backend
│   ├── Dockerfile.mcp
│   ├── Dockerfile.frontend
│   ├── google_creds.json             # Google service account (gitignored)
│   ├── queue.db                      # SQLite queue (created at runtime)
│   └── services/
│       ├── aws_s3.py                 # Temporary S3 upload/purge
│       ├── google_drive.py           # Drive file download
│       ├── discord_notifier.py       # Webhook notifications
│       ├── db_manager.py             # SQLite post queue
│       └── scheduler.py              # APScheduler background worker
├── pyproject.toml
└── uv.lock
```

## MCP tools

| Server | Tool | Description |
|--------|------|-------------|
| Weather | `fetch_weather(city)` | Weather for a city (mock: Meerut, London, New York) |
| News | `fetch_news(category)` | Top 5 Google News RSS headlines |

## Troubleshooting

| Issue | What to check |
|-------|----------------|
| Backend fails on startup | `infrastructure/google_creds.json` must exist (Drive manager initializes at boot). |
| UI: “Could not connect to the Brain API” | Run `docker compose up`; confirm **brain** on port 8000. |
| `ModuleNotFoundError: No module named 'shared'` | Run from project root; use `python -m agent.agent_handler`. |
| MCP connection errors locally | Set `BASE_*_URL` to `localhost`; ensure MCP processes are running. |
| `Missing Instagram API credentials` | Set `IG_ACCOUNT_ID` and `IG_ACCESS_TOKEN` in `shared/.env`. |
| Drive publish fails | Service account has access to the file; S3 bucket allows public-read objects. |
| Meta container creation fails | `image_url` must be public HTTPS reachable by Meta's servers. |
| Queue post not publishing | Check `scheduled_time` is in the past; scheduler runs every 1 minute. |
| No Discord notification | Set `DISCORD_WEBHOOK_URL`; failures are logged but do not block publish. |
| Image slow in UI | Pollinations generates on first request; use the direct link fallback. |

## Roadmap

- Additional MCP servers (sports, facts) sketched in config but not wired up
- Replace mock weather with a live API (e.g. OpenWeatherMap)
- UI for scheduling queued posts
- Optional Replicate / other image backends (`Config.image_model`)

## License

Add a license file if you plan to open-source or distribute this project.
