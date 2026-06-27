# FocusAway

<p align="center">
  <b>English</b> ·
  <a href="README.ko.md">한국어</a>
</p>
<br />

FocusAway is a small OpenAI-compatible middleware for local or small-group LLM service operation.

It sits between end-user frontends and one upstream OpenAI-compatible backend:

frontend -> FocusAway -> upstream OpenAI-compatible backend

The upstream backend runs the models. FocusAway handles user accounts, per-user API keys, model access policy, quota charging, and a browser-based control panel.

<a href='https://ko-fi.com/I2I41WXL3D' target='_blank'><img height='36' style='border:0px;height:36px;' src='https://storage.ko-fi.com/cdn/kofi6.png?v=6' border='0' alt='Buy Me a Coffee at ko-fi.com' /></a>

## Features

- OpenAI-compatible user-facing API.
- Configurable OpenAI-compatible upstream backend.
- Browser web panel for login, signup, dashboard, and administration.
- First registered account becomes the administrator.
- Username-based accounts using lowercase letters and digits.
- Per-user middleware API key issuance.
- SQLite database for users, sessions, tiers, model policies, quota ledger, and usage history.
- Tier-based model access and tier-specific weekly recharge amounts.
- Admin-only model policy.
- Manual upstream model refresh.
- Per-model request cost rounded to two decimal places.
- Weekly quota reset every Monday 00:00 in the configured timezone.
- Bonus quota grants for all users or a specific username.
- Dashboard model cards with model metadata, required tier, copy button, and live 24h call chart.
- Upstream API key encryption in `focusaway-config.json`.
- Cross-platform Python server core.
- `tkinter` desktop launcher for local convenience.

## Files

- `app.py`: server entrypoint.
- `launcher.py`: local desktop launcher.
- `FocusAway.command`: macOS launcher helper.
- `FocusAway.sh`: Linux/macOS shell launcher helper.
- `FocusAway.bat`: Windows launcher helper.
- `focusaway-config.example.json`: example configuration.
- `focusaway/`: application package.
- `focusaway/config.py`: config load/save and encrypted upstream key handling.
- `focusaway/db.py`: SQLite schema, migrations, and data access.
- `focusaway/server.py`: web panel, API routes, auth, quota, proxying, and rendering.
- `focusaway/upstream.py`: upstream HTTP client.
- `focusaway/secret.py`: upstream API key encryption helpers.

## Requirements

- Python 3.10 or newer is recommended.
- No third-party Python package is required for the server core.
- The launcher uses Python's bundled `tkinter`; some Linux distributions require installing Tk separately.
- An upstream OpenAI-compatible backend is required for actual model inference.

## Quick Start For Administrators

1. Start your upstream OpenAI-compatible backend.

2. Launch FocusAway.

```bash
python3 launcher.py
```

Or run the server directly:

```bash
python3 app.py
```

3. In the launcher, configure:

- `Host`: usually `127.0.0.1` for local-only use.
- `Port`: default `8787`.
- `Upstream Base URL`: backend root URL, for example `http://127.0.0.1:11434`.
- `Upstream API Prefix`: usually `/v1`.
- `Upstream Models Path`: usually `/v1/models`.
- `Upstream API Key`: the backend key created on the upstream side, if required.
- `Upstream Auth Mode`: usually `bearer`, `header`, `x-api-key`, or `none`.

4. Open the web panel.

```text
http://127.0.0.1:8787
```

5. Create the first account. The first registered account becomes the administrator.

6. Open the admin panel and refresh models from the backend.

7. Configure tiers, weekly quota amounts, per-model costs, model access requirements, and optional model metadata overrides.

8. Share the FocusAway API base URL and each user's own API key with users.

## Quick Start For Regular Users

1. Sign up or log in through the web panel address provided by the administrator.

2. Open the dashboard.

3. Check:

- your current tier
- remaining premium requests
- available model list
- model costs and required tiers
- your personal API key
- API base URL

4. In your frontend, use the FocusAway API base URL and your personal API key.

Typical API base URL:

```text
http://127.0.0.1:8787/v1
```

If your frontend appends `/v1` automatically, use:

```text
http://127.0.0.1:8787
```

Authentication header:

```http
Authorization: Bearer fk_...
```

Do not use the upstream backend API key in your frontend. Use only your FocusAway-issued key.

## Administrator Guide

### Model Management

Use `Admin Panel -> Refresh Models From Backend` after changing models in the upstream backend.

When models disappear upstream, they are removed from FocusAway policy storage on refresh. Existing model policy values are preserved for models that still exist.

For each model, the admin can configure:

- request cost
- admin-only access or minimum required tier
- custom model kind: server default, `LLM`, or `VLM`
- custom context window
- custom output-token limit

If a custom output-token limit is set, FocusAway clamps request-side output caps down to that limit before proxying to the upstream backend.

### Tier Management

FocusAway includes a base member tier, initially named `Tier 0`.

The admin can:

- create tiers
- rename tiers
- reorder tiers
- delete non-base tiers
- set weekly recharge amount per tier
- assign users to tiers

The fixed admin presentation tier is separate from normal DB-managed member tiers.

### Quota Management

Weekly balance resets every Monday 00:00 in the configured timezone. This is a reset to the tier amount, not an additive top-up.

