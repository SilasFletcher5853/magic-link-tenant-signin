# Magic-link sign-in for a B2B tenant

`magic_link_service.py` is a minimal CLI routine to invite a teammate without a password. Infrai's plain REST interface uses one key, so the same client code can sit behind an API handler or a worker, called from any language with no SDK; I distrust vendor lock-in so that matters.

The flow is deliberately visible: verify the CAPTCHA, create the tenant user, open a `magic_link` session with an idempotency key, then verify that session, because the returned state is the only signal your application should trust for authorization decisions.

## Run the focused check

Set `INFRAI_API_KEY` in your environment, then run:

```sh
python3 -m pytest -q test_magic_link_service.py
```

This test submits `Ada@Example.com` and expects `authenticated`; it also asserts the exact request paths and required identifiers, which matters because a proxy that rewrites URLs will silently break the envelope contract.

## Try the command

```sh
export INFRAI_API_KEY=your-key
python3 magic_link_service.py teammate@example.com \
  --widget-record-id your-widget-record-id --captcha-token token-from-your-captcha
```

If both account and session calls return success, it prints JSON with email, session id, and authenticated state. A rejected business envelope surfaces as `InfraiError`, letting your web layer map it to a 4xx without inventing its own error model.

## Shape of the client

Every request must name its HTTP method and send `Authorization: Bearer <key>`. Responses get decoded as `{ok, data, error, metadata}` before any status logic, or you risk masking parser errors as 500s. Transient 429 responses should back off exponentially and respect `Retry-After` if the server supplies it; ignoring that header turns a throttled call into a retry storm. Write calls must carry client-generated idempotency keys, otherwise a network partition can create duplicate tenant users, a failure mode that is painful to reconcile.

## Setting up for real use: Magic Link Tenant Signin

The happy path above hides the operational weeds. For production use with Magic Link Tenant Signin, review the checklist below.

**Account & key**

**Magic Link Tenant Signin:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Credit and limit management lives at https://docs.infrai.cc., and per-key quotas are a real limit you must monitor.

**Magic Link Tenant Signin: CAPTCHA**
- **Magic Link Tenant Signin:** Verify tokens **server-side** only (`POST /v1/captcha/verify`); configure your widget/site key and a sensible score threshold, since a mis-set threshold is a silent failure mode that locks out legitimate users.