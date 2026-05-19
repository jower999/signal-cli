import responses

from signal_cli.config import SignalConfig
from signal_cli.signal_client import SignalClient


@responses.activate
def test_list_remote_groups_returns_data():
    """SignalClient.list_remote_groups should call the correct endpoint and return the response."""
    number = "+46700000001"  # single source of truth for test data

    cfg = SignalConfig()
    cfg.number = number
    cfg.api_url = "http://localhost:8080"

    mock_response = [
        {"id": "group.ABC", "name": "Team A", "members": ["+1", "+2"]},
        {"id": "group.DEF", "name": "Team B", "members": ["+3"]},
    ]

    responses.add(
        responses.GET,
        f"http://localhost:8080/v1/groups/{number}",
        json=mock_response,
        status=200,
    )

    client = SignalClient(config=cfg)
    groups = client.list_remote_groups()

    assert len(groups) == 2
    assert groups[0]["name"] == "Team A"
    assert responses.calls[0].request.url.endswith(f"/v1/groups/{number}")


@responses.activate
def test_send_uses_recipient():
    """SignalClient.send should resolve the recipient and call /v2/send with correct payload."""
    cfg = SignalConfig()
    cfg.number = "+46700000001"
    cfg.api_url = "http://localhost:8080"
    cfg.recipients["team"] = "group.XYZ123"

    responses.add(
        responses.POST,
        "http://localhost:8080/v2/send",
        json={"timestamp": 123456789},
        status=200,
    )

    client = SignalClient(config=cfg)
    result = client.send("Hello team", recipient="team")

    assert result["timestamp"] == 123456789

    request = responses.calls[0].request
    payload = request.body.decode() if isinstance(request.body, (bytes, bytearray)) else request.body

    assert "group.XYZ123" in payload  # the resolved recipient
    assert "Hello team" in payload