"""
Archetype Seed Tensors (Phase 7: Tensor Resolution)
====================================================

Pre-built tensors for common character archetypes that can be seeded into
the database to enable immediate tensor resolution for new entities.

IMPORTANT: Archetype tensors are generated through the REAL Timepoint tensor
pipeline (baseline -> LLM population -> training), NOT hardcoded values.

These archetypes represent common patterns:
- Corporate: CEO, CFO, Board Member, Manager
- Detective/Investigation: Detective, Investigator, Witness
- Historical: Diplomat, Statesman, Revolutionary
- Medical: Doctor, Nurse, Administrator
- Generic: Leader, Follower, Neutral

Each archetype has:
- Description for semantic matching
- Category for filtering
- Entity metadata template for tensor generation
"""

import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import json
import base64

from schemas import TTMTensor, Entity
from tensor_persistence import TensorDatabase, TensorRecord
from tensor_serialization import serialize_tensor


@dataclass
class ArchetypeSeed:
    """
    Seed template for an archetype tensor.

    NOTE: This no longer contains hardcoded tensor values. Instead, it contains
    the metadata needed to generate a tensor through the real pipeline.

    Attributes:
        archetype_id: Unique identifier (e.g., "archetype_ceo")
        name: Human-readable name
        description: Rich description for semantic matching
        category: Category path for filtering
        role: Role name for LLM population
        background: Background info for LLM population
        tags: Additional tags for matching
        personality_hints: Optional hints for personality traits
    """
    archetype_id: str
    name: str
    description: str
    category: str
    role: str
    background: str
    tags: List[str]
    personality_hints: Dict[str, float] = field(default_factory=dict)

    def to_entity_metadata(self) -> Dict[str, Any]:
        """Convert archetype to entity metadata for tensor generation."""
        return {
            "role": self.role,
            "description": self.description,
            "background": self.background,
            "archetype_id": self.archetype_id,
            "archetype_name": self.name,
            "personality_traits": list(self.personality_hints.values()) if self.personality_hints else [],
            # Physical defaults for human archetypes
            "physical_tensor": {
                "age": 40.0,  # Default middle-aged
                "health_status": 0.8,
                "pain_level": 0.0,
                "stamina": 0.8
            }
        }


# =============================================================================
# Corporate Archetypes
# =============================================================================

CORPORATE_ARCHETYPES = [
    ArchetypeSeed(
        archetype_id="archetype_ceo",
        name="Chief Executive Officer",
        role="CEO",
        description="CEO - Top executive leader who drives company vision and strategy. "
                   "High confidence, decisive, charismatic. Comfortable with risk and "
                   "high-pressure decisions. Strong communication skills, politically "
                   "savvy, results-oriented. Often has significant experience and wisdom.",
        background="Has risen through corporate ranks to lead organizations. Experienced "
                   "in managing boards, investors, and stakeholders. Makes high-stakes "
                   "decisions daily and is accountable for company performance.",
        category="corporate/executive",
        tags=["executive", "leader", "decision-maker", "corporate"],
        personality_hints={
            "openness": 0.7,
            "conscientiousness": 0.9,
            "extraversion": 0.85,
            "agreeableness": 0.5,
            "neuroticism": 0.3
        }
    ),
    ArchetypeSeed(
        archetype_id="archetype_cfo",
        name="Chief Financial Officer",
        role="CFO",
        description="CFO - Financial executive responsible for fiscal management and "
                   "financial strategy. Highly analytical, risk-aware, detail-oriented. "
                   "Conservative approach to decisions, data-driven. Strong numerical "
                   "reasoning, cautious about expenditures.",
        background="Background in finance, accounting, or investment banking. Has managed "
                   "large budgets and financial planning. Values precision and accuracy.",
        category="corporate/executive",
        tags=["executive", "financial", "analytical", "corporate"],
        personality_hints={
            "openness": 0.5,
            "conscientiousness": 0.95,
            "extraversion": 0.6,
            "agreeableness": 0.55,
            "neuroticism": 0.4
        }
    ),
    ArchetypeSeed(
        archetype_id="archetype_board_member",
        name="Board Member",
        role="Board Director",
        description="Board Director - Experienced business person serving on corporate "
                   "board. Provides governance and strategic oversight. Measured, "
                   "deliberate decision-making. Questions management, seeks clarity, "
                   "fiduciary responsibility mindset.",
        background="Successful business career with multiple board experiences. Values "
                   "due diligence and shareholder interests. Experienced in governance.",
        category="corporate/governance",
        tags=["governance", "oversight", "strategic", "corporate"],
        personality_hints={
            "openness": 0.6,
            "conscientiousness": 0.85,
            "extraversion": 0.65,
            "agreeableness": 0.6,
            "neuroticism": 0.35
        }
    ),
    ArchetypeSeed(
        archetype_id="archetype_manager",
        name="Middle Manager",
        role="Department Manager",
        description="Department Manager - Manages team operations and implements "
                   "executive strategy. Balances upward accountability with team "
                   "leadership. Practical, organized, people-focused. Moderate "
                   "risk tolerance, collaborative.",
        background="Has team leadership experience and operational expertise. Bridges "
                   "gap between executive vision and day-to-day execution.",
        category="corporate/management",
        tags=["manager", "team-lead", "operational", "corporate"],
        personality_hints={
            "openness": 0.55,
            "conscientiousness": 0.8,
            "extraversion": 0.7,
            "agreeableness": 0.7,
            "neuroticism": 0.45
        }
    ),
]


