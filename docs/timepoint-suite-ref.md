# Timepoint Suite — Canonical Reference

**Purpose:** Single source of truth for every addressable Timepoint Suite surface — services, hosted URLs, MCP endpoints, and the public API paths they expose. If you are wiring up an integration, adding monitoring, or onboarding a new agent, start here.

**Last updated:** 2026-04-24

---

## Service Registry

| Service | Visibility | Repo | Hosted URL | Role |
|---------|------------|------|------------|------|
| **Flash** | Open Source | [`timepoint-flash`](https://github.com/timepointai/timepoint-flash) | [flash.timepointai.com](https://flash.timepointai.com) | Reality Writer — renders grounded historical moments |
| **Clockchain** | Open Source | [`timepoint-clockchain`](https://github.com/timepointai/timepoint-clockchain) | [clockchain.timepointai.com](https://clockchain.timepointai.com) | Temporal Causal Graph — Rendered Past + Rendered Future, growing 24/7 |
| **Pro** | Open Source | [`timepoint-pro`](https://github.com/timepointai/timepoint-pro) | [pro.timepointai.com](https://pro.timepointai.com) | SNAG Simulation Engine — temporal simulation, TDF output, training data |
| **Proteus** | Open Source | [`proteus`](https://github.com/timepointai/proteus) | [proteus.timepointai.com](https://proteus.timepointai.com) | Settlement Layer — prediction markets for Rendered Futures |
| **TDF** | Open Source | [`timepoint-tdf`](https://github.com/timepointai/timepoint-tdf) | — (library) | Data Format — JSON-LD interchange across all services |
| **SNAG Bench** | Open Source | [`timepoint-snag-bench`](https://github.com/timepointai/timepoint-snag-bench) | — (runner) | Quality Certifier — measures Causal Resolution across renderings |
| **Funding Falcon** | Open Source · **GA 2026-04** | [`funding-falcon`](https://github.com/realityinspector/funding-falcon) | [falcon.timepointai.com](https://falcon.timepointai.com) · also surfaces in [Find Money](https://app.timepointai.com/find-money) | Grant intelligence — discovery, scoring, draft, packaging. Powers Find Money's first backend. |
| **API Gateway** | Private | [`timepoint-api-gateway`](https://github.com/timepointai/timepoint-api-gateway) | [api.timepointai.com](https://api.timepointai.com) | Unified API gateway — auth, metering, HMAC, proxy routing |
| **MCP (central)** | Public | [`timepoint-mcp`](https://github.com/timepointai/timepoint-mcp) | [mcp.timepointai.com](https://mcp.timepointai.com) | Central MCP Server — AI agent access to Flash and Clockchain |
| **Billing** | Private | [`timepoint-billing`](https://github.com/timepointai/timepoint-billing) | [billing.timepointai.com](https://billing.timepointai.com) | Payment Processing — Apple IAP + Stripe |
| **Web App** | Private | [`timepoint-web-app`](https://github.com/timepointai/timepoint-web-app) | [app.timepointai.com](https://app.timepointai.com) | Browser client — Synthetic Time Travel |
| **Landing** | Private | [`timepoint-landing`](https://github.com/timepointai/timepoint-landing) | [timepointai.com](https://timepointai.com) | Marketing site |
| **iPhone App** | Private | [`timepoint-iphone-app`](https://github.com/timepointai/timepoint-iphone-app) | — (iOS) | iOS client — Synthetic Time Travel on mobile |
| **Skip Meetings** | Private | [`skipmeetingsai`](https://github.com/timepointai/skipmeetingsai) | [skipmeetings.com](https://skipmeetings.com) | Meeting intelligence SaaS powered by Flash |

---

## Addressable MCP Surfaces

Three MCP surfaces are live. All require `Authorization: Bearer <token>` on every request. Tokens are the same `tp_*` API keys used for REST.

| MCP Surface | Endpoint | Source | Tools Exposed |
|-------------|----------|--------|---------------|
| **Central MCP** | `https://mcp.timepointai.com/mcp` | `timepoint-mcp` → `app/server.py` (`app.mount("/mcp", mcp_app)`) | Aggregated access to Flash and Clockchain tools |
| **Flash MCP** | `https://flash.timepointai.com/mcp/` | `timepoint-flash` → `app/main.py` (`app.mount("/mcp", BearerAuthMiddleware(get_mcp_app()))`) | `tp_flash_generate` |
| **Pro MCP** | `https://pro.timepointai.com/mcp/` | `timepoint-pro` → `api/main.py` (`app.mount("/mcp", BearerAuthMiddleware(get_mcp_app()))`) | `tp_pro_simulate` (returns `job_id`; poll `GET /simulations/{job_id}`) |

### MCP client config example

```jsonc
{
  "mcpServers": {
    "timepoint-flash": {
      "url": "https://flash.timepointai.com/mcp/",
      "headers": { "Authorization": "Bearer ${TIMEPOINT_API_KEY}" }
    },
    "timepoint-pro": {
      "url": "https://pro.timepointai.com/mcp/",
      "headers": { "Authorization": "Bearer ${TIMEPOINT_API_KEY}" }
    }
  }
}
```

---

## Gateway Route Map

All public API traffic flows through `api.timepointai.com`. The gateway owns auth, metering (`X-Credits-Charged` / `X-Balance-After`), HMAC request signing, and routing to downstream services. Route prefixes currently exposed:

| Prefix | Downstream | Purpose |
|--------|------------|---------|
| `/api/v1/auth/*` | Gateway (self) | Key issuance, introspection, `/auth/me` |
| `/api/v1/conductor/*` | Flash | Conductor (OSS) simulation surface |
| `/api/v1/conductor/pro/*` | **Pro cloud** | Pro-tier simulation (`/simulate`, `/compare`) — **shipped 2026-04-24 (API-3, #12)** |
| `/api/v1/falcon/packages/*` | Funding Falcon | Grant package CRUD proxy — **shipped 2026-04-24 (#10)** |
| `/api/v1/falcon/orgs/*` | Funding Falcon | Org CRUD proxy |
| `/api/v1/falcon/runs/*` | Funding Falcon | Run CRUD proxy |
| `/internal/auth/validate-key` | Gateway (internal) | Key validation for downstream services (not public) |

### Conductor Pro routes (shipped this week)

Defined in `timepoint-api-gateway/gateway/routes/conductor_pro.py` (router prefix `/api/v1/conductor/pro`):

| Method | Path | Credit Cost | Metric |
|--------|------|-------------|--------|
| POST | `/api/v1/conductor/pro/simulate` | 15 | `conductor_pro_sim` |
| POST | `/api/v1/conductor/pro/compare` | 10 | `conductor_compare` |

### Falcon packages routes (shipped this week)

Defined in `timepoint-api-gateway/gateway/routes/falcon.py`:

| Method | Path | Purpose |
|--------|------|---------|
| GET    | `/api/v1/falcon/packages` | List packages |
| GET    | `/api/v1/falcon/packages/{path:path}` | Read package (nested paths) |
| POST   | `/api/v1/falcon/packages` | Create package |
| POST   | `/api/v1/falcon/packages/{path:path}` | Action on package |
| PATCH  | `/api/v1/falcon/packages/{path:path}` | Update package |
| DELETE | `/api/v1/falcon/packages/{path:path}` | Delete package |

Service-key auth and `X-User-Id` headers are forwarded to the Falcon backend. Consumer: the web-app `/find-money` page (FM plan, task FM-1).

---

## Recently Shipped (week of 2026-04-17 → 2026-04-24)

| Change | Repo | Commit / PR |
|--------|------|-------------|
| Pro MCP server at `pro.timepointai.com/mcp/` (`tp_pro_simulate`) | `timepoint-pro` | `2dadc77` (#28) |
| Flash MCP server at `flash.timepointai.com/mcp/` (`tp_flash_generate`) | `timepoint-flash` | `d9f7453` (#35) |
| HMAC-signed Gateway → Flash requests (closes X-User-Id impersonation, API-4) | `timepoint-flash` / `timepoint-api-gateway` | `8495b10` / `228dc23` |
| Gateway billable-response headers (`X-Credits-Charged`, `X-Balance-After`, API-7) | `timepoint-api-gateway` | `2ecbcad` (#13) |
| Gateway → Pro cloud proxy `/api/v1/conductor/pro/*` (API-3) | `timepoint-api-gateway` | `d291939` (#12) |
| Gateway → Falcon packages proxy `/api/v1/falcon/packages/*` | `timepoint-api-gateway` | `9a5de9d` (#10) |
| Gateway auth accepts `tp_gw_*` / `tp_org_*` Bearer on every authenticated route (API-2) | `timepoint-api-gateway` | `afd2d54` |
| Developer docs: quickstart, key-types matrix, MCP tools, errors decision tree (API-8) | `timepoint-api-gateway` | `2cc61c7` (#14) |

---

## Update Policy

This document is the **canonical reference** for addressable Timepoint Suite surfaces. When you:

- Ship a new service subdomain, mount a new MCP surface, or expose a new public route prefix → **update this file in the same PR**.
- Change a hosted URL, deprecate an endpoint, or alter a credit cost → **update this file in the same PR**.
- Add a new MCP tool → **append it to the relevant MCP surface row**.

The short-form table in `README.md` (§ Timepoint Suite) is a summary only; this file is authoritative for URLs and endpoint paths.
