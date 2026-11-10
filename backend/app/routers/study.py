from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.models import (
    EventLog,
    Participant,
    Scenario,
    StudySession,
    SurveyResponse,
    TaskInstance,
    Trip,
)
from app.schemas import (
    EventLogCreate,
    EventLogRead,
    ParticipantCreate,
    ParticipantRead,
    ScenarioCreate,
    ScenarioRead,
    SessionCreate,
    SessionRead,
    SessionUpdate,
    SurveyResponseCreate,
    SurveyResponseRead,
    TaskInstanceCreate,
    TaskInstanceRead,
    TaskInstanceUpdate,
    TripRead,
)

router = APIRouter(tags=["study"])


@router.post("/participants", response_model=ParticipantRead, status_code=201)
def create_participant(
    payload: ParticipantCreate, session: Session = Depends(get_session)
) -> Participant:
    participant = Participant(**payload.model_dump())
    session.add(participant)
    session.commit()
    session.refresh(participant)
    return participant


@router.get("/participants", response_model=list[ParticipantRead])
def list_participants(session: Session = Depends(get_session)) -> list[Participant]:
    return list(session.exec(select(Participant)).all())


@router.post("/sessions", response_model=SessionRead, status_code=201)
def create_session(
    payload: SessionCreate, session: Session = Depends(get_session)
) -> StudySession:
    data = payload.model_dump()
    data["status"] = payload.status.value
    study_session = StudySession(**data)
    session.add(study_session)
    session.commit()
    session.refresh(study_session)
    return study_session


@router.get("/sessions", response_model=list[SessionRead])
def list_sessions(session: Session = Depends(get_session)) -> list[StudySession]:
    return list(session.exec(select(StudySession)).all())


@router.get("/sessions/{session_id}", response_model=SessionRead)
def get_session_(session_id: int, session: Session = Depends(get_session)) -> StudySession:
    study_session = session.get(StudySession, session_id)
    if study_session is None:
        raise HTTPException(status_code=404, detail="session not found")
    return study_session


@router.patch("/sessions/{session_id}", response_model=SessionRead)
def update_session(
    session_id: int, payload: SessionUpdate, session: Session = Depends(get_session)
) -> StudySession:
    study_session = session.get(StudySession, session_id)
    if study_session is None:
        raise HTTPException(status_code=404, detail="session not found")
    data = payload.model_dump(exclude_unset=True)
    if data.get("status") is not None:
        data["status"] = data["status"].value
    for key, value in data.items():
        setattr(study_session, key, value)
    session.add(study_session)
    session.commit()
    session.refresh(study_session)
    return study_session


@router.post("/scenarios", response_model=ScenarioRead, status_code=201)
def create_scenario(
    payload: ScenarioCreate, session: Session = Depends(get_session)
) -> Scenario:
    scenario = Scenario(**payload.model_dump())
    session.add(scenario)
    session.commit()
    session.refresh(scenario)
    return scenario


@router.get("/scenarios", response_model=list[ScenarioRead])
def list_scenarios(session: Session = Depends(get_session)) -> list[Scenario]:
    return list(session.exec(select(Scenario)).all())


@router.post("/tasks", response_model=TaskInstanceRead, status_code=201)
def create_task(
    payload: TaskInstanceCreate, session: Session = Depends(get_session)
) -> TaskInstance:
    if session.get(StudySession, payload.session_id) is None:
        raise HTTPException(status_code=404, detail="session not found")
    if payload.scenario_id is not None and session.get(Scenario, payload.scenario_id) is None:
        raise HTTPException(status_code=404, detail="scenario not found")
    data = payload.model_dump()
    data["variant"] = payload.variant.value
    task = TaskInstance(**data)
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


@router.get("/tasks/{task_id}", response_model=TaskInstanceRead)
def get_task(task_id: int, session: Session = Depends(get_session)) -> TaskInstance:
    task = session.get(TaskInstance, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return task


@router.get("/tasks/{task_id}/trip", response_model=TripRead)
def get_task_trip(task_id: int, session: Session = Depends(get_session)) -> Trip:
    """The trip this task belongs to, so a single study link can open the right screen."""
    if session.get(TaskInstance, task_id) is None:
        raise HTTPException(status_code=404, detail="task not found")
    trip = session.exec(select(Trip).where(Trip.task_instance_id == task_id)).first()
    if trip is None:
        raise HTTPException(status_code=404, detail="no trip is attached to this task")
    return trip


@router.get("/sessions/{session_id}/tasks", response_model=list[TaskInstanceRead])
def list_tasks(session_id: int, session: Session = Depends(get_session)) -> list[TaskInstance]:
    if session.get(StudySession, session_id) is None:
        raise HTTPException(status_code=404, detail="session not found")
    return list(
        session.exec(select(TaskInstance).where(TaskInstance.session_id == session_id)).all()
    )


@router.patch("/tasks/{task_id}", response_model=TaskInstanceRead)
def update_task(
    task_id: int, payload: TaskInstanceUpdate, session: Session = Depends(get_session)
) -> TaskInstance:
    task = session.get(TaskInstance, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    data = payload.model_dump(exclude_unset=True)
    if data.get("status") is not None:
        data["status"] = data["status"].value
    for key, value in data.items():
        setattr(task, key, value)
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


@router.post("/events", response_model=EventLogRead, status_code=201)
def create_event(
    payload: EventLogCreate, session: Session = Depends(get_session)
) -> EventLog:
    if session.get(TaskInstance, payload.task_instance_id) is None:
        raise HTTPException(status_code=404, detail="task not found")
    event = EventLog(**payload.model_dump())
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


@router.get("/tasks/{task_id}/events", response_model=list[EventLogRead])
def list_events(task_id: int, session: Session = Depends(get_session)) -> list[EventLog]:
    return list(session.exec(select(EventLog).where(EventLog.task_instance_id == task_id)).all())


@router.post("/surveys", response_model=SurveyResponseRead, status_code=201)
def create_survey_response(
    payload: SurveyResponseCreate, session: Session = Depends(get_session)
) -> SurveyResponse:
    if session.get(TaskInstance, payload.task_instance_id) is None:
        raise HTTPException(status_code=404, detail="task not found")
    if session.get(Participant, payload.participant_id) is None:
        raise HTTPException(status_code=404, detail="participant not found")
    response = SurveyResponse(**payload.model_dump())
    session.add(response)
    session.commit()
    session.refresh(response)
    return response


@router.get("/tasks/{task_id}/surveys", response_model=list[SurveyResponseRead])
def list_survey_responses(
    task_id: int, session: Session = Depends(get_session)
) -> list[SurveyResponse]:
    return list(
        session.exec(select(SurveyResponse).where(SurveyResponse.task_instance_id == task_id)).all()
    )
