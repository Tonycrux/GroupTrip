def make_task(client):
    session = client.post("/sessions", json={"label": "Group A"}).json()
    return client.post(
        "/tasks",
        json={"session_id": session["id"], "variant": "comparison", "order_index": 1},
    ).json()


def test_a_task_links_to_its_trip(client):
    trip = client.post("/trips", json={"name": "Trip", "days": 1}).json()
    task = make_task(client)
    client.patch(f"/trips/{trip['id']}", json={"task_instance_id": task["id"]})

    linked = client.get(f"/tasks/{task['id']}/trip")
    assert linked.status_code == 200
    assert linked.json()["id"] == trip["id"]


def test_unknown_task_is_404(client):
    assert client.get("/tasks/999/trip").status_code == 404


def test_task_without_a_trip_is_404(client):
    task = make_task(client)
    assert client.get(f"/tasks/{task['id']}/trip").status_code == 404


def test_the_ui_variant_vocabulary_round_trips(client):
    task = client.post(
        "/tasks",
        json={
            "session_id": client.post("/sessions", json={"label": "B"}).json()["id"],
            "variant": "conflict_aware",
            "order_index": 2,
        },
    ).json()

    reread = client.get(f"/tasks/{task['id']}").json()
    assert reread["variant"] == "conflict_aware"
