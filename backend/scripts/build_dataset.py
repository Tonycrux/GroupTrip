"""Build the GroupTrip destination + activity dataset from real sources.

Destination cost  -> Budget Your Trip (via r.jina.ai), "real travelers" daily spend + dated.
Climate           -> Open-Meteo archive, 10 years of daily temperature/precipitation.
Coordinates       -> Open-Meteo geocoding.
Travel time       -> great-circle distance from Toronto (nominal origin) / 800 km/h + 1 h.
Activities        -> Wikivoyage listing templates ({{see}}, {{do}}, {{eat}}, {{drink}},
                     {{buy}}, {{go}}, {{listing}}) -> real names, hours and prices.
Description       -> Wikivoyage page intro.

Outputs destinations.json, activities.json, provenance.json.
"""

from __future__ import annotations

import csv
import json
import math
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
OUT = HERE / "out"
CACHE.mkdir(exist_ok=True)
OUT.mkdir(exist_ok=True)

ORIGIN = (43.6532, -79.3832)  # Toronto
TODAY = date.today().isoformat()
UA = "GroupTripResearch/0.1 (student research prototype)"

# name, country, country_slug, city_slug, dest_type, wikivoyage_page
CITIES = [
    ("Lisbon", "Portugal", "portugal", "lisbon", "coastal city", "Lisbon"),
    ("Barcelona", "Spain", "spain", "barcelona", "coastal city", "Barcelona"),
    ("Rome", "Italy", "italy", "rome", "cultural", "Rome"),
    ("Paris", "France", "france", "paris", "cultural", "Paris"),
    ("Amsterdam", "Netherlands", "netherlands", "amsterdam", "cultural", "Amsterdam"),
    ("Prague", "Czechia", "czech-republic", "prague", "cultural", "Prague"),
    ("Budapest", "Hungary", "hungary", "budapest", "cultural", "Budapest"),
    ("Athens", "Greece", "greece", "athens", "cultural", "Athens"),
    ("Santorini", "Greece", "greece", "santorini", "island", "Santorini|Fira|Oia"),
    ("Reykjavik", "Iceland", "iceland", "reykjavik", "nature", "Reykjavík"),
    ("Oslo", "Norway", "norway", "oslo", "city", "Oslo"),
    ("Dubrovnik", "Croatia", "croatia", "dubrovnik", "coastal city", "Dubrovnik"),
    ("Split", "Croatia", "croatia", "split", "coastal city", "Split"),
    ("Venice", "Italy", "italy", "venice", "cultural", "Venice"),
    ("Berlin", "Germany", "germany", "berlin", "city", "Berlin"),
    ("Vienna", "Austria", "austria", "vienna", "cultural", "Vienna"),
    ("Copenhagen", "Denmark", "denmark", "copenhagen", "city", "Copenhagen"),
    ("Edinburgh", "United Kingdom", "united-kingdom", "edinburgh", "cultural", "Edinburgh"),
    ("Porto", "Portugal", "portugal", "porto", "coastal city", "Porto"),
    ("Krakow", "Poland", "poland", "krakow", "cultural", "Kraków"),
    ("Istanbul", "Turkey", "turkey", "istanbul", "cultural", "Istanbul"),
    ("Marrakesh", "Morocco", "morocco", "marrakesh", "cultural", "Marrakesh"),
    ("Cairo", "Egypt", "egypt", "cairo", "cultural", "Cairo"),
    ("Cape Town", "South Africa", "south-africa", "cape-town", "coastal city", "Cape Town"),
    ("Dubai", "United Arab Emirates", "united-arab-emirates", "dubai", "city", "Dubai"),
    ("Zanzibar", "Tanzania", "tanzania", "zanzibar", "island", "Zanzibar"),
    ("Nairobi", "Kenya", "kenya", "nairobi", "nature", "Nairobi"),
    ("Tokyo", "Japan", "japan", "tokyo", "city", "Tokyo"),
    ("Kyoto", "Japan", "japan", "kyoto", "cultural", "Kyoto"),
    ("Bangkok", "Thailand", "thailand", "bangkok", "city", "Bangkok"),
    ("Chiang Mai", "Thailand", "thailand", "chiang-mai", "cultural", "Chiang Mai"),
    ("Bali", "Indonesia", "indonesia", "bali", "island", "Ubud|Bali|South Bali|Central Bali"),
    ("Singapore", "Singapore", "singapore", "", "city", "Singapore"),
    ("Seoul", "South Korea", "south-korea", "seoul", "city", "Seoul"),
    ("Hong Kong", "Hong Kong", "hong-kong", "", "city", "Hong Kong"),
    ("Hanoi", "Vietnam", "vietnam", "hanoi", "cultural", "Hanoi"),
    ("Kuala Lumpur", "Malaysia", "malaysia", "kuala-lumpur", "city", "Kuala Lumpur"),
    ("Goa", "India", "india", "goa", "island", "Goa|North Goa|South Goa|Panaji"),
    ("Male", "Maldives", "maldives", "", "island", "Malé"),
    ("Beijing", "China", "china", "beijing", "cultural", "Beijing"),
    ("Shanghai", "China", "china", "shanghai", "city", "Shanghai"),
    ("Taipei", "Taiwan", "taiwan", "taipei", "city", "Taipei"),
    ("New York", "United States", "united-states-of-america", "nyc", "city",
     "Manhattan|Brooklyn|Queens|New York City"),
    ("Mexico City", "Mexico", "mexico", "mexico-city", "city", "Mexico City"),
    ("Cancun", "Mexico", "mexico", "cancun", "coastal city", "Cancún"),
    ("Rio de Janeiro", "Brazil", "brazil", "rio-de-janeiro", "coastal city", "Rio de Janeiro"),
    ("Lima", "Peru", "peru", "lima", "city", "Lima"),
    ("Cusco", "Peru", "peru", "cusco", "nature", "Cusco"),
    ("Vancouver", "Canada", "canada", "vancouver", "city", "Vancouver"),
    ("Toronto", "Canada", "canada", "toronto", "city", "Toronto"),
    ("San Francisco", "United States", "united-states-of-america", "san-francisco", "city", "San Francisco"),
    ("Sydney", "Australia", "australia", "sydney", "coastal city", "Sydney"),
    ("Auckland", "New Zealand", "new-zealand", "auckland", "coastal city", "Auckland"),
    ("Queenstown", "New Zealand", "new-zealand", "queenstown", "mountain", "Queenstown (New Zealand)"),
    ("Melbourne", "Australia", "australia", "melbourne", "city", "Melbourne"),
    ("Nadi", "Fiji", "fiji", "", "island", "Nadi"),
    ("Kerala", "India", "india", "kerala", "nature", "Kerala|Kochi|Munnar|Kovalam"),
    ("Los Angeles", "United States", "united-states-of-america", "los-angeles", "city", "Los Angeles"),
    ("Miami", "United States", "united-states-of-america", "miami", "coastal city", "Miami"),
    ("Las Vegas", "United States", "united-states-of-america", "las-vegas", "city", "Las Vegas"),
]
TARGET = 50
FETCH_TARGET = 200  # attempt every candidate, then pick the final set below

