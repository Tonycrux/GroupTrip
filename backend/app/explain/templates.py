from app.engine.aggregation import strategy_label
from app.explain.base import ExplanationContext


class TemplateExplainer:
    def explain(self, ctx: ExplanationContext) -> str:
        label = strategy_label(ctx.strategy)
        parts = [
            f"{ctx.destination.name} scores {ctx.group_score:.0f}/100 for the group, {label}."
        ]

        ranked = sorted(ctx.member_scores, key=lambda s: s.score, reverse=True)
        if ranked:
            best = ranked[0]
            parts.append(f"{best.member_name} is best served ({best.score:.0f}/100).")

        if len(ranked) > 1:
            worst = ranked[-1]
            detail = worst.reasons[0] if worst.reasons else f"score {worst.score:.0f}/100"
            parts.append(f"{worst.member_name} is least satisfied because {detail}.")

        if ctx.conflicts:
            parts.append("Trade-off: " + ctx.conflicts[0].summary + ".")
        else:
            parts.append("No outstanding conflicts were detected for this destination.")

        return " ".join(parts)
