def setup(client):
    trip = client.post("/trips", json={"name": "Trip", "days": 2}).json()
    trip_id = trip["id"]
    client.post(f"/trips/{trip_id}/members", json={"name": "Ada"})
    client.patch(f"/trips/{trip_id}", json={"selected_destination_id": 1})
    return trip_id


def test_generate_then_clear(client):
    trip_id = setup(client)
    generated = client.post(f"/trips/{trip_id}/plan/generate")
    assert generated.status_code == 200
    assert len(generated.json()["items"]) == 1

    assert client.delete(f"/trips/{trip_id}/plan").status_code == 204
    assert client.get(f"/trips/{trip_id}/plan").json()["items"] == []


def test_clear_without_a_plan_is_fine(client):
    trip_id = setup(client)
    assert client.delete(f"/trips/{trip_id}/plan").status_code == 204
    assert client.get(f"/trips/{trip_id}/plan").json()["items"] == []


def test_generate_needs_a_destination(client):
    trip_id = client.post("/trips", json={"name": "Nowhere", "days": 1}).json()["id"]
    assert client.post(f"/trips/{trip_id}/plan/generate").status_code == 400


def test_clear_unknown_trip_is_404(client):
    assert client.delete("/trips/999/plan").status_code == 404


def test_plan_items_survive_a_bootstrap_read(client):
    trip_id = setup(client)
    client.post(f"/trips/{trip_id}/plan/generate")
    data = client.get(f"/trips/{trip_id}/bootstrap").json()
    assert len(data["plan"]["items"]) == 1


def test_a_locked_item_survives_a_rebuild(client):
    trip_id = setup(client)
    item = client.post(f"/trips/{trip_id}/plan/generate").json()["items"][0]

    client.patch(
        f"/plan-items/{item['id']}", json={"locked": True, "day_index": 1, "start_minute": 600}
    )

    rebuilt = client.post(f"/trips/{trip_id}/plan/generate").json()
    kept = [i for i in rebuilt["items"] if i["id"] == item["id"]]

    assert kept, "the locked row was thrown away by the rebuild"
    assert kept[0]["day_index"] == 1
    assert kept[0]["start_minute"] == 600
    assert kept[0]["locked"] is True


def test_moving_an_item_to_another_day(client):
    trip_id = setup(client)
    item = client.post(f"/trips/{trip_id}/plan/generate").json()["items"][0]

    moved = client.patch(f"/plan-items/{item['id']}", json={"day_index": 1, "start_minute": 840})
    assert moved.status_code == 200
    assert moved.json()["day_index"] == 1
    assert moved.json()["start_minute"] == 840

    reread = client.get(f"/trips/{trip_id}/plan").json()["items"]
    assert reread[0]["day_index"] == 1