# =============================================================================
# Detective/Investigation Archetypes
# =============================================================================

DETECTIVE_ARCHETYPES = [
    ArchetypeSeed(
        archetype_id="archetype_detective",
        name="Detective",
        role="Detective",
        description="Detective investigator - Skilled in observation, deduction, and "
                   "interrogation. Patient, methodical, notices details others miss. "
                   "Skeptical by nature, persistent. May be somewhat socially reserved "
                   "but can read people well. Analytical mind.",
        background="Years of investigative experience. Has solved complex cases through "
                   "careful observation and logical deduction. Trained to notice "
                   "inconsistencies and pursue truth relentlessly.",
        category="investigation/detective",
        tags=["investigator", "detective", "analytical", "observant"],
        personality_hints={
            "openness": 0.75,
            "conscientiousness": 0.85,
            "extraversion": 0.5,
            "agreeableness": 0.45,
            "neuroticism": 0.4
        }
    ),
    ArchetypeSeed(
        archetype_id="archetype_witness",
        name="Witness",
        role="Witness",
        description="Witness to events - Has observed something important. May be "
                   "nervous, uncertain about details, or reluctant to speak. Variable "
                   "reliability. Defensive or cooperative depending on circumstances. "
                   "Personal stake in outcome unknown.",
        background="An ordinary person who happened to observe relevant events. May have "
                   "partial information or uncertain memories. Could be helpful or "
                   "hesitant to get involved.",
        category="investigation/witness",
        tags=["witness", "observer", "testimony", "uncertain"],
        personality_hints={
            "openness": 0.5,
            "conscientiousness": 0.6,
            "extraversion": 0.45,
            "agreeableness": 0.6,
            "neuroticism": 0.6
        }
    ),
    ArchetypeSeed(
        archetype_id="archetype_forensic_expert",
        name="Forensic Expert",
        role="Forensic Specialist",
        description="Forensic specialist - Scientific expert providing technical analysis. "
                   "Highly precise, data-driven, objective. Communicates in technical terms. "
                   "Reserved personality, focused on evidence and facts.",
        background="Advanced scientific training and forensic certification. Processes "
                   "evidence methodically and provides expert testimony. Values objectivity.",
        category="investigation/expert",
        tags=["expert", "forensic", "scientific", "technical"],
        personality_hints={
            "openness": 0.8,
            "conscientiousness": 0.95,
            "extraversion": 0.35,
            "agreeableness": 0.5,
            "neuroticism": 0.3
        }
    ),
]


# =============================================================================
# Historical/Political Archetypes
# =============================================================================

