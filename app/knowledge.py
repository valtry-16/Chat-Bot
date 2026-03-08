import asyncio
import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from importlib import import_module
from urllib.parse import quote_plus

import httpx

RSS_FEEDS = [
    "https://feeds.bbci.co.uk/news/rss.xml",
    "https://techcrunch.com/feed/",
    "https://hnrss.org/frontpage",
    "https://www.technologyreview.com/feed/",
]


@dataclass
class ToolResult:
    name: str
    content: str


def _shorten(text: str, limit: int = 1200) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


async def web_search(query: str) -> ToolResult:
    url = f"https://api.duckduckgo.com/?q={quote_plus(query)}&format=json&no_html=1&no_redirect=1"
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(url)
        response.raise_for_status()
    payload = response.json()
    abstract = payload.get("AbstractText") or ""
    heading = payload.get("Heading") or ""
    related_topics = payload.get("RelatedTopics") or []
    related = []
    for item in related_topics[:5]:
        if isinstance(item, dict) and item.get("Text"):
            related.append(item["Text"])
    summary = {
        "heading": heading,
        "abstract": abstract,
        "related": related,
    }
    return ToolResult(name="web_search", content=json.dumps(summary, ensure_ascii=True))


async def extract_article(url: str) -> str:
    # newspaper3k is synchronous, so run it in a worker thread.
    def run() -> str:
        article_module = import_module("newspaper")
        Article = getattr(article_module, "Article")
        article = Article(url)
        article.download()
        article.parse()
        return article.text

    try:
        text = await asyncio.to_thread(run)
        return _shorten(text, limit=1600)
    except Exception:
        return ""


async def rss_news() -> ToolResult:
    feedparser = import_module("feedparser")
    items = []
    for feed_url in RSS_FEEDS:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries[:3]:
            items.append(
                {
                    "title": entry.get("title", ""),
                    "link": entry.get("link", ""),
                    "published": entry.get("published", ""),
                    "source": feed.feed.get("title", feed_url),
                }
            )
    return ToolResult(name="rss_news", content=json.dumps(items[:12], ensure_ascii=True))


async def wikipedia_lookup(query: str) -> ToolResult:
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote_plus(query)}"
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(url)

    if response.status_code != 200:
        return ToolResult(name="wikipedia_lookup", content="No Wikipedia summary found")

    data = response.json()
    summary = data.get("extract") or "No summary found"
    page_url = ((data.get("content_urls") or {}).get("desktop") or {}).get("page", "")
    return ToolResult(name="wikipedia_lookup", content=_shorten(f"{summary}\nSource: {page_url}"))


async def weather_api(city: str) -> ToolResult:
    geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={quote_plus(city)}&count=1"
    async with httpx.AsyncClient(timeout=20.0) as client:
        geo_resp = await client.get(geo_url)
        geo_resp.raise_for_status()
        geo = geo_resp.json()

        results = geo.get("results") or []
        if not results:
            return ToolResult(name="weather_api", content=f"No weather location found for {city}")

        lat = results[0]["latitude"]
        lon = results[0]["longitude"]
        weather_url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}&current=temperature_2m,wind_speed_10m"
        )
        weather_resp = await client.get(weather_url)
        weather_resp.raise_for_status()
        weather = weather_resp.json().get("current", {})

    data = {
        "city": city,
        "temperature_c": weather.get("temperature_2m"),
        "wind_speed": weather.get("wind_speed_10m"),
    }
    return ToolResult(name="weather_api", content=json.dumps(data, ensure_ascii=True))


async def time_api() -> ToolResult:
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get("https://worldtimeapi.org/api/ip")
    if response.status_code != 200:
        return ToolResult(name="time_api", content="Time data unavailable")
    payload = response.json()
    data = {
        "datetime": payload.get("datetime"),
        "timezone": payload.get("timezone"),
        "utc_offset": payload.get("utc_offset"),
    }
    return ToolResult(name="time_api", content=json.dumps(data, ensure_ascii=True))


async def location_api() -> ToolResult:
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get("https://ipapi.co/json/")
    if response.status_code != 200:
        return ToolResult(name="location_api", content="Location unavailable")
    payload = response.json()
    data = {
        "ip": payload.get("ip"),
        "city": payload.get("city"),
        "region": payload.get("region"),
        "country": payload.get("country_name"),
        "timezone": payload.get("timezone"),
    }
    return ToolResult(name="location_api", content=json.dumps(data, ensure_ascii=True))


async def arxiv_search(query: str) -> ToolResult:
    url = (
        "http://export.arxiv.org/api/query"
        f"?search_query=all:{quote_plus(query)}&start=0&max_results=3"
    )
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)
        response.raise_for_status()

    root = ET.fromstring(response.text)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    papers = []
    for entry in root.findall("atom:entry", ns):
        title = (entry.findtext("atom:title", default="", namespaces=ns) or "").strip()
        summary = (entry.findtext("atom:summary", default="", namespaces=ns) or "").strip()
        link = ""
        link_node = entry.find("atom:id", ns)
        if link_node is not None:
            link = link_node.text or ""
        papers.append({"title": title, "summary": _shorten(summary, 320), "link": link})

    return ToolResult(name="arxiv_search", content=json.dumps(papers, ensure_ascii=True))


async def github_search(query: str) -> ToolResult:
    url = f"https://api.github.com/search/repositories?q={quote_plus(query)}&sort=stars&order=desc&per_page=5"
    headers = {"Accept": "application/vnd.github+json"}
    async with httpx.AsyncClient(timeout=20.0, headers=headers) as client:
        response = await client.get(url)

    if response.status_code != 200:
        return ToolResult(name="github_search", content="GitHub search unavailable")

    items = response.json().get("items") or []
    repos = [
        {
            "name": repo.get("full_name"),
            "description": repo.get("description"),
            "stars": repo.get("stargazers_count"),
            "url": repo.get("html_url"),
        }
        for repo in items[:5]
    ]
    return ToolResult(name="github_search", content=json.dumps(repos, ensure_ascii=True))


def extract_city_from_query(query: str) -> str:
    match = re.search(r"in\s+([A-Za-z\s]+)$", query.strip())
    if not match:
        return "Chennai"
    return match.group(1).strip()
