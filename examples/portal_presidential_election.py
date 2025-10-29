"""
PORTAL Mode Example: Presidential Election Backward Simulation

This example demonstrates PORTAL mode (Mechanism 17 - Modal Temporal Causality),
which performs backward inference from a known endpoint to a known origin.

Scenario:
    Portal (2040): John Doe is elected President of the United States
    Origin (2025): John Doe is VP of Engineering at a tech startup

    Goal: Discover the most plausible paths from 2025 → 2040

This showcases:
- Backward temporal reasoning
- Multiple path generation
- Hybrid scoring (LLM + historical + causal + capability + context)
- Forward coherence validation
- Pivot point detection (critical decision moments)
"""

from datetime import datetime
from schemas import Entity, TemporalMode, ResolutionLevel
from generation.config_schema import TemporalConfig
from workflows import TemporalAgent
from storage import GraphStore
from llm_v2 import LLMClient
import os


def example_presidential_election_portal():
    """
    Run a PORTAL mode backward simulation from presidential election to origin.

    Returns:
        List of PortalPath objects with coherence scores and pivot points
    """

    print("=" * 80)
    print("PORTAL MODE EXAMPLE: Presidential Election")
    print("Backward Simulation from Endpoint to Origin")
    print("=" * 80)

    # Initialize storage and LLM
    store = GraphStore()

    # Check if LLM service is available
    llm_service_enabled = os.environ.get("LLM_SERVICE_ENABLED", "false").lower() == "true"

    if llm_service_enabled:
        llm_client = LLMClient()
        print("\n✓ LLM service enabled - will use AI for state generation")
    else:
        print("\n⚠️  LLM service disabled - using placeholder implementations")
        llm_client = None

    # Define portal endpoint
    portal_description = """
    John Doe is elected President of the United States in November 2040.

    Context:
    - Major campaign issues: climate change, economic reform, technology regulation
    - Electoral college victory: 326-212
    - Popular vote margin: 52.4% vs 45.2%
    - Strong support from tech sector and young voters
    - Key swing states: Pennsylvania, Michigan, Arizona
    """

    # Define origin state
    origin_description = """
    John Doe is VP of Engineering at TechCorp, a mid-sized startup in San Francisco.

    Context:
    - Age: 35
    - Education: BS Computer Science, MBA from Stanford
    - Previous roles: Senior Engineer → Engineering Manager → VP Engineering
    - Active on social media, occasional tech conference speaker
    - No prior political experience
    - Married, two young children
    """

    print("\n" + "=" * 80)
    print("CONFIGURATION")
    print("=" * 80)
    print(f"\nPortal (Endpoint): {portal_description.strip()[:100]}...")
    print(f"Portal Year: 2040")
    print(f"\nOrigin (Starting Point): {origin_description.strip()[:100]}...")
    print(f"Origin Year: 2025")
    print(f"\nBackward Steps: 15 (one per year)")
    print(f"Paths to Generate: 3")
    print(f"Exploration Strategy: Adaptive")

    # Create PORTAL mode configuration
    config = TemporalConfig(
        mode=TemporalMode.PORTAL,

        # Portal endpoint
        portal_description=portal_description,
        portal_year=2040,

        # Origin point
        origin_year=2025,
        origin_description=origin_description,

        # Backward exploration parameters
        backward_steps=15,  # 2040 - 2025 = 15 years
        path_count=3,  # Generate top 3 most plausible paths
        candidate_antecedents_per_step=5,  # Generate 5 candidates at each backward step

        # Exploration strategy
        exploration_mode="adaptive",  # System decides based on complexity
        oscillation_complexity_threshold=10,  # Use oscillating if steps > 10

        # Scoring weights
        llm_scoring_weight=0.35,  # LLM plausibility assessment
        historical_precedent_weight=0.20,  # Similar patterns in history
        causal_necessity_weight=0.25,  # How necessary is this antecedent?
        entity_capability_weight=0.15,  # Can entity actually do this?
        # dynamic_context weight: 0.05 (implicit, used as tiebreaker)

        # Validation
        coherence_threshold=0.6,  # Minimum forward coherence score

        # Failure handling
        max_backtrack_depth=3,  # Try fixing paths up to 3 steps back

        # Resolution
        temporal_granularity=ResolutionLevel.YEAR,  # Year-level resolution

        # ===================================================================
        # OPTIONAL: Simulation-Based Judging (NEW)
        # ===================================================================
        # Enable this for MUCH higher quality paths at 3x computational cost
        # Instead of static scoring, runs forward mini-simulations from each
        # candidate and uses a judge LLM to evaluate realism holistically.
        #
        # Uncomment to enable:
        # use_simulation_judging=True,
        # simulation_forward_steps=2,  # Simulate 2 years forward per candidate
        # simulation_max_entities=5,  # Limit entities for performance
        # simulation_include_dialog=True,  # Generate conversations
        # judge_model="meta-llama/llama-3.1-405b-instruct",  # Judge LLM
        # judge_temperature=0.3,  # Low temp for consistent judging
        #
        # Cost estimate with simulation judging: ~$4-8 vs ~$1-2 standard
        # Quality improvement: Significant - captures emergent behaviors
    )

    # Create temporal agent in PORTAL mode
    agent = TemporalAgent(
        mode=TemporalMode.PORTAL,
        store=store,
        llm_client=llm_client
    )

    print("\n" + "=" * 80)
    print("RUNNING PORTAL SIMULATION")
    print("=" * 80)

    # Run backward simulation
    paths = agent.run_portal_simulation(config)

    # Display results
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)

    if not paths:
        print("\n⚠️  No valid paths found. Possible reasons:")
        print("    - Coherence threshold too high")
        print("    - Path exploration needs more candidates per step")
        print("    - LLM service needed for better state generation")
        return []

    print(f"\n✓ Found {len(paths)} plausible paths from origin to portal\n")

    for i, path in enumerate(paths, 1):
        print(f"\n{'─' * 80}")
        print(f"PATH {i}: Coherence Score = {path.coherence_score:.3f}")
        print(f"{'─' * 80}")

        print(f"\nPath ID: {path.path_id}")
        print(f"Total States: {len(path.states)}")
        print(f"Pivot Points: {len(path.pivot_points)} critical decision moments")

        # Show key milestones
        print(f"\nKey Milestones:")
        for state_idx, state in enumerate(path.states):
            is_pivot = state_idx in path.pivot_points
            pivot_marker = " [PIVOT]" if is_pivot else ""

            # Show every 3rd year + pivots + endpoints
            if state_idx == 0 or state_idx == len(path.states) - 1 or is_pivot or state_idx % 3 == 0:
                print(f"  {state.year}: {state.description[:80]}{pivot_marker}")
                print(f"          (plausibility: {state.plausibility_score:.2f})")

        if path.explanation:
            print(f"\nExplanation: {path.explanation}")

        # Show validation details if available
        if path.validation_details:
            print(f"\nValidation Details:")
            for key, value in path.validation_details.items():
                print(f"  {key}: {value}")

    print("\n" + "=" * 80)
    print("ANALYSIS")
    print("=" * 80)

    if len(paths) > 1:
        print("\nComparison of Top Paths:")
        print(f"  Best Path Coherence: {paths[0].coherence_score:.3f}")
        print(f"  Average Coherence: {sum(p.coherence_score for p in paths) / len(paths):.3f}")
        print(f"  Coherence Range: {min(p.coherence_score for p in paths):.3f} - {max(p.coherence_score for p in paths):.3f}")

    # Identify common pivot points across paths
    all_pivots = set()
    for path in paths:
        for pivot_idx in path.pivot_points:
            if pivot_idx < len(path.states):
                all_pivots.add(path.states[pivot_idx].year)

    if all_pivots:
        print(f"\nCritical Years (appearing in multiple paths):")
        for year in sorted(all_pivots):
            count = sum(1 for path in paths if year in [path.states[idx].year for idx in path.pivot_points if idx < len(path.states)])
            print(f"  {year}: Pivot in {count}/{len(paths)} paths")

    print("\n" + "=" * 80)
    print("INSIGHTS")
    print("=" * 80)

    print("""
This backward simulation reveals:

1. PLAUSIBLE PATHWAYS: Multiple routes exist from tech VP → President
   - Different combinations of political experience, visibility, timing
   - Some paths more direct (early political entry), others gradual

2. PIVOT POINTS: Critical decision moments where paths diverge
   - Early career choice (stay in tech vs enter politics)
   - Public visibility events (book, viral moment, crisis response)
   - Political infrastructure (fundraising, coalition building)

3. CAPABILITY REQUIREMENTS: What John Doe needs to develop
   - Public speaking and media skills
   - Policy expertise (climate, economy, tech regulation)
   - Political network and donor relationships
   - Crisis management and leadership experience

4. TEMPORAL DEPENDENCIES: Order matters
   - Can't run for President without prior credibility
   - Building name recognition takes years
   - Policy expertise requires study and engagement
   - Network effects accelerate over time

5. HISTORICAL PATTERNS: Similar trajectories in history
   - Businessman → Governor → President
   - Tech entrepreneur → Philanthropist → Politician
   - Media personality → Political candidate
    """)

    return paths


if __name__ == "__main__":
    # Run the example
    paths = example_presidential_election_portal()

    if paths:
        print(f"\n{'=' * 80}")
        print(f"EXAMPLE COMPLETE: Generated {len(paths)} plausible paths")
        print(f"{'=' * 80}\n")
    else:
        print("\nNo paths generated. Enable LLM service for better results:")
        print("  export LLM_SERVICE_ENABLED=true")
        print("  python examples/portal_presidential_election.py\n")
