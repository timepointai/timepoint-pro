# PLAN.md - Timepoint-Daedalus: From Entity Generator to Interactive Temporal Simulation

## Current State Assessment

**What works:**
- LLM-driven entity population with contextual knowledge
- Graph-based relationship modeling (NetworkX)
- Database persistence (SQLite)
- Validation framework (physics-inspired constraints)
- Report generation (JSON, Markdown, GraphML)
- Cost tracking for API usage

**Critical gaps:**
- No temporal chains (single timepoint snapshots only)
- No exposure tracking (entities have knowledge but no acquisition history)
- No variable resolution system (all entities at uniform detail level)
- No interactive query interface (can't ask questions and get answers)
- Tensor compression exists but isn't used in workflows
- Knowledge consistency validation fails (0.00 scores)

**Cost to date:** ~$0.39 (39 entities populated)

---

## Phase 1: Fix Validation and Exposure Tracking (2-3 hours)

### Goal
Make entities track HOW they acquired knowledge, not just WHAT they know. This enables temporal coherence validation.

### Tasks

**1.1: Add Exposure Event Model**

Create `schemas.py` additions:
```python
class ExposureEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    entity_id: str = Field(foreign_key="entity.entity_id")
    event_type: str  # witnessed, learned, told, experienced
    information: str  # what was learned
    source: Optional[str]  # who/what provided the information
    timestamp: datetime
    confidence: float = Field(default=1.0)
```

**1.2: Update Entity Population to Record Exposure**

Modify `cli.py` `run_historical_training()`:
- After LLM populates entity, create ExposureEvent for each knowledge item
- Set event_type based on context (e.g., "witnessed" for inauguration attendees)
- Link to source entity if knowledge came from relationships
- Store in database alongside entity

**1.3: Fix Knowledge Consistency Validator**

Modify `validation.py` `validate_information_conservation()`:
- Query ExposureEvent table for entity's exposure history
- Build set of all information entity has been exposed to
- Check if entity's knowledge_state ⊆ exposure history
- Return proper validation with violations if mismatch

**Verification:**
```bash
poetry run python cli.py mode=train training.context=founding_fathers_1789
poetry run python cli.py mode=evaluate

# Should show Knowledge Consistency > 0.00 for entities
```

**Anti-patterns to avoid:**
- Don't make exposure tracking synchronous/blocking (batch insert events)
- Don't create circular dependencies between Entity and ExposureEvent
- Don't query exposure events on every validation (cache during evaluation run)

---

## Phase 2: Build Temporal Chains (4-5 hours)

### Goal
Connect multiple timepoints into a causal sequence, enabling "clockchain" narrative progression.

### Tasks

**2.1: Define Timepoint Model**

Add to `schemas.py`:
```python
class Timepoint(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    timepoint_id: str = Field(unique=True, index=True)
    timestamp: datetime
    event_description: str
    entities_present: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    causal_parent: Optional[str]  # previous timepoint_id
    resolution_level: ResolutionLevel = Field(default=ResolutionLevel.SCENE)
```

**2.2: Create Temporal Chain Builder**

New file: `temporal_chain.py`:
```python
def build_temporal_chain(context_name: str, num_timepoints: int = 5):
    """Generate sequence of connected timepoints from historical context"""
    # Load base context
    # Generate timepoints at intervals (e.g., hourly during inauguration day)
    # Create causal links (timepoint N+1 references timepoint N)
    # Vary resolution (early timepoints low-res, peak moment high-res)
    # Return list of Timepoint objects
```

**2.3: Implement Causal Event Propagation**

When populating entity at timepoint N:
- Query entity state at timepoint N-1
- Pass previous knowledge_state as context to LLM
- LLM generates what changed between timepoints
- Create ExposureEvents for new information acquired
- Store delta, not full state duplication

**2.4: Add Temporal Chain Training Mode**

Modify `cli.py` to add `mode=temporal_train`:
```python
def run_temporal_training(cfg, store, llm_client):
    chain = build_temporal_chain(
        cfg.training.context,
        num_timepoints=cfg.training.get("num_timepoints", 5)
    )
    
    for timepoint in chain:
        # Load entities from previous timepoint
        # Generate their evolved states
        # Record exposure events for changes
        # Validate causal consistency
```

**Verification:**
```bash
poetry run python cli.py mode=temporal_train training.context=founding_fathers_1789 training.num_timepoints=3

# Should create 3 linked timepoints
# Check database has Timepoint records with causal_parent links
# Verify entities evolve across timepoints (knowledge accumulates)
```

**Anti-patterns:**
- Don't regenerate full entity state at each timepoint (expensive, redundant)
- Don't create timepoints without causal links (defeats temporal coherence)
- Don't use uniform resolution (waste tokens on unimportant moments)

---

## Phase 3: Variable Resolution System (3-4 hours)

### Goal
Implement adaptive detail levels - some entities/timepoints highly detailed, others compressed.

### Tasks

**3.1: Resolution Decision Engine**

New file: `resolution_engine.py`:
```python
def decide_resolution(
    entity: Entity,
    timepoint: Timepoint,
    query_history: Dict[str, int]  # entity_id -> access count
) -> ResolutionLevel:
    """Decide detail level for entity at timepoint"""
    
    # High resolution if:
    # - Entity central to timepoint event
    # - Frequently queried by users
    # - High eigenvector centrality in graph
    
    # Low resolution if:
    # - Peripheral entity
    # - Rarely accessed
    # - Low graph centrality
    
    # Return TENSOR_ONLY, SCENE, GRAPH, DIALOG, or TRAINED
```

**3.2: Implement Lazy Resolution Elevation**

When entity is queried but resolution too low:
- Trigger LLM call to elaborate entity state
- Increment resolution_level in database
- Cache result for future queries
- Update query_history statistics

**3.3: Apply Tensor Compression to Low-Resolution Entities**

Modify `workflows.py` `compress_tensors()` to actually use results:
- For TENSOR_ONLY entities, store only compressed representation
- For higher resolutions, keep full data but also store compressed version
- On query, decompress tensors if needed for response synthesis

**3.4: Add Resolution Metrics to Reports**

Show distribution of entities by resolution level in evaluation reports.

**Verification:**
```bash
# Create temporal chain with many entities
poetry run python cli.py mode=temporal_train training.context=founding_fathers_1789 training.num_timepoints=5

# Check that peripheral entities have TENSOR_ONLY resolution
# Check that central figures have TRAINED resolution
poetry run python -c "
from storage import GraphStore
from sqlmodel import Session, select
from schemas import Entity

store = GraphStore()
with Session(store.engine) as session:
    entities = session.exec(select(Entity)).all()
    for e in entities:
        print(f'{e.entity_id}: {e.resolution_level.value}')
"
```

**Anti-patterns:**
- Don't compute resolution on every query (cache decisions)
- Don't elevate resolution without user demand (wasteful)
- Don't compress entities that are frequently accessed (thrashing)

---

## Phase 4: Interactive Query Interface (5-6 hours)

### Goal
Enable natural language queries that synthesize answers from entity states.

### Tasks

**4.1: Query Parser**

New file: `query_interface.py`:
```python
def parse_query(query: str, llm_client: LLMClient) -> QueryIntent:
    """Extract intent from natural language query"""
    # Use LLM to classify:
    # - Target entity (who is the query about?)
    # - Target timepoint (when?)
    # - Information type (knowledge, relationships, actions, dialog?)
    # - Context needed (which other entities matter?)
    
    # Return structured QueryIntent object
```

**4.2: Entity State Synthesizer**

```python
def synthesize_response(
    query_intent: QueryIntent,
    store: GraphStore,
    llm_client: LLMClient
) -> str:
    """Generate answer from entity states"""
    
    # 1. Load target entity at target timepoint
    # 2. Load related entities within context window
    # 3. Elevate resolution if needed (lazy loading)
    # 4. Build prompt with entity states + query
    # 5. LLM synthesizes coherent answer
    # 6. Record this as an ExposureEvent if new knowledge created
    # 7. Return response with citations to entity states
```

**4.3: Add Interactive Mode to CLI**

```python
def run_interactive(cfg, store, llm_client):
    """REPL for querying temporal simulation"""
    print("Timepoint Interactive Query Interface")
    print("Enter queries or 'exit' to quit\n")
    
    while True:
        query = input("Query: ")
        if query.lower() == 'exit':
            break
            
        intent = parse_query(query, llm_client)
        response = synthesize_response(intent, store, llm_client)
        
        print(f"\nResponse: {response}\n")
        print(f"Cost: ${llm_client.cost:.4f}\n")
```

**4.4: Add Query History Tracking**

Track which entities/timepoints are queried most frequently.
Use this to inform resolution decisions (Phase 3 integration).

**Verification:**
```bash
poetry run python cli.py mode=interactive

# Try queries:
# "What did George Washington think about the inauguration?"
# "How did Hamilton and Jefferson's relationship evolve?"
# "Describe Leonardo's reaction to Michelangelo's David"
```

**Anti-patterns:**
- Don't load entire database for every query (selective loading only)
- Don't generate responses without citing sources (attribution required)
- Don't ignore query history (it's the signal for resolution elevation)

