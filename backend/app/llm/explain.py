import hashlib, json, re
from pydantic import BaseModel, ValidationError
from app.llm.client import complete
from app.llm.prompts import SYS_EXPLAIN

class MemberLine(BaseModel):
    member: str
    line: str

class Explanation(BaseModel):
    headline: str
    per_member: list[MemberLine]

_NUM = re.compile(r"\d+(?:\.\d+)?")
def _nums(text: str) -> set[float]:
    return {float(x) for x in _NUM.findall(text.replace(",", ""))}

def build_input(dest, scored, conflicts, group_score, rule_text, names) -> dict:
    return {
        "destination": dest.name,
        "ranking_rule": rule_text,
        "group_score": round(group_score),
        "estimated_cost": round(dest.est_cost),
        "flight_hours": dest.travel_time_hours,
        "members": [{"member": s.member_name, "score": round(s.score),
                     "problems": s.reasons} for s in scored],
        "conflicts": [{"kind": c.kind, "topic": c.subject, "summary": c.summary,
                       "wanted_by": [names[i] for i in c.wanted_by],
                       "avoided_by": [names[i] for i in c.avoided_by]} for c in conflicts],
    }

def validate(raw: str, inp: dict, other_destinations: list[str]):
    raw = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.M).strip()
    try:
        out = Explanation.model_validate_json(raw)
    except ValidationError:
        return None, ["not valid JSON for the schema"]
    errs = []
    if {p.member for p in out.per_member} != {m["member"] for m in inp["members"]}:
        errs.append("member list does not match")
    text = out.headline + " " + " ".join(p.line for p in out.per_member)
    errs += [f"number not in input: {n:g}" for n in sorted(_nums(text) - _nums(json.dumps(inp)))]
    errs += [f"mentions another destination: {d}" for d in other_destinations
             if d.lower() in text.lower()]
    return (None if errs else out), errs

def template(inp: dict) -> Explanation:
    return Explanation(
        headline=f"{inp['destination']} scores {inp['group_score']}/100 for the group.",
        per_member=[MemberLine(member=m["member"],
                               line=(m["problems"][0] if m["problems"] else "No problems flagged.")
                                    + f" Score {m['score']}.") for m in inp["members"]])

_cache: dict[str, dict] = {}   # move to a SQLite table so the study sees identical text

async def explain(inp: dict, other_destinations: list[str]) -> dict:
    key = hashlib.sha256(json.dumps(inp, sort_keys=True).encode()).hexdigest()
    if key in _cache:
        return _cache[key]
    try:
        out, errs = validate(await complete(SYS_EXPLAIN, json.dumps(inp)), inp, other_destinations)
    except Exception as e:                     # timeout, rate limit, no key
        out, errs = None, [f"llm error: {type(e).__name__}"]
    result = {"source": "llm" if out else "template", "errors": errs,
              **(out or template(inp)).model_dump()}
    if out:
        _cache[key] = result                   # never cache fallbacks
    return result