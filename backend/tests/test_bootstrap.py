def setup(client):
    trip = client.post("/trips", json={"name": "Trip", "days": 2}).json()
    trip_id = trip["id"]
    ada = client.post(f"/trips/{trip_id}/members", json={"name": "Ada"}).json()
    ben = client.post(f"/trips/{trip_id}/members", json={"name": "Ben"}).json()

    client.put(f"/members/{ada['id']}/profile", json={"budget_max": 5000, "climates": ["warm"]})
    client.put(f"/members/{ben['id']}/profile", json={"budget_max": 500})

    client.post(
        f"/trips/{trip_id}/conditions",
        json={"member_id": ben["id"], "text": "max 500", "type": "budget", "status": "fixed"},
    )
    client.post(
        f"/trips/{trip_id}/vetoes",
        json={"member_id": ada["id"], "destination_id": 1, "reason": "nope"},
    )
    client.post(f"/trips/{trip_id}/approvals", json={"member_id": ada["id"]})
    client.post(f"/members/{ada['id']}/ratings", json={"destination_id": 1, "value": "interested"})
    client.post(f"/trips/{trip_id}/conflicts/detect")
    client.post(
        f"/trips/{trip_id}/revisions",
        json={"member_id": ada["id"], "change_type": "condition_changed", "description": "relaxed"},
    )
    return trip_id, ada["id"], ben["id"]


def test_bootstrap_aggregates_everything(client):
    trip_id, ada, ben = setup(client)

    response = client.get(f"/trips/{trip_id}/bootstrap")
    assert response.status_code == 200
    data = response.json()

    assert data["trip"]["id"] == trip_id
    assert [m["name"] for m in data["members"]] == ["Ada", "Ben"]

    profiles = {p["member_id"]: p for p in data["profiles"]}
    assert profiles[ada]["budget_max"] == 5000
    assert profiles[ben]["budget_max"] == 500

    assert len(data["conditions"]) == 1
    assert data["conditions"][0]["status"] == "fixed"

    assert data["approvals"]["approved_member_ids"] == [ada]
    assert data["approvals"]["pending_member_ids"] == [ben]
    assert data["approvals"]["fully_approved"] is False

    assert len(data["vetoes"]) == 1
    assert len(data["ratings"]) == 1
    assert len(data["conflicts"]) >= 1
    assert all(c["trip_id"] == trip_id for c in data["conflicts"])
    assert len(data["revisions"]) == 1
    assert data["revisions"][0]["change_type"] == "condition_changed"
    assert data["plan"]["items"] == []


def test_bootstrap_unknown_trip_is_404(client):
    assert client.get("/trips/999/bootstrap").status_code == 404


def test_bootstrap_includes_generated_plan(client):
    trip_id, _ada, _ben = setup(client)
    client.patch(f"/trips/{trip_id}", json={"selected_destination_id": 1})
    assert client.post(f"/trips/{trip_id}/plan/generate").status_code == 200

    data = client.get(f"/trips/{trip_id}/bootstrap").json()
    assert len(data["plan"]["items"]) == 1
    assert data["plan"]["items"][0]["activity_id"] == 1


def test_bootstrap_tracks_approval_completion(client):
    trip_id, ada, ben = setup(client)
    client.post(f"/trips/{trip_id}/approvals", json={"member_id": ben})

    data = client.get(f"/trips/{trip_id}/bootstrap").json()
    assert data["approvals"]["fully_approved"] is True
    assert data["approvals"]["pending_member_ids"] == []


def test_bootstrap_without_members_is_safe(client):
    trip_id = client.post("/trips", json={"name": "Empty", "days": 1}).json()["id"]

    response = client.get(f"/trips/{trip_id}/bootstrap")
    assert response.status_code == 200
    data = response.json()
    assert data["members"] == []
    assert data["profiles"] == []
    assert data["approvals"]["fully_approved"] is False
    assert data["vetoes"] == []
    assert data["ratings"] == []