---

## Phase 5: Complete Workflow Integration (2-3 hours)

### Goal
Connect all systems into coherent end-to-end experience.

### Tasks

**5.1: Update Autopilot to Test Temporal Chains**

Modify autopilot to:
- Build temporal chains with varying lengths
- Test resolution elevation under query load
- Validate causal consistency across timepoints
- Report on compression effectiveness

**5.2: Add Temporal Chain Visualization**

Export temporal chains as:
- Timeline graphs (nodes = timepoints, edges = causal links)
- Entity trajectory graphs (how entities evolve)
- Resolution heatmaps (detail level across time/entities)

**5.3: Create End-to-End Demo Script**

New file: `demo.sh`:
```bash
#!/bin/bash
# Demonstrates complete workflow

# 1. Build temporal chain
poetry run python cli.py mode=temporal_train training.context=founding_fathers_1789 training.num_timepoints=5

# 2. Run evaluation
poetry run python cli.py mode=evaluate

# 3. Interactive queries
echo "What did Washington think about becoming president?" | poetry run python cli.py mode=interactive

# 4. Show resolution distribution
poetry run python -c "from resolution_stats import show_distribution; show_distribution()"

# 5. Generate reports
ls -lh reports/
```

**5.4: Documentation Update**

Update README.md with:
- Temporal chain concepts
- Variable resolution explanation
- Query interface examples
- Cost estimation for different use cases

