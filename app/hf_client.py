from collections.abc import AsyncGenerator

import httpx

from .config import settings


class HFSpaceClient:
    def __init__(self) -> None:
        self.base_url = settings.hf_space_url.rstrip("/")
        self.path = settings.hf_generate_path
        self.timeout = settings.hf_timeout_seconds

    async def stream_generate(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> AsyncGenerator[str, None]:
        payload = {
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
        }

        url = f"{self.base_url}{self.path}"
        headers = {"Accept": "text/event-stream"}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream("POST", url, json=payload, headers=headers) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    yield data

    async def generate_text(
        self,
        prompt: str,
        max_tokens: int = 256,
        temperature: float = 0.2,
        top_p: float = 0.9,
    ) -> str:
        chunks = []
        async for chunk in self.stream_generate(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
        ):
            chunks.append(chunk)
        return "".join(chunks)
