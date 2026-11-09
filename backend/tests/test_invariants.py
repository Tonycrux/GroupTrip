def setup_trip(client):
    trip = client.post("/trips", json={"name": "Trip", "days": 2}).json()
    trip_id = trip["id"]
    ada = client.post(f"/trips/{trip_id}/members", json={"name": "Ada"}).json()
    ben = client.post(f"/trips/{trip_id}/members", json={"name": "Ben"}).json()
    return trip_id, ada["id"], ben["id"]


def test_only_owner_can_change_condition_status(client):
    trip_id, ada, ben = setup_trip(client)
    condition = client.post(
        f"/trips/{trip_id}/conditions",
        json={"member_id": ben, "text": "no more than 500", "type": "budget", "status": "fixed"},
    ).json()

    denied = client.patch(
        f"/conditions/{condition['id']}",
        json={"status": "flexible"},
        headers={"X-Member-Id": str(ada)},
    )
    assert denied.status_code == 403

    allowed = client.patch(
        f"/conditions/{condition['id']}",
        json={"status": "flexible"},
        headers={"X-Member-Id": str(ben)},
    )
    assert allowed.status_code == 200
    assert allowed.json()["status"] == "flexible"


def test_confirm_requires_the_owner(client):
    trip_id, ada, ben = setup_trip(client)
    condition = client.post(
        f"/trips/{trip_id}/conditions",
        json={"member_id": ben, "text": "veg only", "type": "other"},
    ).json()

    assert client.post(
        f"/conditions/{condition['id']}/confirm", headers={"X-Member-Id": str(ada)}
    ).status_code == 403
    confirmed = client.post(
        f"/conditions/{condition['id']}/confirm", headers={"X-Member-Id": str(ben)}
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["confirmed_by_owner_at"] is not None


def test_fixed_condition_survives_recommendations(client):
    trip_id, ada, ben = setup_trip(client)
    client.post(
        f"/trips/{trip_id}/conditions",
        json={"member_id": ben, "text": "no more than 500", "type": "budget", "status": "fixed"},
    )
    client.get(f"/trips/{trip_id}/recommendations")
    conditions = client.get(f"/trips/{trip_id}/conditions").json()
    assert conditions[0]["status"] == "fixed"


def test_veto_blocks_destination(client):
    trip_id, ada, ben = setup_trip(client)
    client.post(
        f"/trips/{trip_id}/vetoes",
        json={"member_id": ben, "destination_id": 1, "reason": "not for me"},
    )
    top = client.get(f"/trips/{trip_id}/recommendations").json()[0]
    assert top["destination"]["id"] == 1
    assert top["group_score"] == 0.0
    assert any(c["kind"] == "veto" for c in top["conflicts"])


def test_rating_feedback_feeds_the_score(client):
    trip_id, ada, ben = setup_trip(client)
    before = client.get(f"/trips/{trip_id}/recommendations").json()[0]["group_score"]
    client.post(f"/members/{ada}/ratings", json={"destination_id": 1, "value": "interested"})
    after = client.get(f"/trips/{trip_id}/recommendations").json()[0]["group_score"]
    assert after > before


def test_interested_if_spawns_a_condition(client):
    trip_id, ada, ben = setup_trip(client)
    rating = client.post(
        f"/members/{ada}/ratings",
        json={"destination_id": 1, "value": "interested_if", "reason": "only if under 900"},
    ).json()
    assert rating["condition_id"] is not None
    conditions = client.get(f"/trips/{trip_id}/conditions").json()
    assert any(c["id"] == rating["condition_id"] for c in conditions)


def test_rating_requires_exactly_one_target(client):
    _trip_id, ada, _ben = setup_trip(client)
    missing = client.post(f"/members/{ada}/ratings", json={"value": "interested"})
    assert missing.status_code == 422
    both = client.post(
        f"/members/{ada}/ratings",
        json={"destination_id": 1, "activity_id": 1, "value": "interested"},
    )
    assert both.status_code == 422


def test_all_members_must_approve(client):
    trip_id, ada, ben = setup_trip(client)
    assert client.get(f"/trips/{trip_id}/approvals").json()["fully_approved"] is False
    client.post(f"/trips/{trip_id}/approvals", json={"member_id": ada})
    assert client.get(f"/trips/{trip_id}/approvals").json()["fully_approved"] is False
    client.post(f"/trips/{trip_id}/approvals", json={"member_id": ben})
    status = client.get(f"/trips/{trip_id}/approvals").json()
    assert status["fully_approved"] is True
    assert status["pending_member_ids"] == []


def test_conflicts_are_persisted(client):
    trip_id, ada, ben = setup_trip(client)
    client.put(f"/members/{ada}/profile", json={"budget_max": 5000})
    client.put(f"/members/{ben}/profile", json={"budget_max": 500})
    detected = client.post(f"/trips/{trip_id}/conflicts/detect").json()
    assert any(c["kind"] == "budget" for c in detected)
    listed = client.get(f"/trips/{trip_id}/conflicts").json()
    assert len(listed) == len(detected)


def test_inferred_field_can_be_corrected(client):
    _trip_id, ada, _ben = setup_trip(client)
    client.patch(
        f"/members/{ada}/profile/budget_max",
        json={"value": 800, "source": "inferred", "confidence": 0.4},
    )
    profile = client.get(f"/members/{ada}/profile").json()
    assert profile["budget_max"] == 800
    field = next(f for f in profile["fields"] if f["field"] == "budget_max")
    assert field["source"] == "inferred"

    client.put(f"/members/{ada}/profile", json={"budget_max": 900})
    profile = client.get(f"/members/{ada}/profile").json()
    field = next(f for f in profile["fields"] if f["field"] == "budget_max")
    assert field["source"] == "explicit"
    assert profile["budget_max"] == 900
