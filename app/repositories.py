from supabase import Client

from .config import settings


def upsert_user(db: Client, user_id: str, email: str, name: str | None) -> dict:
    response = db.table("users").upsert({
        "id": user_id,
        "email": email,
        "name": name
    }).execute()
    return response.data[0] if response.data else {"id": user_id, "email": email, "name": name}


def get_or_create_conversation(db: Client, user_id: str, conversation_id: int | None) -> dict:
    if conversation_id:
        response = db.table("conversations").select("*").eq("id", conversation_id).eq("user_id", user_id).execute()
        if response.data:
            return response.data[0]
    
    response = db.table("conversations").insert({"user_id": user_id}).execute()
    return response.data[0]


def add_message(db: Client, conversation_id: int, role: str, content: str) -> dict:
    response = db.table("messages").insert({
        "conversation_id": conversation_id,
        "role": role,
        "content": content
    }).execute()
    return response.data[0] if response.data else {}


def get_recent_messages(db: Client, conversation_id: int) -> list[dict]:
    response = db.table("messages")\
        .select("*")\
        .eq("conversation_id", conversation_id)\
        .order("timestamp", desc=True)\
        .limit(settings.max_history_messages)\
        .execute()
    
    messages = response.data or []
    messages.reverse()
    return messages


def get_user_memories(db: Client, user_id: str) -> list[dict]:
    response = db.table("user_memory")\
        .select("*")\
        .eq("user_id", user_id)\
        .order("importance", desc=True)\
        .order("created_at", desc=True)\
        .limit(settings.max_user_memories)\
        .execute()
    
    return response.data or []


def store_user_memory(db: Client, user_id: str, memory_text: str, importance: float = 0.7) -> dict:
    response = db.table("user_memory").insert({
        "user_id": user_id,
        "memory_text": memory_text,
        "importance": importance
    }).execute()
    return response.data[0] if response.data else {}


def list_conversation_messages_by_user(db: Client, user_id: str) -> list[dict]:
    response = db.table("messages")\
        .select("*, conversations!inner(user_id)")\
        .eq("conversations.user_id", user_id)\
        .order("timestamp")\
        .execute()
    
    return response.data or []


def store_knowledge_cache(db: Client, topic: str, content: str, source: str) -> dict:
    response = db.table("knowledge_cache").insert({
        "topic": topic,
        "content": content,
        "source": source
    }).execute()
    return response.data[0] if response.data else {}