HISTORICAL_ARCHETYPES = [
    ArchetypeSeed(
        archetype_id="archetype_diplomat",
        name="Diplomat",
        role="Diplomat",
        description="Diplomatic negotiator - Skilled in international relations and "
                   "negotiation. Highly articulate, culturally aware, patient. Seeks "
                   "compromise and mutual benefit. Excellent at reading political "
                   "dynamics and navigating complex relationships.",
        background="Career diplomat with experience in international negotiations. "
                   "Understands cultural nuances and the art of compromise. Values "
                   "long-term relationships over short-term wins.",
        category="historical/political",
        tags=["diplomat", "negotiator", "political", "international"],
        personality_hints={
            "openness": 0.75,
            "conscientiousness": 0.85,
            "extraversion": 0.75,
            "agreeableness": 0.8,
            "neuroticism": 0.3
        }
    ),
    ArchetypeSeed(
        archetype_id="archetype_statesman",
        name="Statesman",
        role="Elder Statesman",
        description="Elder statesman - Experienced political leader with historical "
                   "perspective. Wise, measured, thoughtful. Values legacy and principle "
                   "over short-term gains. Respected voice of experience.",
        background="Long career in public service with historical achievements. Offers "
                   "wisdom gained from decades of political experience. Seen as an "
                   "authoritative voice on important matters.",
        category="historical/political",
        tags=["statesman", "leader", "political", "historical"],
        personality_hints={
            "openness": 0.7,
            "conscientiousness": 0.9,
            "extraversion": 0.65,
            "agreeableness": 0.7,
            "neuroticism": 0.25
        }
    ),
    ArchetypeSeed(
        archetype_id="archetype_revolutionary",
        name="Revolutionary",
        role="Revolutionary Leader",
        description="Revolutionary activist - Passionate advocate for dramatic change. "
                   "High conviction, willing to take risks for ideals. May be impatient "
                   "with incremental progress. Charismatic, persuasive, driven by vision.",
        background="Has dedicated life to a cause, willing to sacrifice for ideals. "
                   "Inspires others with passionate rhetoric and unwavering commitment. "
                   "May be seen as hero or troublemaker depending on perspective.",
        category="historical/political",
        tags=["revolutionary", "activist", "idealist", "change-maker"],
        personality_hints={
            "openness": 0.9,
            "conscientiousness": 0.7,
            "extraversion": 0.85,
            "agreeableness": 0.4,
            "neuroticism": 0.5
        }
    ),
]


# =============================================================================
# Medical Archetypes
# =============================================================================

MEDICAL_ARCHETYPES = [
    ArchetypeSeed(
        archetype_id="archetype_doctor",
        name="Physician",
        role="Medical Doctor",
        description="Medical doctor - Healthcare professional with diagnostic expertise. "
                   "Analytical, empathetic, decisive in emergencies. Balances science "
                   "with patient care. May show emotional detachment as professional "
                   "coping mechanism.",
        background="Extensive medical training and clinical experience. Makes life and "
                   "death decisions regularly. Trained to remain calm under pressure "
                   "while providing compassionate care.",
        category="medical/clinical",
        tags=["doctor", "physician", "medical", "clinical"],
        personality_hints={
            "openness": 0.75,
            "conscientiousness": 0.9,
            "extraversion": 0.6,
            "agreeableness": 0.65,
            "neuroticism": 0.35
        }
    ),
    ArchetypeSeed(
        archetype_id="archetype_nurse",
        name="Nurse",
        role="Clinical Nurse",
        description="Clinical nurse - Hands-on patient care provider. High empathy, "
                   "observant, practical. Works under pressure, advocates for patients. "
                   "Team-oriented, communicative, detail-conscious.",
        background="Clinical nursing experience with direct patient care. First line "
                   "of patient observation and care. Strong advocate for patient "
                   "wellbeing and comfort.",
        category="medical/clinical",
        tags=["nurse", "caregiver", "medical", "clinical"],
        personality_hints={
            "openness": 0.6,
            "conscientiousness": 0.85,
            "extraversion": 0.7,
            "agreeableness": 0.8,
            "neuroticism": 0.45
        }
    ),
    ArchetypeSeed(
        archetype_id="archetype_hospital_admin",
        name="Hospital Administrator",
        role="Healthcare Administrator",
        description="Healthcare administrator - Manages hospital operations and policy. "
                   "Balances patient care with financial realities. Politically aware, "
                   "organized, handles competing priorities.",
        background="Background in healthcare management. Navigates complex healthcare "
                   "regulations while maintaining operational efficiency. Balances "
                   "multiple stakeholder interests.",
        category="medical/administration",
        tags=["administrator", "hospital", "management", "healthcare"],
        personality_hints={
            "openness": 0.55,
            "conscientiousness": 0.85,
            "extraversion": 0.7,
            "agreeableness": 0.55,
            "neuroticism": 0.4
        }
    ),
]


# =============================================================================
# Generic Archetypes
# =============================================================================

