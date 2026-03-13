# Timepoint Pro — Front-End Specification

## Overview

Timepoint Pro provides a dashboard API for accessing simulation run data. The front-end consumes this API to display runs, results, analytics, and convergence metrics.

## API Base URLs

| Environment | URL | Auth |
|-------------|-----|------|
| Local dev | `http://localhost:8000` | None required |
| Cloud (hosted) | `https://pro.timepointai.com` | JWT bearer token or `X-API-Key` header |

The cloud layer adds auth gating. The local dashboard API is open for development use.

## Authentication (Cloud Only)

Two auth modes are supported:

1. **API Key** — `X-API-Key: tp_cloud_...` header. Keys are created via the admin endpoint and stored as SHA-256 hashes.
2. **JWT Bearer** — `Authorization: Bearer <token>` header. Supports both Pro-issued JWTs and Flash-issued JWTs (validated via token introspection against `flash.timepointai.com`).

Flash SSO flow: Users authenticated with Flash at `flash.timepointai.com` receive a JWT that is automatically accepted by Pro Cloud via token introspection. This enables single sign-on across the Timepoint Suite.

## API Endpoints

### Simulation Data (Local + Cloud)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/runs` | List runs with filtering (template, status, mode, date, cost, mechanisms) |
| GET | `/api/run/{run_id}` | Detailed run information |
| GET | `/api/narrative/{run_id}` | Narrative JSON for a run |
| GET | `/api/screenplay/{run_id}` | Fountain-format screenplay |
| GET | `/api/dialogs/{run_id}` | All dialog turns for a run |
| GET | `/api/templates` | List all unique templates |
| GET | `/api/mechanisms` | Mechanism usage counts |
| GET | `/api/meta-analytics` | Aggregate analytics across all runs |
| GET | `/api/convergence-stats` | Aggregate convergence statistics |
| GET | `/api/convergence-sets` | List convergence sets with filtering |
| GET | `/api/convergence-set/{set_id}` | Detailed convergence set info |

### Cloud-Only Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/jobs` | Submit a new simulation job |
| GET | `/api/jobs/{job_id}` | Check job status and progress |
| DELETE | `/api/jobs/{job_id}` | Cancel a running job |
| GET | `/api/results/{job_id}` | Retrieve completed job results |
| GET | `/api/admin/usage` | Usage records (admin) |
| GET | `/api/admin/budget` | Budget status (admin) |
| POST | `/api/admin/api-keys` | Create new API key (admin) |
| GET | `/docs` | Interactive OpenAPI documentation (auth-gated) |

### Planned

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/data-export/{run_id}` | Bulk export: causal graphs, tensors, dialogs, convergence sets |

## Query Parameters — Runs Listing

The `/api/runs` endpoint supports comprehensive filtering:

| Parameter | Type | Description |
|-----------|------|-------------|
| `page` | int | Page number (default: 1) |
| `limit` | int | Results per page (default: 20) |
| `template` | string | Filter by template ID |
| `status` | string | `completed`, `running`, `failed` |
| `causal_mode` | string | `FORWARD`, `PORTAL`, `BRANCHING`, `DIRECTORIAL`, `CYCLICAL` |
| `start_date` | string | Filter by start date (YYYY-MM-DD) |
| `end_date` | string | Filter by end date |
| `min_cost` | float | Minimum cost |
| `max_cost` | float | Maximum cost |
| `mechanisms` | string | Comma-separated mechanism IDs (e.g., `M1,M5,M17`) |
| `min_entities` | int | Minimum entity count |
| `min_timepoints` | int | Minimum timepoint count |
| `sort_by` | string | `started_at`, `cost_usd`, `entities_created`, etc. |
| `order` | string | `ASC` or `DESC` |

## Subdomain Architecture

All Timepoint services are deployed under `timepointai.com`:

| Service | URL | Purpose |
|---------|-----|---------|
| Flash | `flash.timepointai.com` | Reality Writer — also serves as SSO provider via token introspection |
| Pro | `pro.timepointai.com` | This service (cloud hosted) |
| Clockchain | `clockchain.timepointai.com` | Temporal Causal Graph |
| Proteus | `proteus.timepointai.com` | Settlement Layer |
| API Gateway | `api.timepointai.com` | Unified routing to all services |
| Web App | `app.timepointai.com` | Browser client |
| Landing | `timepointai.com` | Marketing site |

### CORS

The cloud layer accepts requests from all `*.timepointai.com` subdomains and `localhost` origins for development.

## Front-End Architecture Notes

The previous Quarto-based frontend has been archived (`archive/quarto-frontend` branch). Future front-end options:

- **React/Vue dashboard** — SPA consuming the REST API above
- **Integration with Web App** — `app.timepointai.com` could embed Pro dashboard views
- **Jupyter notebooks** — For research and analysis workflows

### Key UI Surfaces

1. **Run Explorer** — Filterable, sortable table of simulation runs with cost, entity count, mechanism usage
2. **Run Detail** — Full run view: narrative, entity states, causal graph visualization, dialog playback
3. **Template Browser** — Browse and launch templates by category and temporal mode
4. **Analytics Dashboard** — Aggregate metrics: run counts, cost trends, mechanism usage distribution
5. **Convergence Viewer** — Visualize convergence across repeat runs (Jaccard similarity on causal graphs)
6. **Job Manager** (cloud) — Submit, monitor, and cancel simulation jobs

### Data Formats

- **Narratives**: JSON with structured causal events
- **Screenplays**: Fountain format (plain text, industry standard)
- **Training data**: JSONL with full causal context
- **Export**: TDF (JSON-LD), JSONL, SQLite