# Final selection order (first 50 available). Balanced across regions and the
# conflict axes: climate, cost, travel time, trip type.
PREFERRED = [
    # Europe
    "Lisbon", "Barcelona", "Rome", "Paris", "Amsterdam", "Prague", "Budapest", "Athens",
    "Santorini", "Reykjavik", "Oslo", "Dubrovnik", "Split", "Venice", "Berlin", "Vienna",
    "Copenhagen", "Edinburgh", "Porto", "Krakow",
    # Middle East / Africa
    "Istanbul", "Marrakesh", "Cairo", "Cape Town", "Dubai", "Nairobi",
    # Asia
    "Tokyo", "Kyoto", "Bangkok", "Chiang Mai", "Bali", "Singapore", "Seoul", "Hong Kong",
    "Hanoi", "Kuala Lumpur", "Male", "Beijing", "Shanghai", "Taipei",
    # Americas
    "New York", "San Francisco", "Mexico City", "Cancun", "Rio de Janeiro", "Lima", "Cusco",
    # Oceania
    "Sydney", "Auckland", "Queenstown",
]


def get(url: str, cache_name: str, retries: int = 4) -> str | None:
    path = CACHE / cache_name
    if path.exists() and path.stat().st_size > 0:
        return path.read_text(encoding="utf-8", errors="ignore")
    delay = 1.5
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=90) as resp:
                text = resp.read().decode("utf-8", errors="ignore")
            path.write_text(text, encoding="utf-8")
            time.sleep(0.8)
            return text
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 503) and attempt < retries - 1:
                time.sleep(delay)
                delay *= 2
                continue
            print(f"      ! {url}: {exc}")
            return None
        except Exception as exc:  # noqa: BLE001
            if attempt < retries - 1:
                time.sleep(delay)
                delay *= 2
                continue
            print(f"      ! {url}: {exc}")
            return None
    return None


# ------------------------------------------------------------------ Budget Your Trip


