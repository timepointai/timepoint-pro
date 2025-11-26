# Timepoint Dashboard System

A comprehensive, real-time dashboard system for browsing, analyzing, and visualizing Timepoint simulation runs.

## Architecture

The system consists of two main components:

### 1. FastAPI Backend (`api/`)
REST API server providing real-time access to the runs database.

**Key Files:**
- `server.py` - FastAPI application with 8 REST endpoints
- `db.py` - Database query layer with filtering, sorting, and pagination
- `models.py` - Pydantic models for request/response validation
- `requirements.txt` - Python dependencies

**Endpoints:**
- `GET /api/runs` - List runs with comprehensive filtering
- `GET /api/run/{run_id}` - Get detailed run information
- `GET /api/narrative/{run_id}` - Get narrative JSON
- `GET /api/screenplay/{run_id}` - Get Fountain screenplay
- `GET /api/dialogs/{run_id}` - Get all dialogs
- `GET /api/templates` - List all unique templates
- `GET /api/mechanisms` - Get mechanism usage counts
- `GET /api/meta-analytics` - Aggregate analytics across all runs

### 2. Quarto Frontend
Interactive web interface built with Quarto + Observable JS.

**Pages:**
- `index.qmd` - Main dashboard with visualizations (timeline, network, metrics)
- `runs.qmd` - Run selection with filtering and search
- `analytics.qmd` - Meta-analytics with charts and statistics
- `screenplay.qmd` - Fountain screenplay viewer with navigation
- `dialogs.qmd` - Dialog navigator with filtering and export

## Installation & Setup

### 1. Install API Dependencies

```bash
cd dashboards/api
pip install -r requirements.txt
```

### 2. Install Quarto

Download and install Quarto from https://quarto.org/docs/get-started/

Or use Homebrew:
```bash
brew install quarto
```

### 3. Launch Dashboard (Recommended)

Use the provided management scripts:

**Option A: Launch Both Servers Together**
```bash
cd dashboards
./dashboard.sh
```
This starts both backend and frontend, and stops both when you press Ctrl+C.

**Option B: Launch Separately**

Frontend only:
```bash
cd dashboards
./frontend.sh
```

Backend only:
```bash
cd dashboards
./backend.sh
```

### 4. Manual Launch (Alternative)

**Start API Server:**
```bash
cd dashboards/api
python3.10 server.py
```
The API will be available at http://localhost:8000
API documentation at http://localhost:8000/docs

**Start Quarto Preview Server:**
```bash
cd dashboards
quarto preview --port 8888
```
The dashboard will be available at http://localhost:8888

## Management Scripts

Three bash scripts are provided for easy server management:

### `dashboard.sh` - Launch Full System
Starts both backend API and frontend Quarto server together. Automatically handles:
- Killing existing processes on both ports
- Starting backend in background
- Validating backend is running
- Starting frontend in foreground
- Clean shutdown of both servers on Ctrl+C

### `frontend.sh` - Frontend Only
Manages Quarto preview server:
- Kills any existing Quarto processes
- Starts Quarto on port 8888
- Shows helpful URLs

### `backend.sh` - Backend Only
Manages FastAPI server:
- Kills any existing API server processes
- Starts server on port 8000
- Shows API documentation URL

## Usage

### Browsing Runs

