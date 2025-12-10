# Timepoint Dashboard API

REST API backend for accessing Timepoint simulation data.

## Architecture

The API provides real-time access to the runs database via FastAPI.

### API Structure (`api/`)

**Files:**
- `server.py` - FastAPI application with 12 REST endpoints
- `db.py` - Database query layer with filtering, sorting, and pagination
- `models.py` - Pydantic models for request/response validation
- `requirements.txt` - Python dependencies

**Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/runs` | List runs with comprehensive filtering |
| GET | `/api/run/{run_id}` | Get detailed run information |
| GET | `/api/narrative/{run_id}` | Get narrative JSON |
| GET | `/api/screenplay/{run_id}` | Get Fountain screenplay |
| GET | `/api/dialogs/{run_id}` | Get all dialogs |
| GET | `/api/templates` | List all unique templates |
| GET | `/api/mechanisms` | Get mechanism usage counts |
| GET | `/api/meta-analytics` | Aggregate analytics across all runs |
| GET | `/api/convergence-stats` | Aggregate convergence statistics |
| GET | `/api/convergence-sets` | List convergence sets with filtering |
| GET | `/api/convergence-set/{set_id}` | Get detailed convergence set info |

## Quick Start

### Installation

```bash
cd dashboards/api
pip install -r requirements.txt
```

### Launch

```bash
# From project root
./run.sh dashboard

# Or directly
cd dashboards && ./backend.sh

# Or manually
cd dashboards/api && python3.10 server.py
```

**URLs:**
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs (Swagger UI)
- ReDoc: http://localhost:8000/redoc

## API Query Examples

```bash
# List all runs, paginated
curl "http://localhost:8000/api/runs?page=1&limit=50"

# Filter by template and status
curl "http://localhost:8000/api/runs?template=hospital_crisis&status=completed"

# Filter by cost range
curl "http://localhost:8000/api/runs?min_cost=0.1&max_cost=1.0"

# Filter by mechanisms
curl "http://localhost:8000/api/runs?mechanisms=M1,M5,M17"

# Get specific run details
curl "http://localhost:8000/api/run/{run_id}"

# Get narrative JSON
curl "http://localhost:8000/api/narrative/{run_id}"

# Get meta-analytics
curl "http://localhost:8000/api/meta-analytics"

# Get convergence statistics
curl "http://localhost:8000/api/convergence-stats"
```

## Query Parameters

### Runs Listing (`/api/runs`)

| Parameter | Type | Description |
|-----------|------|-------------|
| `page` | int | Page number (default: 1) |
| `limit` | int | Results per page (default: 20) |
| `template` | str | Filter by template ID |
| `status` | str | completed, running, failed |
| `causal_mode` | str | STANDARD, PORTAL, etc. |
| `start_date` | str | Filter by start date (YYYY-MM-DD) |
| `end_date` | str | Filter by end date |
| `min_cost` | float | Minimum cost |
| `max_cost` | float | Maximum cost |
| `mechanisms` | str | Comma-separated mechanism IDs (M1,M5,M17) |
| `min_entities` | int | Minimum entity count |
| `min_timepoints` | int | Minimum timepoint count |
| `sort_by` | str | started_at, cost_usd, entities_created, etc. |
| `order` | str | ASC or DESC |

## Database Schema

The API queries these SQLite tables:

### `runs`
Core run metadata: template_id, status, cost, entities/timepoints created, duration, etc.

### `mechanism_usage`
Tracks mechanisms used per run with timestamps and context.

### `resolution_assignments`
Records entity resolution changes (sketch -> low -> high).

### `validations`
Stores validation results for each run.

### File-based Data
- Narratives: `datasets/{template}/narrative_{timestamp}.json`
- Screenplays: `datasets/{template}/screenplay_{timestamp}.fountain`

## Technology Stack

- **FastAPI** - Modern Python web framework
- **Pydantic** - Data validation
- **SQLite** - Database (metadata/runs.db)
- **Uvicorn** - ASGI server

## Development

### Adding New Endpoints

1. Add endpoint in `api/server.py`:
   ```python
   @app.get("/api/new-endpoint")
   async def new_endpoint(param: str = Query(None)):
       return db.query_new_data(param)
   ```

2. Add query function in `api/db.py`:
   ```python
   def query_new_data(param):
       # SQL query logic
       pass
   ```

3. Add response model in `api/models.py` if needed.

### Adding New Filters

1. Add parameter to endpoint in `api/server.py`
2. Add filter logic in `api/db.py`:
   ```python
   if new_filter:
       where_clauses.append("column = ?")
       params.append(new_filter)
   ```

## Troubleshooting

### API Not Starting
- Check port 8000 is available: `lsof -i:8000`
- Verify database path in `api/db.py` (default: `../../metadata/runs.db`)
- Check Python version (requires 3.10+)

### Empty Responses
- Verify database exists: `ls metadata/runs.db`
- Check run has data: `./run.sh status`
- Test API directly: `curl http://localhost:8000/api/runs`

## Statistics (December 2025)

- **Total Runs**: 600+
- **Templates**: 41 (organized by category with patch metadata)
- **Mechanisms**: 18 (M1-M18)
- **SynthasAIzer**: Phase 1-3 implemented

## Frontend Note

The Quarto frontend has been archived to `archive/quarto-frontend` branch.
The API backend provides full programmatic access to all simulation data.

Future frontend options:
- Custom React/Vue dashboard
- Streamlit interface
- Jupyter notebooks with API integration