def parse_cost(text: str) -> dict:
    if not text or len(text) < 4000:
        return {}
    out: dict = {}
    m = re.search(r"spend approximately \*\*\$([\d,]+)(?:\s*\([^)]*\))?\*\* per person, per day", text)
    if not m:
        m = re.search(r"\*\*\$([\d,]+)(?:\s*\([^)]*\))?\*\* per person, per day", text)
    if m:
        out["daily_cost_usd"] = float(m.group(1).replace(",", ""))
    m = re.search(r"last updated on ([A-Z][a-z]+ \d{1,2}, \d{4})", text)
    if m:
        out["cost_updated"] = m.group(1)
    for key, pat in (
        ("meals_per_day_usd", r"on meals"),
        ("transport_per_day_usd", r"on local transportation"),
        ("hotels_per_day_usd", r"on hotels"),
    ):
        m = re.search(r"\$([\d,]+)(?:\s*\([^)]*\))? " + pat, text)
        if m:
            out[key] = float(m.group(1).replace(",", ""))
    m = re.search(
        r"\*\*budget\*\* travelers spend \*\*\$([\d,]+)\*\*.*?"
        r"\*\*mid-range\*\* travelers spend \*\*\$([\d,]+)\*\*.*?"
        r"\*\*luxury\*\* travelers spend around \*\*\$([\d,]+)\*\*",
        text, re.S,
    )
    if m:
        out["budget_daily_usd"] = float(m.group(1).replace(",", ""))
        out["midrange_daily_usd"] = float(m.group(2).replace(",", ""))
        out["luxury_daily_usd"] = float(m.group(3).replace(",", ""))
    return out


# ------------------------------------------------------------------ Wikivoyage

LISTING_TEMPLATES = {"see", "do", "eat", "drink", "buy", "go", "listing", "vcard"}
TEMPLATE_TYPE = {"see": "see", "do": "do", "eat": "eat", "drink": "drink", "buy": "buy", "go": "do"}


def iter_templates(text: str):
    i = 0
    n = len(text)
    while i < n - 1:
        if text[i : i + 2] != "{{":
            i += 1
            continue
        m = re.match(r"\{\{\s*([A-Za-z_]+)", text[i:])
        if not m:
            i += 2
            continue
        name = m.group(1).lower()
        depth = 0
        j = i
        while j < n - 1:
            if text[j : j + 2] == "{{":
                depth += 1
                j += 2
                continue
            if text[j : j + 2] == "}}":
                depth -= 1
                j += 2
                if depth == 0:
                    break
                continue
            j += 1
        yield name, text[i:j]
        i = max(j, i + 2)


def split_params(block: str) -> list[str]:
    inner = block[2:-2]
    parts, buf, depth, link = [], "", 0, 0
    i = 0
    while i < len(inner):
        if inner[i : i + 2] == "{{":
            depth += 1; buf += "{{"; i += 2; continue
        if inner[i : i + 2] == "}}":
            depth -= 1; buf += "}}"; i += 2; continue
        if inner[i : i + 2] == "[[":
            link += 1; buf += "[["; i += 2; continue
        if inner[i : i + 2] == "]]":
            link -= 1; buf += "]]"; i += 2; continue
        if inner[i] == "|" and depth == 0 and link == 0:
            parts.append(buf); buf = ""; i += 1; continue
        buf += inner[i]; i += 1
    parts.append(buf)
    return parts


NON_ACTIVITY = [
    "airport", "airfield", "station", "terminal", "embassy", "consulate", "hospital",
    "police", "bus stop", "car rental", "hotel", "hostel", "guesthouse",
]
# Listings that are practical information rather than something you do
NON_ACTIVITY_NAMES = re.compile(
    r"(?i)\b(\w*pass|\w*card|tourist information|information cent(re|er)|ticket office|"
    r"money exchange|currency exchange|left luggage|laundry)\b"
)


def clean_name(value: str) -> str:
    for _ in range(4):
        value = re.sub(r"\{\{[^{}]*\}\}", "", value)
    value = re.sub(r"\[\[([^|\]]*\|)?([^\]]*)\]\]", r"\2", value)
    value = value.replace("'''", "").replace("''", "")
    value = re.sub(r"<[^>]+>", "", value)
    return re.sub(r"\s+", " ", value).strip(" |,;:")


def parse_listing(name: str, block: str, section_kind: str | None = None) -> dict | None:
    parts = split_params(block)
    fields: dict[str, str] = {}
    for part in parts[1:]:
        if "=" in part:
            k, v = part.split("=", 1)
            fields[k.strip().lower()] = v.strip()
    ltype = (
        fields.get("type", "").strip().lower()
        or TEMPLATE_TYPE.get(name)
        or section_kind
        or ""
    )
    if ltype not in {"see", "do", "eat", "drink", "buy"}:
        return None
    title = clean_name(fields.get("name", ""))
    if not title or len(title) < 3 or len(title) > 90:
        return None
    if any(bad in title.lower() for bad in NON_ACTIVITY):
        return None
    if NON_ACTIVITY_NAMES.search(title):
        return None
    return {
        "name": title,
        "kind": ltype,
        "hours": fields.get("hours", ""),
        "price": fields.get("price", ""),
        "content": fields.get("content", ""),
        "lat": _to_float(fields.get("lat")),
        "lon": _to_float(fields.get("long")),
    }


def _to_float(value: str | None) -> float | None:
    if not value:
        return None
    m = re.match(r"^\s*(-?\d+(?:\.\d+)?)", value)
    return float(m.group(1)) if m else None