GENERIC_ARCHETYPES = [
    ArchetypeSeed(
        archetype_id="archetype_leader",
        name="Natural Leader",
        role="Leader",
        description="Natural leader personality - Takes charge in group situations. "
                   "Confident, decisive, communicative. Others look to them for direction. "
                   "Comfortable with responsibility and making difficult decisions.",
        background="Has natural charisma and leadership ability. Instinctively takes "
                   "charge in ambiguous situations. Inspires confidence in others.",
        category="generic/personality",
        tags=["leader", "personality", "generic"],
        personality_hints={
            "openness": 0.7,
            "conscientiousness": 0.8,
            "extraversion": 0.85,
            "agreeableness": 0.55,
            "neuroticism": 0.3
        }
    ),
    ArchetypeSeed(
        archetype_id="archetype_follower",
        name="Supportive Follower",
        role="Team Member",
        description="Supportive follower - Prefers to support rather than lead. "
                   "Reliable, consistent, team-oriented. Values harmony and stability. "
                   "Good at executing plans others create.",
        background="Prefers collaborative roles to leadership positions. Reliable "
                   "team member who values stability and clear direction. Gets "
                   "satisfaction from supporting team success.",
        category="generic/personality",
        tags=["follower", "supportive", "personality", "generic"],
        personality_hints={
            "openness": 0.45,
            "conscientiousness": 0.85,
            "extraversion": 0.5,
            "agreeableness": 0.8,
            "neuroticism": 0.5
        }
    ),
    ArchetypeSeed(
        archetype_id="archetype_neutral",
        name="Neutral Observer",
        role="Observer",
        description="Neutral observer - Balanced personality without strong tendencies. "
                   "Can adapt to different situations. Neither dominant nor submissive. "
                   "Baseline human characteristics.",
        background="An average person without extreme traits in any direction. "
                   "Adaptable to various situations and roles. Represents typical "
                   "human baseline.",
        category="generic/baseline",
        tags=["neutral", "baseline", "generic"],
        personality_hints={
            "openness": 0.5,
            "conscientiousness": 0.5,
            "extraversion": 0.5,
            "agreeableness": 0.5,
            "neuroticism": 0.5
        }
    ),
]


# =============================================================================
# Aggregated Collections
# =============================================================================

ALL_ARCHETYPES: List[ArchetypeSeed] = (
    CORPORATE_ARCHETYPES +
    DETECTIVE_ARCHETYPES +
    HISTORICAL_ARCHETYPES +
    MEDICAL_ARCHETYPES +
    GENERIC_ARCHETYPES
)


def get_archetype_by_id(archetype_id: str) -> Optional[ArchetypeSeed]:
    """Get archetype by ID."""
    for archetype in ALL_ARCHETYPES:
        if archetype.archetype_id == archetype_id:
            return archetype
    return None


def get_archetypes_by_category(category_prefix: str) -> List[ArchetypeSeed]:
    """Get all archetypes matching category prefix."""
    return [a for a in ALL_ARCHETYPES if a.category.startswith(category_prefix)]


# =============================================================================
# Tensor Generation Through Real Pipeline
# =============================================================================

def create_archetype_entity(archetype: ArchetypeSeed) -> Entity:
    """
    Create a temporary Entity object from an archetype for tensor generation.

    This entity will be passed through the real Timepoint tensor pipeline.
    """
    return Entity(
        entity_id=archetype.archetype_id,
        entity_type="human",
        temporal_span_start=None,
        temporal_span_end=None,
        resolution_level=None,
        entity_metadata=archetype.to_entity_metadata()
    )


