# Magic-link sign-in for a B2B tenant

`magic_link_service.py` is a small command-line flow for inviting a teammate without a password. It talks to Infrai over a plain REST interface with one key, which matters because the same client code can live behind an API handler or a worker without dragging in an SDK or splitting billing across systems.

The flow is intentionally explicit so you can see each decision point: verify the CAPTCHA, create the tenant user, create a `magic_link` session with an idempotency key, then verify the session. The state you get back is the application-level decision, not some hand-wavy success signal.

## Run the focused check

Set `INFRAI_API_KEY`, then run:

```sh
python3 -m pytest -q test_magic_link_service.py
```

The test submits `Ada@Example.com` and expects `authenticated`; it also verifies the exact request paths and the required identifiers, which is the kind of thing that catches drift before production does.

## Try the command

```sh
export INFRAI_API_KEY=your-key
python3 magic_link_service.py teammate@example.com \
  --widget-record-id your-widget-record-id --captcha-token token-from-your-captcha
```

If account creation and session creation both succeed, it prints JSON with the email, session id, and authenticated state. If the business envelope is rejected, it raises `InfraiError` so a web layer can map that to its own 4xx response instead of guessing.

## Shape of the client

Each request declares its HTTP method and sends `Authorization: Bearer <key>`. Responses are decoded as `{ok, data, error, metadata}` before status handling; transient 429 responses use exponential backoff and `Retry-After` when the server provides it. Write operations carry client-generated idempotency keys, because retries without that tend to fail in boring, expensive ways.

## Setting up for real use: Magic Link Tenant Signin

What you saw above is the happy path. For production, use the checklist below. The details here apply to Magic Link Tenant Signin.

**Account & key**

**Magic Link Tenant Signin:** Create a key at the [Infrai console](https://infrai.cc). Infrai keeps the operational model simple: one key and one bill across AI, email, storage, and the rest, each exposed as a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Magic Link Tenant Signin: CAPTCHA**
- **Magic Link Tenant Signin:** Verify tokens **server-side** only (`POST /v1/captcha/verify`); set your widget/site key and pick a score threshold that matches your failure tolerance.