**Verification:**
```bash
./demo.sh

# Should show complete workflow:
# - Temporal chain creation
# - Entity evolution across timepoints
# - Interactive queries working
# - Reports with resolution metrics
```

---

## Phase 6: Optimization and Polish (2-3 hours)

### Goal
Performance tuning and production readiness.

### Tasks

**6.1: Implement Batch LLM Calls**

Currently LLM calls are sequential. Parallelize where possible:
- Batch entity population at same timepoint
- Use LangGraph parallelization properly
- Respect API rate limits

**6.2: Add Caching Layer**

Cache frequently accessed:
- Entity states at popular timepoints
- Common query responses
- Compressed tensor representations

**6.3: Cost Optimization**

- Use cheaper models for peripheral entities (gpt-3.5-turbo vs llama-405b)
- Implement token budgets per timepoint
- Warn when approaching budget limits

**6.4: Error Handling**

Improve resilience:
- Retry failed LLM calls with backoff
- Graceful degradation if API unavailable
- Partial results if some entities fail

**Verification:**
```bash
# Run stress test
poetry run python cli.py mode=temporal_train training.context=founding_fathers_1789 training.num_timepoints=10

# Verify:
# - No crashes on failures
# - Cost stays within budget
# - Performance acceptable (< 5 min for 10 timepoints)
```

---

## Success Criteria

### Functional Requirements
- [ ] Temporal chains with 5+ connected timepoints work
- [ ] Entities track exposure history with timestamps
- [ ] Knowledge consistency validation passes (>0.80 scores)
- [ ] Variable resolution system automatically adjusts detail
- [ ] Interactive queries generate coherent responses
- [ ] Reports show temporal evolution and resolution distribution

### Performance Requirements
- [ ] 10-timepoint chain completes in <5 minutes
- [ ] Interactive query responds in <5 seconds
- [ ] Cost per temporal chain <$1 (assuming 5 timepoints, 5 entities)
- [ ] 90%+ of peripheral entities at TENSOR_ONLY resolution

### Quality Requirements
- [ ] Temporal coherence: entities don't know future events
- [ ] Causal consistency: changes have explanations
- [ ] Response quality: queries answered accurately from entity states
- [ ] Attribution: responses cite source entities/timepoints

---

## Estimated Total Effort

- Phase 1: 2-3 hours (exposure tracking)
- Phase 2: 4-5 hours (temporal chains)
- Phase 3: 3-4 hours (variable resolution)
- Phase 4: 5-6 hours (query interface)
- Phase 5: 2-3 hours (integration)
- Phase 6: 2-3 hours (optimization)

**Total: 18-24 hours of development**

---

## Risk Mitigation

### Technical Risks
- **LLM inconsistency:** Use temperature=0.7 and validation to catch contradictions
- **Cost overruns:** Implement hard budget limits, abort if exceeded
- **State explosion:** Aggressive compression for peripheral entities
- **Query ambiguity:** Clarification prompts if intent unclear

### Data Risks
- **Anachronisms:** Strict temporal validation, reject future knowledge
- **Hallucinations:** Cross-reference entity claims against exposure history
- **Inconsistent evolution:** Require causal explanations for state changes

### Operational Risks
- **API failures:** Retry logic with exponential backoff
- **Database corruption:** Regular backups, transaction safety
- **Memory issues:** Stream large queries, don't load all entities

---

## Final Notes

This plan takes you from a **static entity generator** to an **interactive temporal simulation**. The key innovation is the temporal chain with variable resolution - you populate detail where it matters, compress where it doesn't, and let user queries drive resolution elevation.

The original vision of "eigen-reduced back into behavior temperatures along llm-extruded behavior edges" translates to: peripheral entities stored as compressed tensors, central entities with full state, and LLM synthesis of interactions based on graph relationships.

You're not building a game or a chatbot. You're building a **queryable temporal knowledge graph** where entities evolve causally and respond coherently to questions about their simulated experiences.