SECTION_ALLOW = re.compile(r"\b(see|do|eat|drink|buy)\b", re.I)
SECTION_DENY = re.compile(
    r"(get in|get around|get out|go next|sleep|stay safe|stay healthy|connect|cope|"
    r"respect|talk|work|understand|learn|budget|weather|history|orient|"
    r"money|bank|exchange|currency|atm)",
    re.I,
)


def kind_of(heading: str):
    m = SECTION_ALLOW.search(heading or "")
    return m.group(1).lower() if m else None


def sections(wt: str):
    """Yield (level, heading, body). Level 0 is the page intro."""
    parts = re.split(r"(?m)^(={2,4})\s*(.+?)\s*\1\s*$", wt)
    if parts:
        yield 0, "", parts[0]
    i = 1
    while i + 2 < len(parts):
        yield len(parts[i]), parts[i + 1], parts[i + 2]
        i += 3


def strip_markup(text: str) -> str:
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r"\{\{[^{}]*\}\}", "", text)
    text = re.sub(r"\[\[([^|\]]*\|)?([^\]]*)\]\]", r"\2", text)
    text = re.sub(r"\[https?://\S+\s+([^\]]+)\]", r"\1", text)
    text = re.sub(r"'''?|<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _wikitext(page: str) -> str:
    text = get(
        "https://en.wikivoyage.org/w/api.php?action=parse&prop=wikitext&format=json"
        "&formatversion=2&redirects=1&page=" + urllib.parse.quote(page),
        f"wv_{re.sub(r'[^A-Za-z0-9]+', '_', page)}.json",
    )
    if not text:
        return ""
    try:
        return json.loads(text)["parse"]["wikitext"]
    except (json.JSONDecodeError, KeyError):
        return ""


def expand_districts(pages: list[str], max_subs: int = 6) -> list[str]:
    """Add district subpages (Page/District) referenced from each page."""
    expanded: list[str] = []
    for page in pages:
        if page not in expanded:
            expanded.append(page)
        wt = _wikitext(page)
        if not wt:
            continue
        subs = re.findall(r"\[\[(" + re.escape(page) + r"/[^|\]\[<>]{1,60})\|", wt)
        added = 0
        for sub in subs:
            if added >= max_subs:
                break
            if sub not in expanded:
                expanded.append(sub)
                added += 1
    return expanded


def wikivoyage_listings(pages: list[str]) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    for page in expand_districts(pages):
        wt = _wikitext(page)
        if not wt:
            continue
        stack: list[tuple[int, str | None]] = []
        for level, heading, body in sections(wt):
            if level == 0:
                stack = []
            else:
                while stack and stack[-1][0] >= level:
                    stack.pop()
                if SECTION_DENY.search(heading):
                    kind = None
                else:
                    kind = kind_of(heading) or (stack[-1][1] if stack else None)
                stack.append((level, kind))
            kind = stack[-1][1] if stack else None
            if kind is None:
                continue
            for tname, block in iter_templates(body):
                if tname not in LISTING_TEMPLATES:
                    continue
                item = parse_listing(tname, block, kind)
                if not item:
                    continue
                key = item["name"].lower()
                if key in seen:
                    continue
                seen.add(key)
                out.append(item)
    return out


def wikivoyage_intro(page: str) -> str:
    wt = _wikitext(page)
    if not wt:
        return ""
    intro = re.split(r"\n==", wt, maxsplit=1)[0]
    intro = re.sub(r"\{\{[^{}]*\}\}", "", intro)
    intro = strip_markup(intro)
    sentences = re.split(r"(?<=[.!?])\s+", intro)
    return " ".join(sentences[:2])[:400]


# ------------------------------------------------------------------ images

# Wikipedia article titles that differ from the destination's display name
WIKI_TITLE = {
    "New York": "New York City",
    "Male": "Malé",
    "Cancun": "Cancún",
    "Reykjavik": "Reykjavík",
    "Krakow": "Kraków",
    "Queenstown": "Queenstown, New Zealand",
}

# Lead images that are symbolic rather than photographic
BAD_IMAGE = re.compile(
    r"(?i)(flag|coat[_ ]of[_ ]arms|seal|logo|emblem|banner|map|marker|locator|location|blank)"
)

# Destinations whose article lead image is not a usable photo; point at a better article
IMAGE_TITLE = {
    "Santorini": "Oia, Greece",
    "Hong Kong": "Hong Kong Island",
}


def image_ok(url: str | None) -> bool:
    """Reject non-photographic lead images (flags, maps, logos) and non-free uploads."""
    if not url:
        return False
    if "wikipedia/en/" in url:  # fair-use local file, not Commons
        return False
    name = urllib.parse.unquote(url.rsplit("/", 1)[-1]).lower()
    if name.endswith(".svg") or ".svg." in name:
        return False
    return not BAD_IMAGE.search(name)


def fetch_page_image(name: str) -> str | None:
    """Lead photo for a destination, from Wikipedia (falling back to Wikivoyage).
    Images are Wikimedia Commons files; the query string is stripped for a clean URL."""
    title = IMAGE_TITLE.get(name) or WIKI_TITLE.get(name, name)
    for site in ("en.wikipedia.org", "en.wikivoyage.org"):
        url = (
            f"https://{site}/w/api.php?action=query&prop=pageimages&piprop=thumbnail"
            f"&pithumbsize=1200&format=json&formatversion=2&redirects=1&titles="
            + urllib.parse.quote(title)
        )
        text = get(url, f"img_{site.split('.')[1]}_{re.sub(r'[^A-Za-z0-9]+', '_', title)}.json")
        if not text:
            continue
        try:
            pages = json.loads(text).get("query", {}).get("pages") or []
        except json.JSONDecodeError:
            continue
        if pages:
            src = ((pages[0].get("thumbnail") or {}).get("source") or "").split("?")[0]
            if image_ok(src):
                return src
    return None


# ------------------------------------------------------------------ Open-Meteo


def geocode(name: str, country: str):
    text = get(
        "https://geocoding-api.open-meteo.com/v1/search?count=10&language=en&format=json&name="
        + urllib.parse.quote(name),
        f"geo_{re.sub(r'[^A-Za-z0-9]+', '_', name)}.json",
    )
    if not text:
        return None
    try:
        results = json.loads(text).get("results") or []
    except json.JSONDecodeError:
        return None
    for r in results:
        if r.get("country", "").lower() == country.lower():
            return {"lat": r["latitude"], "lon": r["longitude"], "admin1": r.get("admin1", "")}
    if results:
        r = results[0]
        return {"lat": r["latitude"], "lon": r["longitude"], "admin1": r.get("admin1", "")}
    return None


def climate_normals(lat: float, lon: float, cache_name: str):
    text = get(
        f"https://archive-api.open-meteo.com/v1/archive?latitude={lat:.4f}&longitude={lon:.4f}"
        f"&start_date=2014-01-01&end_date=2023-12-31"
        f"&daily=temperature_2m_mean,precipitation_sum&timezone=auto",
        cache_name,
    )
    if not text:
        return None
    try:
        daily = json.loads(text)["daily"]
    except (json.JSONDecodeError, KeyError):
        return None
    months: dict[int, list[float]] = {}
    precip = 0.0
    for d, t, p in zip(daily["time"], daily["temperature_2m_mean"], daily["precipitation_sum"]):
        if t is not None:
            months.setdefault(int(d[5:7]), []).append(t)
        if p is not None:
            precip += p
    if not months:
        return None
    means = {m: sum(v) / len(v) for m, v in months.items()}
    years = 10
    return {
        "mean_temp_c": round(sum(means.values()) / len(means), 1),
        "coldest_month_c": round(min(means.values()), 1),
        "warmest_month_c": round(max(means.values()), 1),
        "annual_precip_mm": round(precip / years),
    }


def classify_climate(n: dict) -> str:
    t_cold, t_warm, precip = n["coldest_month_c"], n["warmest_month_c"], n["annual_precip_mm"]
    if precip < 250:
        return "arid"
    if t_cold >= 18:
        return "tropical"
    if t_warm < 12:
        return "cold"
    if t_cold < 0 and t_warm >= 22:
        return "continental"
    if t_cold < 0:
        return "temperate"
    if t_warm >= 25 and t_cold >= 8:
        return "warm"
    if t_warm >= 22 and t_cold < 8:
        return "temperate"
    return "mild"


def haversine_km(a, b) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


# ------------------------------------------------------------------ activities

TYPE_RULES = [
    ("beach", ["beach", "surf", "snorkel", "diving", "dive", "lagoon", "reef",
               "coast", "seaside", "harbour", "harbor", "marina", "promenade", "pier", "cove",
               "waterfront", "playa", "praia"]),
    ("wellness", ["spa", "thermal", "hot spring", "wellness", "massage", "onsen", "hammam", "bath"]),
    ("nightlife", ["night", "club", "bar", "pub", "party", "rooftop", "live music"]),
    ("food", ["food", "wine", "tasting", "cooking", "culinary", "market", "brew", "cuisine", "dinner", "restaurant", "cafe", "coffee"]),
    ("shopping", ["shop", "souk", "bazaar", "mall", "market", "store"]),
    ("history", ["castle", "palace", "ruin", "fort", "barracks", "historic", "ancient", "archaeolog",
                 "monument", "temple", "shrine", "cathedral", "church", "mosque", "pyramid",
                 "colosseum", "acropolis", "citadel", "basilica"]),
    ("nature", ["park", "garden", "glacier", "volcano", "waterfall", "safari", "wildlife", "desert", "forest", "lake", "nature", "trek", "hike", "mountain", "fjord", "cruise", "river"]),
    ("adventure", ["kayak", "bike", "zip", "climb", "raft", "adventure", "paraglid", "sail", "dune", "diving"]),
    ("culture", ["museum", "gallery", "art", "theatre", "theater", "opera", "tour", "quarter",
                 "old town", "square", "plaza", "walk", "walking"]),
]
DURATION_BY_TYPE = {"beach": 3.0, "wellness": 2.0, "nightlife": 3.0, "food": 2.5, "shopping": 2.0,
                    "nature": 4.0, "adventure": 3.5, "history": 2.0, "culture": 2.5}
FREE_HINTS = ["park", "beach", "garden", "square", "plaza", "walk", "promenade", "bridge", "market", "viewpoint"]


def classify_type(name: str, kind: str = "see") -> str:
    # Wikivoyage's own section is the strongest signal
    if kind == "eat":
        return "food"
    if kind == "drink":
        return "nightlife"
    if kind == "buy":
        return "shopping"
    low = name.lower()
    for label, keys in TYPE_RULES:
        # whole words only (allowing plurals) - "Barcelona" must not match "bar"
        if any(re.search(rf"\b{re.escape(k)}(?:s|es)?\b", low) for k in keys):
            return label
    return "nature" if kind == "do" else "culture"


def parse_hours(value: str):
    m = re.search(r"(\d{1,2}):(\d{2})\s*[-–]\s*(\d{1,2}):(\d{2})", value or "")
    if not m:
        return None, None
    h1, m1, h2, m2 = (int(g) for g in m.groups())
    if not (0 <= h1 <= 23 and 0 <= m1 <= 59 and 0 <= h2 <= 23 and 0 <= m2 <= 59):
        return None, None
    return f"{h1:02d}:{m1:02d}", f"{h2:02d}:{m2:02d}"


def parse_price(value: str):
    if not value:
        return None
    low = value.lower()
    if "free" in low and not re.search(r"\d", low):
        return 0.0
    m = re.search(r"(\d[\d,]*)", low)
    if not m:
        return None
    amount = float(m.group(1).replace(",", ""))
    if "$" in value or "usd" in low:
        return amount
    if "€" in value or "eur" in low:
        return round(amount * 1.08, 2)
    if "£" in value or "gbp" in low:
        return round(amount * 1.27, 2)
    return None


def estimate_cost(name: str, atype: str) -> float:
    if any(h in name.lower() for h in FREE_HINTS):
        return 0.0
    return {"history": 18.0, "culture": 22.0, "nature": 12.0, "beach": 0.0,
            "food": 45.0, "nightlife": 30.0, "wellness": 40.0, "shopping": 0.0,
            "adventure": 55.0}.get(atype, 20.0)


def estimate_duration(name: str, atype: str) -> float:
    low = name.lower()
    if "full day" in low or "full-day" in low:
        return 8.0
    if "half day" in low or "half-day" in low:
        return 4.0
    return DURATION_BY_TYPE.get(atype, 2.5)


KIND_PRIORITY = {"see": 0, "do": 1, "eat": 2, "drink": 3, "buy": 4}
# Deliberately balanced so a destination's activity mix spans several interests
KIND_QUOTA = {"see": 4, "do": 4, "eat": 2, "drink": 1, "buy": 1}

# Intra-city travel model: minutes to get from the destination centre to an activity
URBAN_KMH = 18.0
TRAVEL_BASE_MIN = 5
TRAVEL_MAX_MIN = 90
TRAVEL_FALLBACK_MIN = 20


def travel_minutes(lat, lon, dest_lat, dest_lon):
    """Rough city travel time from the destination centre, from straight-line distance."""
    if lat is None or lon is None:
        return None
    km = haversine_km((dest_lat, dest_lon), (lat, lon))
    return max(TRAVEL_BASE_MIN, min(TRAVEL_MAX_MIN, round(km / URBAN_KMH * 60) + TRAVEL_BASE_MIN))


def build_activities(
    dest_id: int, listings: list[dict], dest_coords: tuple[float, float], max_n: int = 12
) -> tuple[list[dict], int]:
    buckets: dict[str, list[dict]] = {}
    for item in listings:
        buckets.setdefault(item["kind"], []).append(item)

    pool: list[dict] = []
    for kind in ("see", "do", "eat", "drink", "buy"):
        pool.extend(buckets.get(kind, [])[: max(KIND_QUOTA[kind], 12)])

    chosen: list[dict] = []
    seen: set[str] = set()
    type_counts: dict[str, int] = {}
    while len(chosen) < max_n:
        best, best_rank = None, None
        for item in pool:
            key = item["name"].lower()[:40]
            if key in seen:
                continue
            rank = (type_counts.get(classify_type(item["name"], item["kind"]), 0), KIND_PRIORITY.get(item["kind"], 9))
            if best_rank is None or rank < best_rank:
                best, best_rank = item, rank
        if best is None:
            break
        seen.add(best["name"].lower()[:40])
        atype = classify_type(best["name"], best["kind"])
        type_counts[atype] = type_counts.get(atype, 0) + 1
        chosen.append(best)

    # travel minutes from real coordinates where the listing has them
    computed = [
        travel_minutes(item["lat"], item["lon"], *dest_coords)
        for item in chosen
    ]
    known = sorted(v for v in computed if v is not None)
    fallback = known[len(known) // 2] if known else TRAVEL_FALLBACK_MIN
    with_coords = len(known)

    activities: list[dict] = []
    for item, minutes in zip(chosen, computed):
        atype = classify_type(item["name"], item["kind"])
        price = parse_price(item["price"])
        open_from, open_to = parse_hours(item["hours"])
        activities.append(
            {
                "id": dest_id * 100 + len(activities) + 1,
                "destination_id": dest_id,
                "name": item["name"][:120],
                "type": atype,
                "est_cost": float(price if price is not None else estimate_cost(item["name"], atype)),
                "duration_hours": estimate_duration(item["name"], atype),
                "open_from": open_from,
                "open_to": open_to,
                "travel_time_min": fallback if minutes is None else minutes,
                "description": strip_markup(item["content"])[:200],
            }
        )
    return activities, with_coords


# ------------------------------------------------------------------ main


DEST_CSV = ["id", "name", "region", "country", "climate", "dest_type", "est_cost",
            "travel_time_hours", "activities", "description", "image_url"]
ACT_CSV = ["id", "destination_id", "name", "type", "est_cost", "duration_hours",
           "open_from", "open_to", "travel_time_min", "description"]
PROV_CSV = ["id", "name", "cost_source", "cost_updated", "daily_cost_usd", "budget_daily_usd",
            "midrange_daily_usd", "luxury_daily_usd", "climate_source", "mean_temp_c",
            "coldest_month_c", "warmest_month_c", "annual_precip_mm", "activity_source",
            "activity_count", "activities_with_coords", "lat", "lon",
            "distance_km_from_origin", "fetched"]


def write_csvs(destinations, activities, provenance, out_dir: Path | None = None) -> None:
    out_dir = out_dir or OUT
    with (out_dir / "destinations.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=DEST_CSV)
        writer.writeheader()
        for dest in destinations:
            writer.writerow({**dest, "activities": "; ".join(dest["activities"])})

    with (out_dir / "activities.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=ACT_CSV)
        writer.writeheader()
        writer.writerows(activities)

    with (out_dir / "provenance.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=PROV_CSV)
        writer.writeheader()
        for row in provenance:
            normals = row.get("climate_normals", {})
            coords = row.get("coords", {})
            writer.writerow({
                "id": row["id"], "name": row["name"], "cost_source": row["cost_source"],
                "cost_updated": row.get("cost_updated", ""),
                "daily_cost_usd": row.get("daily_cost_usd", ""),
                "budget_daily_usd": row.get("budget_daily_usd", ""),
                "midrange_daily_usd": row.get("midrange_daily_usd", ""),
                "luxury_daily_usd": row.get("luxury_daily_usd", ""),
                "climate_source": row.get("climate_source", ""),
                "mean_temp_c": normals.get("mean_temp_c", ""),
                "coldest_month_c": normals.get("coldest_month_c", ""),
                "warmest_month_c": normals.get("warmest_month_c", ""),
                "annual_precip_mm": normals.get("annual_precip_mm", ""),
                "activity_source": row.get("activity_source", ""),
                "activity_count": row.get("activity_count", ""),
                "activities_with_coords": row.get("activities_with_coords", ""),
                "lat": coords.get("lat", ""), "lon": coords.get("lon", ""),
                "distance_km_from_origin": row.get("distance_km_from_origin", ""),
                "fetched": row.get("fetched", ""),
            })


def csv_from_json(data_dir: Path | None = None) -> None:
    """Regenerate the CSV exports from existing JSON, without refetching anything."""
    data_dir = data_dir or (HERE.parent / "data")
    destinations = json.loads((data_dir / "destinations.json").read_text(encoding="utf-8"))
    activities = json.loads((data_dir / "activities.json").read_text(encoding="utf-8"))
    provenance = json.loads((data_dir / "provenance.json").read_text(encoding="utf-8"))
    write_csvs(destinations, activities, provenance, data_dir)
    print(f"wrote destinations.csv / activities.csv / provenance.csv to {data_dir}")


def backfill_images(data_dir: Path | None = None) -> None:
    """Fill or replace destination image_url from Wikipedia/Wikivoyage, then re-export CSV."""
    data_dir = data_dir or (HERE.parent / "data")
    path = data_dir / "destinations.json"
    destinations = json.loads(path.read_text(encoding="utf-8"))

    for dest in destinations:
        if dest["name"] in IMAGE_TITLE or not image_ok(dest.get("image_url")):
            dest["image_url"] = fetch_page_image(dest["name"])
            time.sleep(1.0)

    # second pass: anything still missing is usually a transient rate limit
    for dest in destinations:
        if not image_ok(dest.get("image_url")):
            time.sleep(3.0)
            dest["image_url"] = fetch_page_image(dest["name"])

    for dest in destinations:
        print(f"  {dest['name']:<16} {(dest['image_url'] or 'NO IMAGE')[-70:]}")
    missing = [d["name"] for d in destinations if not image_ok(d.get("image_url"))]
    print(f"\n{len(destinations) - len(missing)}/{len(destinations)} destinations have a photo")
    if missing:
        print("no image:", ", ".join(missing))
    path.write_text(json.dumps(destinations, indent=2, ensure_ascii=False), encoding="utf-8")
    csv_from_json(data_dir)


def main() -> None:
    destinations: list[dict] = []
    activities: list[dict] = []
    provenance: list[dict] = []

    for name, country, cslug, cityslug, dtype, wvpage in CITIES:
        if len(destinations) >= FETCH_TARGET:
            break
        print(f"[{len(destinations) + 1:>2}] {name}")

        btt_path = f"{cslug}/{cityslug}" if cityslug else cslug
        cost = parse_cost(
            get(f"https://r.jina.ai/https://www.budgetyourtrip.com/{btt_path}",
                f"btt_{cslug}_{cityslug or 'country'}.txt") or ""
        )
        if not cost.get("daily_cost_usd"):
            print("      - no cost data")
            continue

        geo = geocode(name, country)
        if not geo:
            print("      - no coordinates")
            continue

        normals = climate_normals(geo["lat"], geo["lon"], f"climate_{cslug}_{cityslug}.json")
        if not normals:
            print("      - no climate data")
            continue

        listings = wikivoyage_listings([p for p in wvpage.split("|") if p])
        acts, with_coords = build_activities(
            len(destinations) + 1, listings, (geo["lat"], geo["lon"])
        )
        if len(acts) < 5:
            print(f"      - only {len(acts)} activities")
            continue

        dest_id = len(destinations) + 1
        dist = haversine_km(ORIGIN, (geo["lat"], geo["lon"]))
        destinations.append(
            {
                "id": dest_id,
                "name": name,
                "region": geo.get("admin1") or "",
                "country": country,
                "climate": classify_climate(normals),
                "dest_type": dtype,
                "est_cost": float(round(cost["daily_cost_usd"] * 3)),
                "travel_time_hours": round(dist / 800.0 + 1.0, 1),
                "activities": sorted({a["type"] for a in acts}),
                "description": wikivoyage_intro(wvpage.split("|")[0])[:300],
                "image_url": fetch_page_image(name),
            }
        )
        activities.extend(acts)
        provenance.append(
            {
                "id": dest_id,
                "name": name,
                "cost_source": f"https://www.budgetyourtrip.com/{btt_path}",
                "cost_updated": cost.get("cost_updated"),
                "daily_cost_usd": cost.get("daily_cost_usd"),
                "budget_daily_usd": cost.get("budget_daily_usd"),
                "midrange_daily_usd": cost.get("midrange_daily_usd"),
                "luxury_daily_usd": cost.get("luxury_daily_usd"),
                "climate_source": "Open-Meteo archive 2014-2023",
                "climate_normals": normals,
                "activity_source": f"https://en.wikivoyage.org/wiki/{urllib.parse.quote(wvpage)}",
                "activity_count": len(acts),
                "activities_with_coords": with_coords,
                "coords": {"lat": round(geo["lat"], 4), "lon": round(geo["lon"], 4)},
                "distance_km_from_origin": round(dist),
                "fetched": TODAY,
            }
        )
        print(f"      ok  cost=${cost['daily_cost_usd']:.0f}/day  climate={classify_climate(normals)}  acts={len(acts)}")

    # ---- final selection + renumber -------------------------------------- #
    by_name = {d["name"]: d for d in destinations}
    selected: list[dict] = [by_name[n] for n in PREFERRED if n in by_name]
    for dest in destinations:
        if len(selected) >= TARGET:
            break
        if dest not in selected:
            selected.append(dest)
    selected = selected[:TARGET]

    id_map = {d["id"]: i for i, d in enumerate(selected, 1)}
    selected_ids = set(id_map)
    activities = [a for a in activities if a["destination_id"] in selected_ids]
    provenance = [p for p in provenance if p["id"] in selected_ids]

    for dest in selected:
        dest["id"] = id_map[dest["id"]]
    for act in activities:
        act["destination_id"] = id_map[act["destination_id"]]
        act["id"] = act["destination_id"] * 100 + (act["id"] % 100)
    for row in provenance:
        row["id"] = id_map[row["id"]]

    (OUT / "destinations.json").write_text(json.dumps(selected, indent=2, ensure_ascii=False))
    (OUT / "activities.json").write_text(json.dumps(activities, indent=2, ensure_ascii=False))
    (OUT / "provenance.json").write_text(json.dumps(provenance, indent=2, ensure_ascii=False))
    write_csvs(selected, activities, provenance)
    print(f"\nDONE {len(selected)} destinations / {len(activities)} activities")


if __name__ == "__main__":
    if "--from-json" in sys.argv:
        csv_from_json()
    elif "--images" in sys.argv:
        backfill_images()
    else:
        main()
