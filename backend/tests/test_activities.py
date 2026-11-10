def setup(client):
    trip = client.post("/trips", json={"name": "Trip", "days": 2}).json()
    trip_id = trip["id"]
    member = client.post(f"/trips/{trip_id}/members", json={"name": "Ada"}).json()
    client.patch(f"/trips/{trip_id}", json={"selected_destination_id": 1})
    return trip_id, member["id"]


def test_activities_are_scored_per_member(client):
    trip_id, member_id = setup(client)

    rows = client.get(f"/trips/{trip_id}/activities").json()

    assert len(rows) == 1
    row = rows[0]
    assert row["activity"]["id"] == 1
    assert [s["member_id"] for s in row["member_scores"]] == [member_id]
    assert 0 <= row["member_scores"][0]["score"] <= 100
    assert row["rejected_by"] == []


def test_preferences_and_ratings_move_the_score(client):
    trip_id, member_id = setup(client)

    plain = client.get(f"/trips/{trip_id}/activities").json()[0]["member_scores"][0]["score"]

    client.put(f"/members/{member_id}/profile", json={"activities": ["beach"]})
    matched = client.get(f"/trips/{trip_id}/activities").json()[0]["member_scores"][0]["score"]
    assert matched > plain

    client.post(f"/members/{member_id}/ratings", json={"activity_id": 1, "value": "not_interested"})
    disliked = client.get(f"/trips/{trip_id}/activities").json()[0]
    assert disliked["member_scores"][0]["score"] < matched
    assert disliked["rejected_by"] == [member_id]


def test_activities_need_a_destination(client):
    trip_id = client.post("/trips", json={"name": "Nowhere", "days": 1}).json()["id"]
    assert client.get(f"/trips/{trip_id}/activities").status_code == 400


def test_activities_unknown_trip_is_404(client):
    assert client.get("/trips/999/activities").status_code == 404


def test_a_rejected_activity_is_left_out_of_the_plan(client):
    trip_id, member_id = setup(client)

    assert len(client.post(f"/trips/{trip_id}/plan/generate").json()["items"]) == 1

    client.post(f"/members/{member_id}/ratings", json={"activity_id": 1, "value": "not_interested"})
    rebuilt = client.post(f"/trips/{trip_id}/plan/generate").json()

    assert rebuilt["items"] == []
    assert rebuilt["unscheduled"] == []


def test_bootstrap_lists_suggestions(client):
    trip_id, member_id = setup(client)

    client.post(
        f"/trips/{trip_id}/requests",
        json={"member_id": member_id, "activity_id": 1, "text": "something outdoors"},
    )

    data = client.get(f"/trips/{trip_id}/bootstrap").json()
    assert len(data["requests"]) == 1
    assert data["requests"][0]["text"] == "something outdoors"
    assert data["requests"][0]["activity_id"] == 1


def two_members(client):
    trip = client.post("/trips", json={"name": "Two", "days": 2}).json()
    trip_id = trip["id"]
    ada = client.post(f"/trips/{trip_id}/members", json={"name": "Ada"}).json()
    ben = client.post(f"/trips/{trip_id}/members", json={"name": "Ben"}).json()
    client.patch(f"/trips/{trip_id}", json={"selected_destination_id": 1})
    return trip_id, ada["id"], ben["id"]


def test_like_and_dislike_produce_an_activity_conflict(client):
    trip_id, ada, ben = two_members(client)
    client.put(f"/members/{ada}/profile", json={"likes": ["beach"]})
    client.put(f"/members/{ben}/profile", json={"dislikes": ["beach"]})

    row = client.get(f"/trips/{trip_id}/activities").json()[0]

    kinds = [c["kind"] for c in row["conflicts"]]
    assert "activity" in kinds
    conflict = next(c for c in row["conflicts"] if c["kind"] == "activity")
    assert sorted(conflict["member_ids"]) == sorted([ada, ben])


def test_fixed_condition_shows_up_as_an_activity_conflict(client):
    trip_id, ada, ben = two_members(client)
    client.post(
        f"/trips/{trip_id}/conditions",
        json={"member_id": ben, "text": "No beach days", "type": "activity", "status": "fixed"},
    )

    row = client.get(f"/trips/{trip_id}/activities").json()[0]

    kinds = [c["kind"] for c in row["conflicts"]]
    assert "fixed_condition" in kinds
    assert next(c for c in row["conflicts"] if c["kind"] == "fixed_condition")["member_ids"] == [ben]


def test_agreeing_members_have_no_activity_conflict(client):
    trip_id, ada, ben = two_members(client)
    client.put(f"/members/{ada}/profile", json={"activities": ["beach"]})
    client.put(f"/members/{ben}/profile", json={"activities": ["beach"]})

    row = client.get(f"/trips/{trip_id}/activities").json()[0]

    assert row["conflicts"] == []