Bonus balance is separate and survives weekly reset.

When charging a request, FocusAway consumes weekly balance first, then bonus balance.

Admins are never charged.

### User Management

The admin can:

- suspend users
- delete users
- change a user's tier
- grant bonus quota to all users
- grant bonus quota to one user by login username
- see each user's last seen IP

### Signup Control

Signup can be opened or closed from service settings.

When signup is closed, the signup button is hidden and direct `/signup` access shows a closed-state message.

### Auto Promotion

Automatic tier promotion can be configured when at least one non-base regular tier exists.

Supported conditions:

- elapsed time after signup
- cumulative premium request usage after signup

If multiple enabled conditions are configured, current behavior is OR: satisfying any selected condition promotes the user.

## User API Guide

Supported core routes:

- `GET /health`
- `GET /v1/models`
- `POST /v1/chat/completions`
- `POST /v1/completions`
- `POST /v1/responses`
- `POST /v1/embeddings`
- `POST /v1/images/generations`

`GET /v1/models` returns only models accessible to the authenticated API user.

Billable POST routes deduct the model's configured per-request cost before proxying.

Streaming is supported for compatible upstreams and clients, but OpenAI-compatible backends can differ in event details. If model listing works but chat fails, test both stream and non-stream modes.

## Configuration

The launcher writes `focusaway-config.json` in the project root.

Example:

```json
{
  "host": "127.0.0.1",
  "port": 8787,
  "timezone": "Asia/Seoul",
  "database_path": "focusaway.db",
  "max_request_bytes": 10485760,
  "cors_allowed_origins": "http://127.0.0.1:3000,http://localhost:3000",
  "upstream_base_url": "http://127.0.0.1:11434",
  "upstream_api_prefix": "/v1",
  "upstream_models_path": "/v1/models",
  "upstream_api_key": "enc:v1:...",
  "upstream_auth_mode": "bearer",
  "upstream_auth_header": "Authorization",
  "upstream_auth_scheme": "Bearer",
  "upstream_extra_headers": "",
  "upstream_timeout_seconds": 300,
  "session_hours": 168,
  "app_name": "FocusAway",
  "operator_name": "FocusAway Operator",
  "contact_email": "operator@example.com",
  "contact_address": ""
}
```

Important fields:

- `cors_allowed_origins`: restrict this for public deployments.
- `upstream_base_url`: upstream backend root URL.
- `upstream_api_prefix`: prefix for proxied API calls.
- `upstream_models_path`: model-list endpoint.
- `upstream_auth_mode`: `bearer`, `header`, `x-api-key`, or `none`.
- `upstream_auth_header`: auth header name.
- `upstream_auth_scheme`: bearer-like auth scheme.
- `upstream_extra_headers`: JSON object string for additional static headers.

## Upstream API Key Encryption

`upstream_api_key` is saved encrypted in `focusaway-config.json`.

FocusAway chooses the encryption master key as follows:

1. Use `FOCUSAWAY_SECRET_KEY` if set.
2. Otherwise, generate and use a local `focusaway-secret.key` file beside the config.

Existing plaintext upstream API keys are automatically migrated to encrypted form on config load.

When moving an existing installation to another machine, move the encrypted config and the matching `focusaway-secret.key`, or keep the same `FOCUSAWAY_SECRET_KEY`.

If the master key is lost, the encrypted upstream API key cannot be recovered. Re-enter the upstream API key in the launcher.

## Security Notes

- Passwords are not stored in plaintext.
- Session cookies are `HttpOnly` and `SameSite=Lax`.
- Session-authenticated POST actions use CSRF protection.
- Login attempts are rate-limited in memory by IP.
- Suspended users are blocked from web and API auth.
- Upstream error bodies are not directly returned to users.
- Config, SQLite DB, and local secret key files are chmod-attempted to `0600`.
- `X-Forwarded-*` headers are trusted by current code. Expose FocusAway only behind a trusted proxy or tunnel if relying on those headers.
- For public deployment, restrict `cors_allowed_origins` to trusted frontend origins.
- A fresh empty database makes the first registered account admin. Create the admin account before exposing the service publicly.

## Platform Notes

- macOS: use `FocusAway.command` or `python3 launcher.py`.
- Linux: use `python3 launcher.py` if Tk is available, or `python3 app.py` for server-only operation.
- Windows: use `FocusAway.bat` or `py launcher.py`.

## Troubleshooting

- Launcher does not open: run `python3 launcher.py` from a terminal and check `focusaway-launcher.log`.
- Server does not start: check `focusaway-server.log`.
- Frontend cannot fetch models: verify API base URL, `/v1` handling, CORS origin, and user API key.
- Models are missing: refresh models in the admin panel and check assistant-model filtering.
- Chat fails while models load: test stream and non-stream modes; backend compatibility may differ.
- Encrypted upstream key fails to load: verify `FOCUSAWAY_SECRET_KEY` or `focusaway-secret.key`.

## Deployment Copy

A clean distribution copy should not include:

- `focusaway.db`
- `focusaway-config.json`
- `focusaway-secret.key`
- logs
- backup databases
- `__pycache__`
- `.git`

Use `focusaway-config.example.json` as the starting config for new deployments.
