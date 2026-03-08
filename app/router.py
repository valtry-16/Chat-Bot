from dataclasses import dataclass


@dataclass
class RouteDecision:
    tools: list[str]


def route_query(user_message: str) -> RouteDecision:
    text = user_message.lower()
    tools: list[str] = []

    if any(word in text for word in ["weather", "temperature", "rain", "forecast"]):
        tools.append("weather_api")
    if any(word in text for word in ["time", "timezone", "clock"]):
        tools.append("time_api")
    if any(word in text for word in ["where am i", "my location", "location", "country", "city"]):
        tools.append("location_api")
    if any(word in text for word in ["wiki", "wikipedia", "who is", "what is"]):
        tools.append("wikipedia_lookup")
    if any(word in text for word in ["news", "latest", "today", "breaking"]):
        tools.append("rss_news")
    if any(word in text for word in ["paper", "research", "arxiv"]):
        tools.append("arxiv_search")
    if any(word in text for word in ["github", "repository", "repo", "open source"]):
        tools.append("github_search")

    if not tools:
        tools.append("web_search")

    # Always allow memory lookup for personalization.
    if "memory_lookup" not in tools:
        tools.append("memory_lookup")

    return RouteDecision(tools=tools)