def generate_archetype_tensor(
    archetype: ArchetypeSeed,
    llm_client: Any,
    include_training: bool = False,
    verbose: bool = True
) -> Tuple[TTMTensor, float]:
    """
    Generate tensor for a single archetype through the REAL Timepoint pipeline.

    This is the CORRECT way to create archetype tensors - through the same
    LLM-guided process used for real entities.

    Args:
        archetype: ArchetypeSeed to generate tensor for
        llm_client: LLM client for population
        include_training: Whether to run training to maturity (slower)
        verbose: Print progress

    Returns:
        (tensor, maturity) tuple
    """
    import networkx as nx
    from tensor_initialization import (
        create_baseline_tensor,
        populate_tensor_llm_guided,
        compute_tensor_maturity
    )
    from schemas import Timepoint

    if verbose:
        print(f"  Generating tensor for {archetype.name}...")

    # Step 1: Create entity from archetype
    entity = create_archetype_entity(archetype)

    # Step 2: Create baseline tensor (instant, no LLM)
    tensor = create_baseline_tensor(entity)

    # Serialize and store on entity for population
    entity.tensor = json.dumps({
        "context_vector": base64.b64encode(
            __import__('msgspec').msgpack.encode(tensor.to_arrays()[0].tolist())
        ).decode('utf-8'),
        "biology_vector": base64.b64encode(
            __import__('msgspec').msgpack.encode(tensor.to_arrays()[1].tolist())
        ).decode('utf-8'),
        "behavior_vector": base64.b64encode(
            __import__('msgspec').msgpack.encode(tensor.to_arrays()[2].tolist())
        ).decode('utf-8')
    })
    entity.tensor_maturity = 0.0
    entity.tensor_training_cycles = 0

    # Step 3: LLM-guided population (3 loops)
    # Create minimal graph for population
    graph = nx.Graph()
    graph.add_node(archetype.archetype_id)

    # Create minimal timepoint
    timepoint = Timepoint(
        timepoint_id="archetype_generation",
        datetime_iso="2024-01-01T00:00:00Z",
        timepoint_description="Archetype tensor generation"
    )

    try:
        refined_tensor, maturity = populate_tensor_llm_guided(
            entity, timepoint, graph, llm_client
        )

        if verbose:
            print(f"    -> Populated with maturity: {maturity:.2f}")

    except Exception as e:
        if verbose:
            print(f"    -> Population failed: {e}, using baseline")
        refined_tensor = tensor
        maturity = compute_tensor_maturity(tensor, entity, training_complete=False)

    # Step 4: Optional training (expensive)
    if include_training:
        try:
            from tensor_initialization import train_tensor_to_maturity
            # Would need store - skip for now
            if verbose:
                print(f"    -> Training skipped (requires store)")
        except Exception as e:
            if verbose:
                print(f"    -> Training failed: {e}")

    return refined_tensor, maturity


def generate_all_archetype_tensors(
    llm_client: Any,
    archetypes: Optional[List[ArchetypeSeed]] = None,
    include_training: bool = False,
    verbose: bool = True
) -> Dict[str, Tuple[TTMTensor, float]]:
    """
    Generate tensors for all archetypes through the real pipeline.

    This is the batch version of generate_archetype_tensor().

    Args:
        llm_client: LLM client for population
        archetypes: List of archetypes (defaults to ALL_ARCHETYPES)
        include_training: Whether to run training to maturity
        verbose: Print progress

    Returns:
        Dict mapping archetype_id to (tensor, maturity)
    """
    if archetypes is None:
        archetypes = ALL_ARCHETYPES

    results = {}

    if verbose:
        print(f"\nGenerating tensors for {len(archetypes)} archetypes...")
        print("This uses the REAL Timepoint tensor pipeline (LLM calls).\n")

    for i, archetype in enumerate(archetypes):
        if verbose:
            print(f"[{i+1}/{len(archetypes)}] {archetype.name}")

        try:
            tensor, maturity = generate_archetype_tensor(
                archetype, llm_client, include_training, verbose=False
            )
            results[archetype.archetype_id] = (tensor, maturity)

            if verbose:
                print(f"    -> Success (maturity: {maturity:.2f})")

        except Exception as e:
            if verbose:
                print(f"    -> Failed: {e}")
            results[archetype.archetype_id] = (None, 0.0)

    if verbose:
        successful = sum(1 for t, m in results.values() if t is not None)
        print(f"\nGenerated {successful}/{len(archetypes)} archetype tensors")

    return results


