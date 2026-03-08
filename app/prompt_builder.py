import json
import re

SYSTEM_PROMPT = (
    "You are a helpful, friendly AI assistant. "
    "Answer the user's question clearly and concisely in plain English. "
    "If reference data is provided below, use it to give a factual answer. "
    "Do NOT repeat the raw data — summarize it naturally. "
    "If no useful data is available, answer based on your own knowledge and say so."
)


def _summarize_external(external_knowledge: str) -> str:
    """Extract the useful parts from raw tool output so the small model isn't overwhelmed."""
    if not external_knowledge or external_knowledge.strip() == "No external knowledge retrieved.":
        return ""

    summaries: list[str] = []
    for block in external_knowledge.split("\n\n"):
        block = block.strip()
        if not block:
            continue

        # Try to parse JSON values out of the block
        # e.g. [weather_api] {"city":"New York","temperature_c":19.3,...}
        label_match = re.match(r"\[([^\]]+)\]\s*(.*)", block, re.DOTALL)
        label = label_match.group(1) if label_match else "info"
        content = label_match.group(2).strip() if label_match else block

        # If content is JSON, extract key facts
        try:
            data = json.loads(content)
            if isinstance(data, dict):
                facts = ", ".join(f"{k}: {v}" for k, v in data.items() if v)
                summaries.append(f"{label}: {facts}")
            elif isinstance(data, list):
                items = []
                for item in data[:5]:
                    if isinstance(item, dict):
                        title = item.get("title") or item.get("name") or item.get("heading") or ""
                        desc = item.get("description") or item.get("summary") or item.get("abstract") or item.get("Text") or ""
                        source = item.get("source") or item.get("link") or item.get("url") or ""
                        parts = [p for p in [title, desc[:200], source] if p]
                        items.append(" — ".join(parts))
                if items:
                    summaries.append(f"{label}:\n" + "\n".join(f"  - {i}" for i in items))
            else:
                summaries.append(f"{label}: {str(data)[:300]}")
        except (json.JSONDecodeError, TypeError):
            # Plain text — just truncate
            summaries.append(f"{label}: {content[:400]}")

    return "\n".join(summaries)[:1500]


def build_prompt(
    user_question: str,
    history: list[dict],
    memories: list[dict],
    external_knowledge: str,
) -> str:
    # Build conversation in chat-style format the model understands
    parts: list[str] = []

    # System instructions
    parts.append(f"<|im_start|>system\n{SYSTEM_PROMPT}")

    # User memories (if any)
    if memories:
        memory_lines = [m["memory_text"] for m in memories[:5]]
        parts.append("What you know about this user: " + "; ".join(memory_lines))

    parts.append("<|im_end|>")

    # Conversation history (last few turns)
    for m in history[-6:]:
        role = "user" if m["role"] == "user" else "assistant"
        parts.append(f"<|im_start|>{role}\n{m['content']}<|im_end|>")

    # Current user message with reference data
    ref_text = _summarize_external(external_knowledge)
    user_block = user_question
    if ref_text:
        user_block = f"{user_question}\n\n[Reference data for your answer]\n{ref_text}"

    parts.append(f"<|im_start|>user\n{user_block}<|im_end|>")
    parts.append("<|im_start|>assistant")

    return "\n".join(parts)
