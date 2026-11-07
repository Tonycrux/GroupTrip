from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.models import Destination
from app.schemas import DestinationRead

router = APIRouter(prefix="/destinations", tags=["destinations"])


@router.get("", response_model=list[DestinationRead])
def list_destinations(session: Session = Depends(get_session)) -> list[Destination]:
    return list(session.exec(select(Destination)).all())


@router.get("/{destination_id}", response_model=DestinationRead)
def get_destination(
    destination_id: int, session: Session = Depends(get_session)
) -> Destination:
    destination = session.get(Destination, destination_id)
    if destination is None:
        raise HTTPException(status_code=404, detail="destination not found")
    return destination
