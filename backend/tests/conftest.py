import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.db import get_session
from app.main import app
from app.models import Activity, Destination


@pytest.fixture
def client():
    """TestClient backed by a throwaway in-memory database with one destination."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(
            Destination(
                id=1,
                name="Barcelona",
                climate="warm",
                dest_type="coastal city",
                est_cost=1000,
                travel_time_hours=2,
                activities=["beach", "food"],
            )
        )
        session.add(
            Activity(
                id=1,
                destination_id=1,
                name="Beach day",
                type="beach",
                est_cost=0,
                duration_hours=3,
            )
        )
        session.commit()

    def override():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override
    yield TestClient(app)
    app.dependency_overrides.clear()
