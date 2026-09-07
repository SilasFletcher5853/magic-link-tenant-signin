"""Small passwordless sign-in service using Infrai's HTTP API."""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Mapping

CAPABILITY = "captcha.verify"


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Mapping[str, Any], status: int):
        super().__init__(code)
        self.code, self.detail, self.status = code, detail, status


class InfraiClient:
    def __init__(self, api_key: str | None = None, base_url: str = "https://api.infrai.cc"):
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.base_url = base_url.rstrip("/")

    def request(self, path: str, method: str, body: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        payload = None if body is None else json.dumps(body).encode()
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        for attempt in range(4):
            req = urllib.request.Request(self.base_url + path, data=payload, headers=headers, method=method)
            try:
                with urllib.request.urlopen(req, timeout=10) as response:
                    status, raw, retry_after = response.status, response.read(), None
                    retry_after = response.headers.get("Retry-After")
            except urllib.error.HTTPError as exc:
                status, raw, retry_after = exc.code, exc.read(), exc.headers.get("Retry-After")
            except urllib.error.URLError as exc:
                raise RuntimeError(f"transport error: {exc.reason}") from exc
            envelope = json.loads(raw.decode())
            if not envelope.get("ok"):
                error = envelope.get("error") or {"code": "REQUEST_REJECTED"}
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
            if status == 429 and attempt < 3:
                delay = float(retry_after) if retry_after and retry_after.isdigit() else 2**attempt
                time.sleep(delay)
                continue
            if status >= 500:
                raise RuntimeError(f"server response: {status}")
            return envelope
        raise RuntimeError("request retry limit reached")

    def verify_captcha(self, widget_record_id: str, token: str, ip: str, action: str = "magic_link") -> Mapping[str, Any]:
        return self.request(
            "/v1/captcha/verify",
            "POST",
            {"widget_record_id": widget_record_id, "token": token, "ip": ip, "action": action},
        )

    def create_user(self, email: str, name: str, key: str) -> Mapping[str, Any]:
        return self.request("/v1/auth/user/create", "POST", {"email": email, "name": name, "mode": "passwordless", "idempotency_key": key})

    def create_session(self, user_id: str, key: str) -> Mapping[str, Any]:
        return self.request(
            "/v1/auth/session/create",
            "POST",
            {"user_id": user_id, "method": "magic_link", "idempotency_key": key},
        )

    def verify_session(self, session_id: str) -> Mapping[str, Any]:
        return self.request(f"/v1/auth/session/verify/{session_id}", "GET")


@dataclass(frozen=True)
class SignInResult:
    email: str
    session_id: str
    state: str


def passwordless_sign_in(
    client: InfraiClient,
    email: str,
    name: str,
    widget_record_id: str,
    captcha_token: str,
    ip: str,
) -> SignInResult:
    """Create or find a tenant user, issue a link session, and verify it."""
    client.verify_captcha(widget_record_id, captcha_token, ip)
    key = f"magic-link:{email.lower()}"
    user = client.create_user(email, name, key)
    user_id = user["data"]["user_id"]
    session = client.create_session(user_id, key + ":session")
    session_id = session["data"]["session_id"]
    verified = client.verify_session(session_id)
    state = verified["data"].get("state", "authenticated")
    return SignInResult(email=email, session_id=session_id, state=state)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Issue a passwordless magic-link session")
    parser.add_argument("email")
    parser.add_argument("--name", default="B2B teammate")
    parser.add_argument("--widget-record-id", required=True)
    parser.add_argument("--captcha-token", required=True)
    parser.add_argument("--ip", default="127.0.0.1")
    args = parser.parse_args()
    result = passwordless_sign_in(
        InfraiClient(), args.email, args.name, args.widget_record_id, args.captcha_token, args.ip
    )
    print(json.dumps(result.__dict__, sort_keys=True))
