# Insta Posts (InstaAgent)

Autonomous Instagram post generator with a Streamlit UI. An OpenAI Agents workflow pulls live weather and news via MCP servers, drafts captions and image prompts, generates AI previews through Pollinations.ai, and semantically matches your Google Drive image library using CLIP + ChromaDB. Publish immediately, pick from Drive matches, schedule posts, or ingest assets from Kaggle.

## Architecture

```
┌──────────────────┐
│  Streamlit UI    │  generate · gallery · publish · queue · diagnostics
│  :8501           │
└────────┬─────────┘
         │
         ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  FastAPI Backend (brain) :8000                                             │
│  ├─ InstaCreator agent (MCP → GitHub Models gpt-4o-mini)                   │
│  ├─ Pollinations.ai FLUX preview URLs                                      │
│  ├─ ChromaDB + CLIP semantic Drive search                                  │
│  ├─ Meta Graph API publish                                                 │
│  ├─ Drive → S3 → Instagram pipeline                                        │
│  ├─ SQLite queue + APScheduler (1 min)                                     │
│  └─ Discord webhook notifications                                          │
└──────┬──────────────────────────────┬──────────────────────────────────────┘
       │                              │
       ▼                              ▼
┌─────────────┐              ┌─────────────────┐
│ weather-mcp │              │ news-mcp        │
│ :8001       │              │ :8002           │
└─────────────┘              └─────────────────┘

Offline / ops scripts:
  index_drive.py      → Drive folder → ChromaDB vectors
  kaggle_to_drive.py  → Kaggle dataset → Google Drive
```

| Service | Port | Role |
|---------|------|------|
| **frontend** | 8501 | Streamlit — generation, image gallery, publish, queue dashboard |
| **brain** | 8000 | FastAPI — agent, vector search, publishing, queue |
| **weather-mcp** | 8001 | MCP: weather by city |
| **news-mcp** | 8002 | MCP: Google News RSS headlines |

## Features

- **AI post generation** — MCP-grounded captions + Pollinations image concepts
- **Semantic Drive matching** — CLIP embeddings in ChromaDB return top Drive images per prompt
- **Image gallery** — publish AI-generated art or a matched Drive asset
- **Direct Drive publish** — immediate or scheduled via SQLite queue
- **Queue dashboard** — view, refresh, and cancel pending posts
- **ChromaDB diagnostics** — vector count and recent ingestions from the UI
- **Asset pipelines** — index existing Drive images; optional Kaggle → Drive bulk upload

## Prerequisites

