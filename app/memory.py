import re


PREFERENCE_PATTERNS = [
    re.compile(r"\bI like\b(.+)", re.IGNORECASE),
    re.compile(r"\bI love\b(.+)", re.IGNORECASE),
    re.compile(r"\bI prefer\b(.+)", re.IGNORECASE),
    re.compile(r"\bMy name is\b(.+)", re.IGNORECASE),
]


def extract_long_term_memories(user_message: str) -> list[tuple[str, float]]:
    text = user_message.strip()
    if not text:
        return []

    memories: list[tuple[str, float]] = []
    for pattern in PREFERENCE_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue

        extracted = match.group(0).strip().rstrip(".")
        if len(extracted) > 6:
            importance = 0.95 if "name" in extracted.lower() else 0.75
            memories.append((extracted, importance))

    # Keep unique values and bound memory writes per message.
    unique = []
    seen = set()
    for memory_text, importance in memories:
        key = memory_text.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append((memory_text, importance))
        if len(unique) >= 3:
            break

    return unique