def seed_database_with_archetypes(
    tensor_db: TensorDatabase,
    llm_client: Any,
    archetypes: Optional[List[ArchetypeSeed]] = None,
    world_id: str = "archetype_seeds",
    regenerate: bool = False,
    verbose: bool = True
) -> int:
    """
    Seed database with archetype tensors generated through the REAL pipeline.

    This is the correct way to seed archetypes - generating them through
    the same LLM-guided process used for real entities.

    Args:
        tensor_db: TensorDatabase to seed
        llm_client: LLM client for tensor generation
        archetypes: List of archetypes (defaults to ALL_ARCHETYPES)
        world_id: World ID to assign to seed tensors
        regenerate: If True, regenerate even if already exists
        verbose: Print progress

    Returns:
        Number of archetypes seeded
    """
    if archetypes is None:
        archetypes = ALL_ARCHETYPES

    seeded = 0
    skipped = 0

    if verbose:
        print(f"\nSeeding database with {len(archetypes)} archetypes...")
        print("Using REAL tensor pipeline (LLM calls required).\n")

    for archetype in archetypes:
        # Check if already exists
        if not regenerate:
            existing = tensor_db.get_tensor(archetype.archetype_id)
            if existing is not None:
                if verbose:
                    print(f"  Skip {archetype.name}: already exists")
                skipped += 1
                continue

        if verbose:
            print(f"  Generating {archetype.name}...")

        try:
            # Generate through real pipeline
            tensor, maturity = generate_archetype_tensor(
                archetype, llm_client, include_training=False, verbose=False
            )

            if tensor is None:
                if verbose:
                    print(f"    -> Failed to generate")
                continue

            # Create record
            record = TensorRecord(
                tensor_id=archetype.archetype_id,
                entity_id=archetype.archetype_id,
                world_id=world_id,
                tensor_blob=serialize_tensor(tensor),
                maturity=maturity,
                training_cycles=3,  # LLM population counts as training
                description=archetype.description,
                category=archetype.category,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )

            # Save
            tensor_db.save_tensor(record)
            seeded += 1

            if verbose:
                print(f"    -> Saved (maturity: {maturity:.2f})")

        except Exception as e:
            if verbose:
                print(f"    -> Error: {e}")

    if verbose:
        print(f"\nSeeded {seeded} archetypes, skipped {skipped} existing")

    return seeded


# =============================================================================
# Keyword-based Matching (for quick lookups without semantic search)
# =============================================================================

def get_best_archetype_match(
    role: str,
    entity_type: str,
    description: str = ""
) -> Optional[ArchetypeSeed]:
    """
    Get the best matching archetype based on role and description.

    Simple keyword matching - for semantic matching use TensorRAG.

    Args:
        role: Entity role (e.g., "CEO", "Detective")
        entity_type: Entity type (e.g., "human")
        description: Additional description text

    Returns:
        Best matching archetype or None
    """
    search_text = f"{role} {entity_type} {description}".lower()

    best_match = None
    best_score = 0

    for archetype in ALL_ARCHETYPES:
        score = 0

        # Check name match
        if archetype.name.lower() in search_text:
            score += 3

        # Check role match
        if archetype.role.lower() in search_text:
            score += 3

        # Check tag matches
        for tag in archetype.tags:
            if tag.lower() in search_text:
                score += 1

        # Check description overlap
        archetype_words = set(archetype.description.lower().split())
        search_words = set(search_text.split())
        overlap = len(archetype_words & search_words)
        score += overlap * 0.1

        if score > best_score:
            best_score = score
            best_match = archetype

    return best_match if best_score > 0 else None


# =============================================================================
# Legacy Compatibility (for tests that expect old interface)
# =============================================================================

def archetype_to_tensor(archetype: ArchetypeSeed) -> TTMTensor:
    """
    LEGACY: Create a placeholder tensor from archetype.

    WARNING: This creates a tensor from personality_hints ONLY, not through
    the real pipeline. Use generate_archetype_tensor() for proper tensors.

    This exists only for backward compatibility with tests.
    """
    # Create baseline tensor from hints
    hints = archetype.personality_hints

    # Context: neutral baseline
    context = np.array([0.5, 0.5, 0.5, 0.75, 0.5, 0.5, 0.5, 0.5], dtype=np.float32)

    # Biology: human defaults
    biology = np.array([0.4, 0.8, 0.85, 0.8], dtype=np.float32)

    # Behavior: from personality hints (Big Five + 3)
    if hints:
        behavior = np.array([
            hints.get("openness", 0.5),
            hints.get("conscientiousness", 0.5),
            hints.get("extraversion", 0.5),
            hints.get("agreeableness", 0.5),
            hints.get("neuroticism", 0.5),
            0.5,  # decisiveness
            0.5,  # empathy
            0.5   # analytical
        ], dtype=np.float32)
    else:
        behavior = np.array([0.5] * 8, dtype=np.float32)

    return TTMTensor.from_arrays(context, biology, behavior)
