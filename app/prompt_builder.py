SYSTEM_PROMPT = (
    "You are a helpful AI assistant. Use provided memory and external data when relevant. "
    "If external data is missing, answer honestly and avoid hallucination."
)


def build_prompt(
    user_question: str,
    history: list[dict],
    memories: list[dict],
    external_knowledge: str,
) -> str:
    history_lines = [f"{m['role'].upper()}: {m['content']}" for m in history[-10:]]
    memory_lines = [f"- {m['memory_text']}" for m in memories[:5]]

    parts = [
        "SYSTEM",
        SYSTEM_PROMPT,
        "",
        "USER MEMORY",
        "\n".join(memory_lines) if memory_lines else "- No user memory available",
        "",
        "CONVERSATION HISTORY",
        "\n".join(history_lines) if history_lines else "No previous conversation.",
        "",
        "EXTERNAL DATA",
        external_knowledge or "No external knowledge retrieved.",
        "",
        "USER QUESTION",
        user_question,
    ]
    return "\n".join(parts)
