# orgo-hermes-connect

**Connect Hermes Desktop to your Hermes agent on Orgo with one command.**

Run this on an [Orgo](https://orgo.ai) cloud computer that runs [Hermes Agent](https://hermes-agent.nousresearch.com):

```bash
curl -fsSL https://raw.githubusercontent.com/OrgoAI/orgo-hermes-connect/main/install.sh | bash
orgo-hermes-connect up
```

You get back a URL like `https://my-agent-3f2a.orgo.dev`. Paste it into
**Hermes Desktop → Settings → Gateways → Remote gateway** and sign in. Your desktop app is now
talking to the agent on its cloud computer: same sessions, memory, skills and tools.

```
  orgo-hermes-connect 0.1.0

  ✓ Orgo API key works
  ✓ Computer: Hermes Agent (7f388be6-…)
  ✓ Created public URL https://doug-hermes.orgo.dev -> :9119
  ✓ Registered Nous Portal login for this URL
  ✓ Backend started via supervisor on 0.0.0.0:9119
  ✓ Login required (providers: nous)

  ────────────────────────────────────────────────────────────
  Hermes Desktop gateway URL:  https://doug-hermes.orgo.dev
  ────────────────────────────────────────────────────────────
```

## Just tell your agent

This repo ships a Hermes skill. Give your agent the link:

> Set me up with https://github.com/OrgoAI/orgo-hermes-connect so I can connect my Hermes desktop app to you.

The agent installs the tool and runs it. It sends you up to two approval links, one for Orgo
and one for Nous Portal, and then hands you the URL. You never paste an API key into chat.

## What it does

1. **Orgo API key**: uses `ORGO_API_KEY` from `~/.hermes/.env`. If there isn't one, it runs
   Orgo's device approval: you open a link and click approve, and the key goes straight to
   `~/.hermes/.env`.
2. **Finds this computer** from Orgo's Hermes template (the `orgo.ai/mcp/computers/<id>` MCP
   entry in `config.yaml`). Otherwise use `--computer-id` or `ORGO_COMPUTER_ID`.
3. **Public URL**: creates (or reuses) `https://<label>.orgo.dev` → port 9119 through
   Orgo's public URL API.
4. **Login**: Hermes refuses to serve on a public address without a login provider. By default
   this registers a **Nous Portal** OAuth login for the URL (`hermes dashboard register`), so only
   your Nous account can sign in.
5. **Backend**: runs `hermes serve --host 0.0.0.0 --port 9119` under supervisor (Orgo VMs) or a
   systemd user service, so it survives restarts and reboots.
6. **Verifies** that the public URL answers, reports `auth_required: true`, and has a login
   provider registered.

Re-running `up` is safe. It reuses the URL and login, and **it never restarts a healthy
backend unless a setting it depends on changed.** If it finds a `hermes-serve` service it didn't
create, it uses that service as-is.

## Commands

| Command | |
|---|---|
| `orgo-hermes-connect up` | Set up or repair everything, then print the URL |
| `orgo-hermes-connect status [--json]` | URL, backend and login state; exits 1 if unhealthy |
| `orgo-hermes-connect url` | Print just the URL |
| `orgo-hermes-connect down [--keep-url]` | Stop the backend and delete the URL |

`up` options:

| Option | Default | |
|---|---|---|
| `--auth nous\|password\|oidc` | `nous` | Login provider (see below) |
| `--label NAME` | `<computer-name>-<4 hex>` | URL becomes `https://NAME.orgo.dev` |
| `--port N` | `9119` | Local port for `hermes serve` |
| `--computer-id UUID` | auto | Orgo computer id |
| `--non-interactive` | | Fail instead of waiting for approvals (for scripts and agents) |
| `--restart` | | Restart the backend even when nothing changed |
| `--force` | | Take over a `hermes-serve` service this tool didn't create |

## Login options

| `--auth` | Who can sign in | Use when |
|---|---|---|
| `nous` (default) | Your Nous Portal account | Recommended for a public URL |
| `oidc` | Users of your own OpenID Connect provider (Keycloak, Auth0, Okta, …) | Your team already has an identity provider. Pass `--oidc-issuer` and `--oidc-client-id`, and register `<url>/auth/callback` as the redirect URI |
| `password` | Anyone with a generated username and password | Quick tests only. Hermes recommends it for trusted networks, not the open internet |

## Requirements

- An Orgo **Linux** computer with public URLs enabled. This needs a paid plan or credits.
- Hermes Agent installed (Orgo's Hermes template ships it).
- Python 3.9+ and `curl`. The tool is a single stdlib-only Python file.

## Security notes

- `/api/status` stays public: it reports only the version and login providers. Every other
  endpoint and the chat WebSocket require a signed-in session.
- Don't put an Orgo **visitor password** on the URL. It blocks the desktop app's API and
  WebSocket calls. The tool removes one if it finds it, and Hermes' own login still protects
  the backend.
- Revoke the Nous login at <https://portal.nousresearch.com/local-dashboards>. Delete the URL
  with `orgo-hermes-connect down`.
- Secrets live only in `~/.hermes/.env` (mode 600). The tool never prints them, except the
  generated password in `--auth password` mode, which is shown once.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Desktop says *ready* but chat won't connect | Run `orgo-hermes-connect status`. Then check desktop.log for the `/api/ws` close code: **4401** means the sign-in ticket failed (sign in again), **4403** means a Host header or peer mismatch (use the exact URL) |
| `Public URLs are not enabled` | The account needs a paid plan or credits. Only Linux and Windows computers support public URLs |
| `Not signed in to Nous` with `--non-interactive` | Run without `--non-interactive` once and approve the Nous device code |
| Backend won't start | `supervisorctl tail hermes-serve stderr` |
| Port 8642 vs 9119 | 8642 is Hermes' OpenAI-compatible API server. The desktop app connects to `hermes serve` on **9119** |

## Making this the default on Orgo

The end goal is for every new agent on Orgo to get its URL automatically, with a
**"Sign in with Orgo"** login so no Nous approval is needed. See
[docs/out-of-the-box.md](docs/out-of-the-box.md) for the design.

## Development

```bash
python3 -m unittest discover -s tests -v
```

## License

MIT
