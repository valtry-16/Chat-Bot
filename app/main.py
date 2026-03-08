import asyncio
import json
from collections.abc import AsyncGenerator

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import StreamingResponse

from .agent_controller import build_agent_plan
from .auth import CurrentUser, get_current_user
from .database import get_supabase
from .hf_client import HFSpaceClient
from .knowledge import (
    ToolResult,
    arxiv_search,
    extract_city_from_query,
    github_search,
    location_api,
    rss_news,
    time_api,
    weather_api,
    web_search,
    wikipedia_lookup,
)
from .memory import extract_long_term_memories
from .prompt_builder import build_prompt
from .repositories import (
    add_message,
    get_or_create_conversation,
    get_recent_messages,
    get_user_memories,
    list_conversation_messages_by_user,
    store_knowledge_cache,
    store_user_memory,
    upsert_user,
)
from .schemas import ChatRequest, MemoryOut, MessageOut

app = FastAPI(title="AI Assistant Platform Backend", version="1.0.0")
hf_client = HFSpaceClient()


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


async def execute_tools(user_message: str, memories: list[str]) -> list[ToolResult]:
    decision = build_agent_plan(user_message)
    tasks = []

    for tool in decision.tools:
        if tool == "web_search":
            tasks.append(web_search(user_message))
        elif tool == "rss_news":
            tasks.append(rss_news())
        elif tool == "wikipedia_lookup":
            tasks.append(wikipedia_lookup(user_message))
        elif tool == "weather_api":
            tasks.append(weather_api(extract_city_from_query(user_message)))
        elif tool == "time_api":
            tasks.append(time_api())
        elif tool == "location_api":
            tasks.append(location_api())
        elif tool == "arxiv_search":
            tasks.append(arxiv_search(user_message))
        elif tool == "github_search":
            tasks.append(github_search(user_message))
        elif tool == "memory_lookup":
            tasks.append(asyncio.sleep(0, result=ToolResult("memory_lookup", json.dumps(memories))))

    results = await asyncio.gather(*tasks, return_exceptions=True)
    normalized = []
    for item in results:
        if isinstance(item, Exception):
            normalized.append(ToolResult(name="tool_error", content=f"Tool error: {item}"))
            continue
        normalized.append(item)
    return normalized


@app.post("/chat")
async def chat(
    request: ChatRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    try:
        db = get_supabase()
        
        user = upsert_user(db, current_user.id, current_user.email, current_user.name)
        conversation = get_or_create_conversation(db, user["id"], request.conversation_id)

        add_message(db, conversation["id"], "user", request.message)

        extracted_memories = extract_long_term_memories(request.message)
        for memory_text, importance in extracted_memories:
            store_user_memory(db, user["id"], memory_text, importance)

        history = get_recent_messages(db, conversation["id"])
        memories = get_user_memories(db, user["id"])

        tool_results = await execute_tools(request.message, [m["memory_text"] for m in memories])
        external_text = "\n\n".join([f"[{r.name}] {r.content}" for r in tool_results])

        # Cache consolidated external knowledge for future lookup/analytics.
        store_knowledge_cache(db, topic=request.message[:255], content=external_text[:4000], source="multi_tool")

        prompt = build_prompt(
            user_question=request.message,
            history=history,
            memories=memories,
            external_knowledge=external_text,
        )

        async def event_stream() -> AsyncGenerator[str, None]:
            chunks = []
            meta = {"conversation_id": conversation["id"], "user_id": user["id"]}
            yield f"data: {json.dumps({'type': 'meta', 'data': meta})}\n\n"
            try:
                async for token in hf_client.stream_generate(
                    prompt=prompt,
                    max_tokens=request.max_tokens,
                    temperature=request.temperature,
                    top_p=request.top_p,
                ):
                    chunks.append(token)
                    yield f"data: {json.dumps({'type': 'token', 'data': token})}\n\n"

                full_text = "".join(chunks).strip()
                if full_text:
                    add_message(db, conversation["id"], "assistant", full_text)

                yield "data: {\"type\":\"done\"}\n\n"
            except Exception as exc:
                import traceback
                print(f"ERROR in HF streaming: {exc}")
                traceback.print_exc()
                error_payload = json.dumps({"type": "error", "data": str(exc)})
                yield f"data: {error_payload}\n\n"

        return StreamingResponse(event_stream(), media_type="text/event-stream")
    
    except Exception as e:
        import traceback
        print(f"ERROR in chat endpoint: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@app.get("/history/{user_id}", response_model=list[MessageOut])
async def get_history(
    user_id: str,
):
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="You can only access your own history")

    db = get_supabase()
    messages = list_conversation_messages_by_user(db, user_id)
    return [
        MessageOut(
            id=m["id"],
            conversation_id=m["conversation_id"],
            role=m["role"],
            content=m["content"],
            timestamp=m["timestamp"],
        )
        for m in messages
    ]


@app.get("/memory/{user_id}", response_model=list[MemoryOut])
async def get_memory(
    user_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="You can only access your own memory")

    db = get_supabase()
    memories = get_user_memories(db, user_id)
    return [
        MemoryOut(
            id=m["id"],
            user_id=m["user_id"],
            memory_text=m["memory_text"],
            importance=m["importance"],
            created_at=m["created_at"],
        )
        for m in memories
    ]
