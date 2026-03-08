import json
from dataclasses import dataclass

from .router import route_query

ALLOWED_TOOLS = {
    "web_search",
    "rss_news",
    "wikipedia_lookup",
    "weather_api",
    "time_api",
    "location_api",
    "memory_lookup",
    "memory_store",
    "arxiv_search",
    "github_search",
}


@dataclass
class AgentPlan:
    tools: list[str]


def parse_tool_call_json(text: str) -> list[str]:
    text = (text or "").strip()
    if not text.startswith("{"):
        return []

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return []

    tool = payload.get("tool")
    if isinstance(tool, str) and tool in ALLOWED_TOOLS:
        return [tool]
    return []


def build_agent_plan(user_message: str) -> AgentPlan:
    # If a message already uses explicit tool-call JSON, honor it.
    explicit_tools = parse_tool_call_json(user_message)
    if explicit_tools:
        return AgentPlan(tools=explicit_tools)

    decision = route_query(user_message)
    return AgentPlan(tools=decision.tools)
