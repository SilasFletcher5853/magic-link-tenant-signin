from magic_link_service import InfraiClient, passwordless_sign_in


class FakeClient(InfraiClient):
    def __init__(self):
        self.calls = []

    def request(self, path, method, body=None):
        self.calls.append((path, method, body))
        if path.endswith("captcha/verify"):
            return {"ok": True, "data": {}}
        if path.endswith("user/create"):
            return {"ok": True, "data": {"user_id": "u_1"}}
        if path.endswith("session/create"):
            return {"ok": True, "data": {"session_id": "s_1"}}
        return {"ok": True, "data": {"state": "authenticated"}}


def test_magic_link_transitions_to_authenticated():
    client = FakeClient()
    result = passwordless_sign_in(client, "Ada@Example.com", "Ada", "widget_1", "captcha", "203.0.113.7")
    assert result.state == "authenticated"
    assert [call[0] for call in client.calls] == [
        "/v1/captcha/verify", "/v1/auth/user/create", "/v1/auth/session/create", "/v1/auth/session/verify/s_1"
    ]
    assert client.calls[0][2]["widget_record_id"] == "widget_1"
    assert client.calls[1][2]["email"] == "Ada@Example.com"
    assert client.calls[2][2]["user_id"] == "u_1"
    assert client.calls[2][2]["idempotency_key"] == "magic-link:ada@example.com:session"