1. Navigate to **Browse Runs** (http://localhost:8888/runs.html)
2. Use filters to narrow down results:
   - **Template** - Filter by template ID
   - **Status** - completed, running, or failed
   - **Causal Mode** - STANDARD, PORTAL, etc.
   - **Date Range** - Filter by start date
   - **Cost Range** - Min/max cost filters
   - **Entities/Timepoints** - Minimum thresholds
   - **Mechanisms** - Comma-separated list (e.g., M1,M5,M17)
3. Click any row to view the full dashboard for that run

### Viewing Run Details

The main dashboard (index.html?run_id=XXX) shows:
- **Run Metadata** - ID, template, status, cost, duration
- **Simulation Stats** - Entities, timepoints, LLM calls, tokens
- **Mechanisms Used** - Visual badges showing which mechanisms were active
- **Executive Summary** - Narrative summary if available
- **Visualizations**:
  - Timeline view (via vis-timeline)
  - Network graph (via Cytoscape.js)
  - Mechanism radar chart (via ECharts)
- **Detailed Analysis**:
  - Resolution assignments table
  - Validations table
  - Mechanism timeline

### Meta-Analytics

The analytics page (analytics.html) provides:
- **Overview Metrics** - Total runs, cost, success rate, avg cost
- **Run Statistics** - Completed, failed, entities, timepoints
- **Cost Analysis** - Cost over time (last 30 days)
- **Template Performance** - Top templates by usage
- **Causal Mode Distribution** - Pie chart
- **Mechanism Co-Occurrence** - Pairs that frequently appear together

### Screenplay Viewer

View Fountain-formatted screenplays (screenplay.html?run_id=XXX):
- **Scene Navigation** - Jump to specific scenes
- **Character Filtering** - Show only scenes with specific characters
- **Dialog Search** - Full-text search
- **Statistics** - Scene count, character count, line count
- **Download** - Export to .fountain file

### Dialog Navigator

Browse and analyze dialogs (dialogs.html?run_id=XXX):
- **Filters**:
  - Character - Show dialogs from specific characters
  - Timepoint - Filter by timepoint
  - Location - Filter by location
  - Search - Full-text search
- **Sorting** - Chronological, by character, or by location
- **Timeline View** - Visual representation of dialogs across timepoints
- **Export** - Download filtered dialogs as CSV

## Features

### Real-Time Database Access
All pages fetch data directly from the API, showing the latest information from the database without manual refresh.

### Comprehensive Filtering
The runs browser supports 10+ filter parameters:
- Template ID
- Status (completed/running/failed)
- Date range
- Cost range (min/max)
- Causal mode
- Mechanisms (comma-separated)
- Minimum entities
- Minimum timepoints

### Sorting & Pagination
- Sort by: started_at, cost_usd, entities_created, timepoints_created, duration_seconds
- Order: ASC or DESC
- Pagination: 10, 25, 50, or 100 per page

### Interactive Visualizations
- **Timeline** - Chronological navigation of timepoints with vis-timeline
- **Network Graph** - Character relationships with Cytoscape.js
- **Charts** - Mechanism radar, cost over time, template distribution with ECharts

### Export Capabilities
- Fountain screenplay download
- Dialog CSV export
- Filtered data export

## Database Schema

The system queries the following tables:

### `runs`
Core run metadata including template_id, status, cost, entities/timepoints created, etc.

### `mechanism_usage`
Tracks which mechanisms were used in each run with timestamps and context.

### `resolution_assignments`
Records entity resolution changes (sketch → low → high).

### `validations`
Stores validation results for each run.

### Narrative JSON Files
Located in `datasets/{template}/narrative_{timestamp}.json`
Contains characters, timepoints, dialogs, and executive summary.

### Screenplay Fountain Files
Located in `datasets/{template}/screenplay_{timestamp}.fountain`
Fountain-formatted screenplay output.

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
curl "http://localhost:8000/api/run/hospital_crisis_20251102_134859_a38592ed"

# Get narrative
curl "http://localhost:8000/api/narrative/hospital_crisis_20251102_134859_a38592ed"

# Get screenplay
curl "http://localhost:8000/api/screenplay/hospital_crisis_20251102_134859_a38592ed"

# Get meta-analytics
curl "http://localhost:8000/api/meta-analytics"
```

## Technology Stack

### Backend
- **FastAPI** - Modern Python web framework
- **Pydantic** - Data validation
- **SQLite** - Database (via runs.db)
- **Uvicorn** - ASGI server

### Frontend
- **Quarto** - Static site generator with native Observable JS support
- **Observable JS** - Reactive JavaScript for data visualization
- **vis-timeline** - Interactive timeline visualization
- **Cytoscape.js** - Network graph visualization
- **Apache ECharts** - Chart library for analytics
- **Fountain.js** - Screenplay parsing and rendering

## Development

### Adding New Filters

To add a new filter to the runs browser:

1. Add filter input in `runs.qmd`:
   ```javascript
   viewof newFilter = Inputs.select(...)
   ```

2. Add filter to query params:
   ```javascript
   if (newFilter !== "All") params.append("new_filter", newFilter);
   ```

3. Add filter support in `api/db.py`:
   ```python
   if new_filter:
       where_clauses.append("new_column = ?")
       params.append(new_filter)
   ```

4. Add parameter to `api/server.py`:
   ```python
   new_filter: Optional[str] = Query(None, description="...")
   ```

### Adding New Visualizations

1. Add chart container in the .qmd file
2. Initialize chart library (ECharts, Cytoscape, etc.)
3. Fetch data from API
4. Render visualization

### Adding New API Endpoints

1. Add endpoint in `api/server.py`
2. Add query function in `api/db.py`
3. Add response model in `api/models.py` if needed

## Troubleshooting

### API Not Starting
- Check that port 8000 is available
- Verify database path in `api/db.py` (default: `../../metadata/runs.db`)
- Check Python version (requires 3.10+)

### Quarto Preview Issues
- Verify Quarto is installed: `quarto --version`
- Check Python kernel: should use `python3.10`
- Clear cache: `quarto clean`

### Empty Visualizations
- Verify run has narrative data (check `narrative_{timestamp}.json` exists)
- Check API is returning data: `curl http://localhost:8000/api/narrative/{run_id}`
- Look for browser console errors

### CORS Errors
- Ensure API is running on localhost:8000
- Check CORS middleware configuration in `api/server.py`

## Statistics (as of 2025-11-03)

- **Total Runs**: 558
- **Total Cost**: $123.67
- **Completed Runs**: 454
- **Success Rate**: 81.4%
- **Templates**: 64 unique
- **Mechanisms Tracked**: 17
- **Database Size**: ~558 runs with full metadata

## Next Steps

Potential enhancements:
- Add real-time run monitoring (WebSocket support)
- Implement run comparison view
- Add mechanism dependency graph
- Export full reports as PDF
- Add user authentication
- Implement run replay/visualization
- Add cost prediction models
- Integrate with CI/CD for automatic testing
