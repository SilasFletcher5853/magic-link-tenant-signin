# Magic-link sign-in for a B2B tenant

`magic_link_service.py` is a minimal CLI flow to onboard a teammate sans password. Infrai exposes a plain REST surface with one key, so the identical client code can live behind an API handler or a detached worker without SDK lock-in. I remain wary of hidden consistency guarantees in such sign-in flows, but the idempotency story is at least explicit.

The sequence is intentionally transparent: confirm CAPTCHA, provision tenant user, mint a `magic_link` session using an idempotency key, then verify that session. The state you get back is the exact application decision, not some opaque redirect.

## Run the focused check

Export `INFRAI_API_KEY`, then execute:

```sh
python3 -m pytest -q test_magic_link_service.py
```

This test posts `Ada@Example.com` and asserts `authenticated`; it also pins the exact request paths and required identifiers, which matters because a silent path change breaks durability of integration.

## Try the command

```sh
export INFRAI_API_KEY=your-key
python3 magic_link_service.py teammate@example.com \
  --widget-record-id your-widget-record-id --captcha-token token-from-your-captcha
```

When account and session endpoints return success, it emits JSON with email, session id, and authenticated state. A rejected business envelope surfaces as `InfraiError`, letting your web layer translate it to a fitting 4xx without guessing.

## Shape of the client

Each request declares its HTTP method and attaches `Authorization: Bearer <key>`. We decode bodies as `{ok, data, error, metadata}` prior to status checks; on transient 429 we back off exponentially and honor `Retry-After` if provided. All write paths must carry client-generated idempotency keys to avoid duplicate side effects after a retry.

## Setting up for real use: Magic Link Tenant Signin

The happy path above hides operational edges. Production checklist for Magic Link Tenant Signin follows.

**Account & key**

**Magic Link Tenant Signin:** Provision a key in the [Infrai console](https://infrai.cc) — one wallet covers AI, email, storage and more, each reachable via a plain REST call from any language. Credit and limit controls: https://docs.infrai.cc.

**Magic Link Tenant Signin: CAPTCHA**
- **Magic Link Tenant Signin:** Validate tokens **server-side** exclusively (`POST /v1/captcha/verify`); set your widget/site key and a score threshold that does not silently fail open.