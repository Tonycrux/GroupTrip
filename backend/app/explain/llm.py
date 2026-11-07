import httpx

from app.config import settings
from app.explain.base import ExplanationContext, Explainer
from app.explain.templates import TemplateExplainer

SYSTEM_PROMPT = (
    "You explain group travel recommendations. Describe only the supplied scores and "
    "conflicts. Never invent scores, never change the ranking, and never add destinations. "
    "Two or three sentences, plain language."
)


def _build_prompt(ctx: ExplanationContext) -> str:
    lines = [
        f"Destination: {ctx.destination.name} ({ctx.destination.climate}, {ctx.destination.dest_type})",
        f"Group score: {ctx.group_score:.0f}/100 (strategy: {ctx.strategy.value})",
        "Per-member scores:",
    ]
    for s in sorted(ctx.member_scores, key=lambda s: s.score, reverse=True):
        reasons = f" — {s.reasons[0]}" if s.reasons else ""
        lines.append(f"- {s.member_name}: {s.score:.0f}{reasons}")
    lines.append("Conflicts:")
    if ctx.conflicts:
        lines.extend(f"- ({c.kind}) {c.summary}" for c in ctx.conflicts)
    else:
        lines.append("- none")
    return "\n".join(lines)


class LLMExplainer:
    def __init__(self, provider: str, model: str, api_key: str):
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.fallback = TemplateExplainer()

    def explain(self, ctx: ExplanationContext) -> str:
        try:
            return self._call(ctx)
        except Exception:
            return self.fallback.explain(ctx)

    def _call(self, ctx: ExplanationContext) -> str:
        prompt = _build_prompt(ctx)
        with httpx.Client(timeout=20.0) as client:
            if self.provider == "anthropic":
                resp = client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": self.model or "claude-3-5-haiku-latest",
                        "max_tokens": 300,
                        "system": SYSTEM_PROMPT,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                )
                resp.raise_for_status()
                return resp.json()["content"][0]["text"].strip()

            resp = client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model or "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                },
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()


def get_explainer() -> Explainer:
    provider = (settings.llm_provider or "template").lower()
    if provider == "openai" and settings.openai_api_key:
        return LLMExplainer("openai", settings.llm_model, settings.openai_api_key)
    if provider == "anthropic" and settings.anthropic_api_key:
        return LLMExplainer("anthropic", settings.llm_model, settings.anthropic_api_key)
    return TemplateExplainer()
