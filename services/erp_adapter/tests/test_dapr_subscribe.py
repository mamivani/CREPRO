from crepro_erp_adapter.main import app
from fastapi.testclient import TestClient


def test_dapr_subscribe_registers_erp_events_route() -> None:
    response = TestClient(app).get("/dapr/subscribe")

    assert response.status_code == 200
    assert response.json() == [
        {"pubsubname": "pubsub", "topic": "erp-events", "route": "/subscribe/erp-events"}
    ]