- Python 3.12+ and [uv](https://docs.astral.sh/uv/)
- [Docker](https://docs.docker.com/get-docker/) and Docker Compose (recommended)
- [GitHub personal access token](https://github.com/settings/tokens) with **GitHub Models** access

**Optional integrations**

| Integration | Required for |
|-------------|--------------|
| Meta Graph API (`IG_ACCOUNT_ID`, `IG_ACCESS_TOKEN`) | Publishing to Instagram |
| AWS S3 (`STORAGE_*`) | Drive pipeline and queued Drive posts |
| Google service account (`infrastructure/google_creds.json`) | Drive download, image proxy, indexing |
| Discord webhook (`DISCORD_WEBHOOK_URL`) | Publish success notifications |
| Kaggle API credentials | `kaggle_to_drive.py` dataset ingestion |

## Environment variables

Create `shared/.env` (loaded by Docker Compose and `python-dotenv`):

```env
# LLM (required for generation)
GITHUB_TOKEN=ghp_your_github_models_token
OPENAI_API_KEY=sk_optional_if_you_switch_providers

# Instagram publish
IG_ACCOUNT_ID=your_instagram_business_account_id
IG_ACCESS_TOKEN=your_meta_graph_api_access_token

# AWS S3 handoff (Drive → Instagram pipeline)
STORAGE_BUCKET_NAME=your-instagram-handoff-bucket
STORAGE_ACCESS_KEY=your_aws_access_key
STORAGE_SECRET_KEY=your_aws_secret_key

# Discord (optional)
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...

# Optional overrides
DB_PATH=/app/infrastructure/queue.db
GOOGLE_APPLICATION_CREDENTIALS=/app/infrastructure/google_creds.json
```

### Google Drive setup

1. Create a Google Cloud service account with Drive API access.
2. Save the JSON key to `infrastructure/google_creds.json` (gitignored).
3. Share your target Drive folder with the service account email.
4. Update `TARGET_DRIVE_FOLDER_ID` in `infrastructure/services/google_drive.py` if needed.

Docker Compose sets `GOOGLE_APPLICATION_CREDENTIALS=/app/infrastructure/google_creds.json`.

### Kaggle setup

For `kaggle_to_drive.py`, configure [Kaggle API credentials](https://www.kaggle.com/docs/api) (`~/.kaggle/kaggle.json` or `KAGGLE_USERNAME` / `KAGGLE_KEY`).

## Install dependencies

The project uses **uv dependency groups**:

```bash
# Backend (FastAPI, ChromaDB, CLIP, AWS, Google, scheduler)
uv sync --group backend

# Frontend only
uv sync --group frontend
```

Docker images install the appropriate group per service (`Dockerfile.backend`, `Dockerfile.mcp`, `Dockerfile.frontend`).

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

> **Note:** The backend loads the CLIP model (`clip-ViT-B-32`) on first boot. Initial startup can take a minute while weights download.

Stop the stack:

```bash
docker compose -f infrastructure/docker-compose.yml down
```

## Index your Drive image library

Semantic search only works after images are embedded into ChromaDB.

**Inside the running `brain` container:**

```bash
docker compose -f infrastructure/docker-compose.yml exec brain \
  uv run python infrastructure/services/index_drive.py
```

This script:

1. Lists images in the configured Drive folder
2. Downloads each file temporarily
3. Indexes CLIP embeddings into `infrastructure/vectordb/` (persisted via volume mount)

**Check the database:**

```bash
docker compose -f infrastructure/docker-compose.yml exec brain \
  uv run python infrastructure/services/check_db.py
```

Or use the **Database Diagnostics** section in the Streamlit UI (`GET /api/db-status`).

### Ingest images from Kaggle (optional)

Upload a Kaggle dataset to Drive (tracked in `infrastructure/dataset_registry.json` to prevent duplicates):

```bash
uv run --group backend python infrastructure/services/kaggle_to_drive.py
```

Edit the dataset handle in the script’s `__main__` block or call `ingest_kaggle_dataset("owner/dataset-name")` programmatically.

## Run locally (without Docker)

Set MCP hostnames in `shared/config.py`:

```python
BASE_WEATHER_URL = "localhost"
BASE_NEWS_URL = "localhost"
```

### 1. Sync backend dependencies

```bash
uv sync --group backend
```

### 2. Start MCP servers

```bash
cd mcp_servers/weather_mcp && uv run python weather_server.py
```

```bash
cd mcp_servers/news_mcp && uv run python news_server.py
```

### 3. Start the backend

```bash
uv run uvicorn backend.api:app --reload --host 0.0.0.0 --port 8000
```

### 4. Start Streamlit

In `frontend/main_ui.py`, replace `http://brain:8000` with `http://localhost:8000` for all API URLs, then:

```bash
uv sync --group frontend
uv run streamlit run frontend/main_ui.py
```

## Usage flows

### AI post with Drive matches

1. Enter a prompt → **Generate Post**.
2. Review the caption and **Image Gallery** (AI concept + up to 3 semantic Drive matches).
3. Select an image with the radio control.
4. Click **Approve & Publish to Instagram** (Pollinations URL or Drive → S3 pipeline).

### Google Drive (manual)

- **Publish Immediately** — direct Drive → S3 → Instagram
- **Schedule for Later** — adds a `drive` source row to the SQLite queue

### Queue dashboard

View scheduled posts, statuses (`pending`, `processing`, `completed`, `failed`), and cancel pending items.

## API reference

### `POST /api/generate-post`

Generates caption, image prompt, Pollinations URL, and semantic Drive matches.

```json
// Request
{ "prompt": "Create a weather post for Meerut today." }

// Response
{
  "status": "success",
  "content": { "caption": "...", "image_prompt": "..." },
  "image_url": "https://image.pollinations.ai/prompt/...",
  "drive_matches": ["drive_file_id_1", "drive_file_id_2"]
}
```

### `POST /api/publish-post`

Publish a public image URL (e.g. Pollinations) to Instagram.

```json
{ "image_url": "https://...", "caption": "Your caption" }
```

### `POST /api/publish-from-drive`

Drive download → S3 staging → Meta publish → cleanup.

```json
{ "drive_file_id": "1abc...", "caption": "Your caption" }
```

### `POST /api/queue-post`

Schedule a post for the background worker.

```json
{
  "source_type": "drive",
  "file_id_or_url": "1abc...",
  "caption": "Scheduled caption",
  "scheduled_time": "2026-05-30T09:00:00"
}
```

`source_type`: `drive` | `pollinations`

### `GET /api/queue-status`

Returns all rows in the post queue.

### `DELETE /api/queue/{post_id}`

Cancels a pending scheduled post.

### `POST /api/search-drive`

Semantic search over indexed Drive images.

```json
{ "query": "sunset over mountains", "top_k": 3 }
```

### `GET /api/image/{file_id}`

Streams a Drive image through the backend (used by the UI gallery).

### `GET /api/db-status`

ChromaDB diagnostics: vector count and recent metadata.

## Project structure

```
Insta_posts/
├── frontend/
│   └── main_ui.py                    # Streamlit UI
├── backend/
│   └── api.py                        # FastAPI routes
├── agent/
│   ├── agent_handler.py              # InstaCreator + MCP
│   ├── schemas.py
│   └── prompts/insta_persona.py
├── shared/
│   └── config.py
├── mcp_servers/
│   ├── weather_mcp/
│   └── news_mcp/
├── infrastructure/
│   ├── docker-compose.yml
│   ├── Dockerfile.backend
│   ├── Dockerfile.mcp
│   ├── Dockerfile.frontend
│   ├── google_creds.json             # gitignored
│   ├── queue.db                      # SQLite queue (runtime)
│   ├── vectordb/                     # ChromaDB persistence
│   ├── dataset_registry.json         # Kaggle ingest lock file
│   └── services/
│       ├── vector_manager.py         # ChromaDB + CLIP
│       ├── index_drive.py            # Drive → vector indexer
│       ├── kaggle_to_drive.py        # Kaggle → Drive uploader
│       ├── google_drive.py
│       ├── aws_s3.py
│       ├── db_manager.py
│       ├── scheduler.py
│       ├── discord_notifier.py
│       └── check_db.py
├── pyproject.toml                    # uv dependency groups
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
| Slow backend startup | CLIP model downloads on first boot; wait for `VectorManager ready!` in logs. |
| No Drive matches on generate | Run `index_drive.py`; confirm ChromaDB count via `/api/db-status`. |
| Backend fails on startup | `infrastructure/google_creds.json` must exist. |
| UI cannot connect | Run `docker compose up`; confirm **brain** on port 8000. |
| `ModuleNotFoundError: shared` | Run from project root; use `python -m` for agent modules. |
| MCP errors locally | Set `BASE_*_URL` to `localhost`; start both MCP servers. |
| Missing Instagram credentials | Set `IG_ACCOUNT_ID` and `IG_ACCESS_TOKEN`. |
| Drive publish fails | Service account has folder access; S3 objects must be public-readable. |
| Meta container fails | `image_url` must be public HTTPS reachable by Meta. |
| Queue post not firing | `scheduled_time` in the past; scheduler runs every 1 minute. |
| AI image warning in gallery | Pollinations may be congested; select a Drive match instead. |
| Kaggle ingest fails | Valid Kaggle API credentials; Drive upload may need expanded OAuth scopes. |

## Roadmap

- Additional MCP servers (sports) sketched in config
- Live weather API (e.g. OpenWeatherMap)
- Drive upload scope alignment for full Kaggle pipeline
- UI-triggered re-indexing without CLI

## License

Add a license file if you plan to open-source or distribute this project.
