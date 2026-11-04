# Making it the default: an out-of-the-box gateway URL for every Orgo agent

Today `orgo-hermes-connect up` takes one command and up to two approvals. The goal is
**zero**: every Hermes computer Orgo creates already has a URL, and its owner signs in
with their Orgo account.

## What's missing

Hermes refuses to serve on a public address without a login provider. It supports:

| Provider | Works with no setup? |
|---|---|
| Nous Portal OAuth | No. It needs a Nous account and one registration per computer |
| Username/password | Yes, but Hermes recommends it for trusted networks only |
| **Generic OIDC** (`plugins/dashboard_auth/self_hosted`) | **Yes, if Orgo is the OIDC provider** |

The OIDC plugin needs just two settings: `HERMES_DASHBOARD_OIDC_ISSUER` and
`HERMES_DASHBOARD_OIDC_CLIENT_ID`. It accepts a public client using authorization code +
PKCE (S256) and verifies the ID token against the issuer's `jwks_uri`.

## What Orgo already has

`https://www.orgo.ai/.well-known/oauth-authorization-server` already advertises:
- `authorization_endpoint`, `token_endpoint`
- `code_challenge_methods_supported: ["S256"]`
- `registration_endpoint` (dynamic client registration)

## What Orgo needs to add (the OIDC layer)

1. **`/.well-known/openid-configuration`** with `issuer`, `authorization_endpoint`,
   `token_endpoint`, and `jwks_uri`. `revocation_endpoint` is optional.
2. A **`jwks_uri`** that publishes the RS256/ES256 signing keys.
3. An **`openid` scope** that returns an **ID token** with `iss`, `aud` (= client_id), `sub`,
   `email`, `name`, `exp`, and `iat`.
4. **Per-computer authorization (required).** The Hermes plugin accepts *any* user the
   issuer signs in; it has no allowlist of its own. So Orgo must issue a code for a
   computer's client **only to people with access to that computer's workspace**. One client
   per computer makes this a simple check at `/oauth/authorize`.

## Provisioning flow (when a computer is created from the Hermes template)

1. `POST /api/computers/{id}/public-urls {"port": 9119}` gives `https://<label>.orgo.dev`.
2. Register a public OIDC client for that computer with redirect `https://<label>.orgo.dev/auth/callback`.
3. Inject these into the computer's create-time secrets (`/root/.env`). The template's
   `orgo-hermes-env` hook already copies these into `~/.hermes/.env`:
   ```
   HERMES_DASHBOARD_OIDC_ISSUER=https://www.orgo.ai
   HERMES_DASHBOARD_OIDC_CLIENT_ID=<per-computer client>
   HERMES_DASHBOARD_PUBLIC_URL=https://<label>.orgo.dev
   ```
4. Ship a `hermes-serve` supervisor program in the golden image, the same one this tool writes.
5. Show **"Connect Hermes Desktop: https://<label>.orgo.dev"** with a copy button on the
   computer's page in the Orgo dashboard.

The user's whole flow then becomes: copy the URL, paste it into Hermes Desktop, sign in with Orgo.

Until then, `orgo-hermes-connect up --auth oidc --oidc-issuer https://www.orgo.ai
--oidc-client-id <id>` will work as soon as the OIDC layer ships. No changes to this tool
are needed.

## Other things to decide

- **URL quota**: accounts default to 10 public URLs, but workspaces often run far more
  computers. Agent computers need a larger quota, or a separate pool.
- **Labels**: they must be unique and can't look like a computer id. `<name>-<4 hex>` works.
  New names are limited to 30 per user per day.
- **Teardown**: delete the URL and the OIDC client when the computer is deleted.
