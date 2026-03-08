# AI Assistant Platform Backend (Render)

FastAPI backend for Android and Telegram clients with:

- Streaming chat responses from a Hugging Face Space LLM
- Supabase auth verification
- Postgres conversation + user memory persistence
- Smart query routing for real-time external knowledge
- Tool-based knowledge retrieval and cache storage

## Architecture Mapping

- Client layer: Android app, Telegram bot
- Backend layer: this FastAPI service (`/chat`, `/history/{user_id}`, `/memory/{user_id}`)
- Database layer: Supabase Postgres + Supabase Auth
- AI model layer: Hugging Face Space (`/generate_stream`)
- External knowledge: DuckDuckGo, RSS, Wikipedia, Open-Meteo, WorldTimeAPI, ipapi, arXiv, GitHub

## Project Structure

- `app/main.py` - API server and endpoints
- `app/hf_client.py` - streaming client for Hugging Face Space
- `app/agent_controller.py` - tool planning logic
- `app/router.py` - keyword-based query routing
- `app/knowledge.py` - external tool implementations
- `app/memory.py` - long-term memory extraction
- `app/models.py` - SQLAlchemy models
- `app/repositories.py` - database operations
- `app/auth.py` - Supabase token verification
- `app/telegram_bot.py` - Telegram integration script
- `.env.example` - required environment variables
- `schema.sql` - SQL schema

## Environment Variables

Copy `.env.example` to `.env` and fill:

- `DATABASE_URL`
- `HF_SPACE_URL`
- `HF_GENERATE_PATH`
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`

## Install and Run

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Render Deployment

- Runtime: Python 3.11+
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Add all environment variables from `.env.example`

## API Endpoints

### `POST /chat`

Request:

```json
{
  "message": "What is the latest AI research?",
  "conversation_id": 1,
  "max_tokens": 512,
  "temperature": 0.7,
  "top_p": 0.9
}
```

Response: `text/event-stream`

SSE events:

- `meta` (conversation/user ids)
- `token` (incremental model output)
- `done` (stream finished)
- `error` (if any)

### `GET /history/{user_id}`

Returns stored conversation messages for that user.

### `GET /memory/{user_id}`

Returns top stored user memories for personalization.

## Authentication

- Uses Supabase Auth bearer token.
- Backend validates token via Supabase `/auth/v1/user`.
- Set `ALLOW_ANON_CHAT=true` only for local testing.

## Telegram Integration

Run optional Telegram bot proxy:

```bash
cd backend
python -m app.telegram_bot
```

Required env vars:

- `TELEGRAM_BOT_TOKEN`
- `BACKEND_CHAT_URL`
- `BACKEND_BEARER_TOKEN` (optional)

## Android Integration (Kotlin)

Android app should call backend `/chat` and parse SSE lines from `data:` frames for real-time token updates.

## Notes

- The backend builds prompts from system instructions + memory + history + external knowledge.
- User memory extraction runs on each user message.
- Knowledge results are cached in `knowledge_cache` for reuse.
