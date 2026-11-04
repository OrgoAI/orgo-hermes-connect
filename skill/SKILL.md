---
name: orgo-hermes-connect
description: "Use when connecting Hermes Desktop to an agent on Orgo."
version: 0.1.0
author: Orgo
license: MIT
metadata:
  hermes:
    tags: [Orgo, Hermes-Desktop, Remote-Gateway, Public-URL, Dashboard-Auth]
    homepage: https://github.com/OrgoAI/orgo-hermes-connect
---

# orgo-hermes-connect

Gives a Hermes agent running on an Orgo cloud computer a public HTTPS URL
(`https://<label>.orgo.dev`) that the person can paste into **Hermes Desktop ->
Settings -> Gateways -> Remote gateway**. Logging in is required (Nous Portal by default).

## When to use
- The user says something like "connect my Hermes desktop app to you", "give me a gateway
  URL", "I want to use you from my laptop", or "remote gateway".
- You're running on an Orgo computer. `/proc/cmdline` contains `orgo.` or
  `~/.hermes/config.yaml` references `orgo.ai/mcp/computers/`.

## Procedure
1. Install it if it's missing:
   `curl -fsSL https://raw.githubusercontent.com/OrgoAI/orgo-hermes-connect/main/install.sh | bash`
2. Run `orgo-hermes-connect up --non-interactive` first. If it reports a missing approval,
   rerun **without** `--non-interactive` in the background or in tmux (it blocks while
   polling), read its output, and send the user each approval link:
   - an Orgo device approval link (only if there's no working `ORGO_API_KEY`)
   - a Nous Portal device code (only if this Hermes install isn't signed in to Nous)
   Never ask the user to paste a key into chat. Both flows are device approvals.
3. When it finishes, give the user the printed **gateway URL** and these steps:
   Hermes Desktop -> Settings -> Gateways -> Remote gateway -> paste URL -> Sign in
   (with the Nous account that approved step 2).
4. Verify: `orgo-hermes-connect status` exits 0 when the public URL answers and
   `auth_required` is true with a provider listed.

## Commands
| Command | Effect |
|---|---|
| `orgo-hermes-connect up` | create/reuse the URL, configure login, start `hermes serve` on :9119 (idempotent) |
| `orgo-hermes-connect status [--json]` | URL, backend and auth state; exit 1 if unhealthy |
| `orgo-hermes-connect url` | print just the URL |
| `orgo-hermes-connect down [--keep-url]` | stop the backend, delete the URL |

Options for `up`: `--auth nous|password|oidc`, `--label NAME`, `--port N`,
`--computer-id UUID`, `--oidc-issuer/--oidc-client-id`, `--rotate-password`, `--reregister`.

## Pitfalls
- `--auth password` is a single shared credential. Hermes recommends it only for trusted
  networks. Default to `nous` for a public URL.
- Never add an Orgo visitor password to the URL. It returns 401 for the desktop app's
  API/WebSocket calls. The tool removes one if it finds it.
- Orgo refuses ports 22, 3389, 5900-5999, 6080-6099, 8080 and 9000.
- On Orgo's Hermes template, port 8642 is the separate OpenAI-compatible API server. The
  desktop app connects to `hermes serve` (9119), not 8642.
- If chat fails after sign-in, check desktop.log for the `/api/ws` close code: 4401 means
  the ticket auth failed, 4403 means a Host header or peer mismatch.
- Revoke the Nous login client at https://portal.nousresearch.com/local-dashboards
