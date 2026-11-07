import json
from datetime import time

from sqlmodel import Session, select

from app.config import settings
from app.db import engine
from app.models import Activity, Destination


def _parse_time(value):
    if not value or not isinstance(value, str):
        return value
    hours, minutes = value.split(":")
    return time(int(hours), int(minutes))


def seed_if_empty() -> None:
    with Session(engine) as session:
        if session.exec(select(Destination)).first() is not None:
            return

        destinations = json.loads((settings.data_dir / "destinations.json").read_text())
        activities = json.loads((settings.data_dir / "activities.json").read_text())

        for dest in destinations:
            session.add(Destination(**dest))

        for act in activities:
            payload = dict(act)
            payload["open_from"] = _parse_time(payload.get("open_from"))
            payload["open_to"] = _parse_time(payload.get("open_to"))
            session.add(Activity(**payload))

        session.commit()
