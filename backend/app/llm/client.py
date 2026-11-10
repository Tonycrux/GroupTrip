import os
from openai import AsyncOpenAI

_client = None

async def complete(system: str, user: str, max_tokens: int = 1500) -> str:
    global _client
    _client = _client or AsyncOpenAI(
        base_url=os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1"),
        api_key=os.environ["LLM_API_KEY"], timeout=15)
    r = await _client.chat.completions.create(
        model=os.environ["LLM_MODEL"], max_tokens=max_tokens,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}])
    return r.choices[0].message.content or ""