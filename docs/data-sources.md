# Dataset sources and derivation

`backend/data/destinations.json` (50 destinations), `backend/data/activities.json`
(600 activities) and `backend/data/provenance.json` are **generated**, not hand-written.
`backend/scripts/build_dataset.py` rebuilds all three from live sources.

## What each field comes from

| Field | Source | Notes |
| --- | --- | --- |
| `est_cost` | [Budget Your Trip](https://www.budgetyourtrip.com) | mid-range cost per person per day, × 3 days, in **USD** |
| `climate` | [Open-Meteo archive API](https://open-meteo.com) | 10 years (2014–2023) of daily temperature/precipitation, classified |
| `travel_time_hours` | computed | great-circle km from Toronto ÷ 800 km/h + 1 h |
| `region`, `country`, coordinates | [Open-Meteo geocoding](https://open-meteo.com/en/docs/geocoding-api) | used for region and for distance |
| `dest_type` | editorial | `coastal city / island / cultural / nature / mountain / city` |
| `image_url` | [Wikipedia](https://en.wikipedia.org) page images | lead photo (Wikimedia Commons file), falling back to Wikivoyage |
| activities (`name`, `hours`, `price`, `description`) | [Wikivoyage](https://en.wikivoyage.org) | listing templates in See/Do/Eat/Drink/Buy sections |
| activity `type`, `duration_hours` | derived | from the Wikivoyage section + name keywords |
| activity `travel_time_min` | derived | minutes from the destination centre, from the listing's own coordinates |

Cost data was current at build time — Budget Your Trip reports its own last-updated date,
recorded per destination in `provenance.json` (46 of 50 were updated 30 Oct – 3 Nov 2026).

## Derivation rules

- **Cost.** `est_cost = mid-range daily cost × 3`. Budget Your Trip's daily figure already
  bundles accommodation, meals, local transport and sightseeing. It excludes flights — travel
  cost is represented separately by `travel_time_hours`.
- **Climate label.** From the 10-year monthly means:
  `arid` if annual precipitation < 250 mm; `tropical` if the coldest month ≥ 18 °C; `cold` if the
  warmest month < 12 °C; `continental` if the coldest month < 0 °C with a warm summer;
  `warm` if the warmest month ≥ 25 °C and the coldest ≥ 8 °C; `temperate` if the coldest < 0 °C
  or the summer is mild with a cool winter; otherwise `mild`.
- **Travel time.** Straight-line distance from Toronto (43.6532, −79.3832) over an 800 km/h
  cruising speed plus one hour of airport overhead. It is an estimate, not a schedule.
- **Intra-city travel (`travel_time_min`).** Minutes from the destination centre to the activity:
  straight-line distance ÷ 18 km/h + 5 min, capped at 90. It uses the coordinates embedded in the
  Wikivoyage listing — 404 of 600 have them; the rest fall back to that destination's median.
- **Activities.** Wikivoyage listings are taken only from See / Do / Eat / Drink / Buy sections,
  then de-duplicated and selected to spread across interest types (target ~12 per destination).
  `type` comes from the section (`eat`→food, `drink`→nightlife, `buy`→shopping) refined by name
  keywords; `duration_hours` and any missing `price` are estimates; `open_from`/`open_to` are
  left null unless the listing states hours (159 of 600 do).

## Refresh

```bash
cd backend
pdm run python scripts/build_dataset.py     # writes scripts/out/*.json + *.csv
cp scripts/out/*.json scripts/out/*.csv data/   # then reseed (delete grouptrip.db)
```

The script caches every HTTP response in `scripts/cache/`, so re-runs are cheap. It skips any
destination whose cost, coordinates, climate or activity data can't be retrieved, then takes the
final 50 in the order listed at the top of the file.

## Caveats

- **Estimates, not facts.** Costs are travel-community averages; per-activity durations, and any
  `est_cost` that is a default by type, are modelled. Treat them as plausible, not exact.
- **Derived labels.** `climate`, `dest_type` and activity `type` are classifications, not data
  from the source. Swap the thresholds in `classify_climate` / `classify_type` to change them.
- **Activity `type` is a best-effort tag.** 275 of 600 are matched from a whole word in the
  title (`Beach` → beach, `Museum` → culture, `Cathedral` → history). The other 325 fall back to
  the Wikivoyage section the listing sits in (Eat → food, Drink → nightlife, Buy → shopping,
  Do → nature, See → culture), which is coarse: an event listed under "Do" can end up as `nature`
  (e.g. a fashion week). Treat the type as a hint, not ground truth.
- **`travel_time_min` is a distance estimate, not a journey.** It assumes the destination centre
  as the start point and a fixed 18 km/h effective speed, with no routing, traffic or transit.
  Region-wide pages (Cape Town, Bali) can give long times because their listings span the whole
  region, so a few hit the 90-minute cap.
- **Individual activities are not independently dated.** The activity *names* are real and
  current; their prices and hours come from Wikivoyage and are only as fresh as that page.
- **Regional proxies.** Where Budget Your Trip has no city page, a country-level page is used
  (Singapore, Hong Kong, Maldives→Malé, Fiji→Nadi), and for a few region-shaped places the
  activity listings come from a main district page (Bali→Ubud, Goa→North/South Goa).
  `provenance.json` records the exact source URL per destination.
- **Missing `region`** on 2 destinations where the geocoder returned no admin region.
- **Images are lead images, not curated photos.** `image_url` is the article's lead image from
  the `pageimages` API. Flags, coats of arms, maps, logos and non-free uploads are filtered out,
  and a couple of destinations point at a more photogenic article (`IMAGE_TITLE` in the script:
  Santorini → Oia, Hong Kong → Hong Kong Island). All 50 resolve to Wikimedia Commons files.
- **Licensing.** Open-Meteo data is CC-BY; Wikivoyage is CC-BY-SA; Wikimedia Commons images each
  carry their own licence and need attribution; Budget Your Trip is proprietary and is used here
  only as a cited numeric reference, not redistributed in bulk.

## Files

The same three tables are written as both JSON and CSV. JSON is what the backend seeds from;
the CSV versions are for spreadsheets and quick inspection. `activities` is joined with `; `
in CSV; nested values from `provenance.json` (climate normals, coordinates) are flattened into
their own columns in `provenance.csv`.

| File | Contents |
| --- | --- |
| `data/destinations.{json,csv}` | 50 rows matching the `Destination` model |
| `data/activities.{json,csv}` | 600 rows matching the `Activity` model (`id = destination_id*100 + n`) |
| `data/provenance.{json,csv}` | per-destination source URLs, fetch date, raw cost figures, climate normals, coordinates, distance |
| `scripts/build_dataset.py` | the generator |

Regenerate the CSVs from existing JSON without refetching anything:

```bash
cd backend
pdm run python scripts/build_dataset.py --from-json
```

Fill or repair the `image_url` column (no other data is touched):

```bash
cd backend
pdm run python scripts/build_dataset.py --images
```
