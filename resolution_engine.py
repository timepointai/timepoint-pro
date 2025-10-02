# ============================================================================
# resolution_engine.py - Variable resolution system for adaptive detail levels
# ============================================================================
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import networkx as nx
from schemas import Entity, Timepoint, ResolutionLevel, ExposureEvent
from storage import GraphStore
from llm import LLMClient


class ResolutionEngine:
    """Decides optimal resolution levels for entities based on multiple factors"""

    def __init__(self, store: GraphStore, llm_client: Optional[LLMClient] = None):
        self.store = store
        self.llm_client = llm_client
        self.query_history: Dict[str, int] = {}  # entity_id -> access count

    def decide_resolution(
        self,
        entity: Entity,
        timepoint: Timepoint,
        graph: Optional[nx.Graph] = None
    ) -> ResolutionLevel:
        """
        Decide detail level for entity at timepoint using multiple signals:

        - Graph centrality (eigenvector centrality)
        - Query history (frequent access = higher resolution)
        - Timepoint importance (key events = higher resolution)
        - Role importance (protagonists > supporting > extras)
        - Temporal recency (recent events more detailed)
        """

        # Base score starts at 0, we add points for each factor
        resolution_score = 0.0
        max_score = 5.0  # Corresponds to TRAINED resolution

        # 1. Graph centrality (0-1 points)
        centrality_score = 0.0
        if graph and entity.entity_id in graph:
            centrality = nx.eigenvector_centrality_numpy(graph)
            centrality_score = centrality.get(entity.entity_id, 0.0)
            resolution_score += centrality_score * 1.0  # Max 1.0 points

        # 2. Query history (0-1 points)
        query_count = self.query_history.get(entity.entity_id, 0)
        if query_count > 0:
            # Logarithmic scaling: 1 query = 0.2, 10 queries = 0.5, 100+ = 1.0
            query_score = min(1.0, (query_count ** 0.5) / 10.0)
            resolution_score += query_score

        # 3. Timepoint importance (0-1 points)
        timepoint_score = self._calculate_timepoint_importance(timepoint)
        resolution_score += timepoint_score

        # 4. Role importance (0-1 points)
        role_score = self._calculate_role_importance(entity)
        resolution_score += role_score

        # 5. Temporal recency (0-0.5 points, bonus for recent events)
        recency_score = self._calculate_temporal_recency(timepoint)
        resolution_score += recency_score

        # Convert score to resolution level
        return self._score_to_resolution(resolution_score, max_score)

    def _calculate_timepoint_importance(self, timepoint: Timepoint) -> float:
        """Rate timepoint importance based on event description and position in chain"""
        importance = 0.0

        # Keywords indicating high importance
        high_importance_keywords = [
            "inauguration", "election", "revolution", "war", "treaty", "declaration",
            "crisis", "summit", "ceremony", "historic", "first", "founding"
        ]

        event_lower = timepoint.event_description.lower()
        for keyword in high_importance_keywords:
            if keyword in event_lower:
                importance += 0.3
                break  # Only count once

        # First timepoint in chain gets bonus (establishment events)
        if timepoint.causal_parent is None:
            importance += 0.2

        # Resolution level already set on timepoint affects importance
        resolution_hierarchy = {
            ResolutionLevel.TENSOR_ONLY: 0.0,
            ResolutionLevel.SCENE: 0.2,
            ResolutionLevel.GRAPH: 0.4,
            ResolutionLevel.DIALOG: 0.6,
            ResolutionLevel.TRAINED: 0.8
        }
        importance += resolution_hierarchy.get(timepoint.resolution_level, 0.0)

        return min(1.0, importance)

    def _calculate_role_importance(self, entity: Entity) -> float:
        """Rate entity importance based on role and metadata"""
        importance = 0.0

        role = entity.entity_metadata.get("role", "").lower()

        # Primary roles get high importance
        primary_roles = ["president", "general", "commander", "leader", "founder"]
        if any(primary_role in role for primary_role in primary_roles):
            importance += 0.6

        # Secondary roles get medium importance
        secondary_roles = ["secretary", "minister", "governor", "ambassador", "delegate"]
        if any(secondary_role in role for secondary_role in secondary_roles):
            importance += 0.4

        # Military/political figures get bonus
        if any(term in role for term in ["general", "colonel", "major", "captain", "politician"]):
            importance += 0.2

        return min(1.0, importance)

    def _calculate_temporal_recency(self, timepoint: Timepoint) -> float:
        """Bonus for more recent timepoints (within last 24 hours simulation time)"""
        # In a real scenario, this would compare to current time
        # For now, give small bonus to maintain some detail in recent events
        return 0.1

    def _score_to_resolution(self, score: float, max_score: float) -> ResolutionLevel:
        """Convert numeric score to resolution level"""
        normalized_score = score / max_score

        if normalized_score < 0.2:
            return ResolutionLevel.TENSOR_ONLY
        elif normalized_score < 0.4:
            return ResolutionLevel.SCENE
        elif normalized_score < 0.6:
            return ResolutionLevel.GRAPH
        elif normalized_score < 0.8:
            return ResolutionLevel.DIALOG
        else:
            return ResolutionLevel.TRAINED

    def record_query(self, entity_id: str) -> None:
        """Record that an entity was queried (increases its resolution priority)"""
        self.query_history[entity_id] = self.query_history.get(entity_id, 0) + 1

    def get_resolution_stats(self) -> Dict[str, int]:
        """Get statistics on current resolution distribution"""
        entities = []  # We'd need to get all entities from store

        # This is a placeholder - in real implementation, we'd query all entities
        stats = {
            ResolutionLevel.TENSOR_ONLY.value: 0,
            ResolutionLevel.SCENE.value: 0,
            ResolutionLevel.GRAPH.value: 0,
            ResolutionLevel.DIALOG.value: 0,
            ResolutionLevel.TRAINED.value: 0
        }

        # Count would go here...

        return stats

    def check_retraining_needed(self, entity: Entity, graph: Optional[nx.Graph] = None) -> bool:
        """
        Determine if an entity needs retraining/elevation based on:
        - High eigenvector centrality with low training iterations
        - High query count relative to current resolution level
        """
        # Get current centrality (recompute if graph provided, otherwise use stored value)
        centrality = entity.eigenvector_centrality
        if graph and entity.entity_id in graph:
            try:
                centrality = nx.eigenvector_centrality_numpy(graph)[entity.entity_id]
            except:
                # Fallback to stored value if computation fails
                centrality = entity.eigenvector_centrality

        # High centrality + low training iterations = needs retraining
        training_iterations = entity.training_count
        if centrality > 0.3 and training_iterations < 3:
            return True

        # High query count = needs elevation (relative to current resolution)
        query_count = entity.query_count
        current_resolution_value = list(ResolutionLevel).index(entity.resolution_level)

        # Thresholds increase with resolution level
        elevation_thresholds = {
            ResolutionLevel.TENSOR_ONLY: 5,   # Low threshold for basic elevation
            ResolutionLevel.SCENE: 10,        # Medium threshold
            ResolutionLevel.GRAPH: 15,        # Higher threshold
            ResolutionLevel.DIALOG: 25,       # High threshold
            ResolutionLevel.TRAINED: 50       # Very high threshold (max training)
        }

        threshold = elevation_thresholds.get(entity.resolution_level, 10)
        if query_count > threshold and current_resolution_value < len(ResolutionLevel) - 1:
            return True

        return False

    def elevate_resolution(self, entity: Entity, target_resolution: ResolutionLevel, timepoint: Optional[Timepoint] = None) -> bool:
        """
        Attempt to elevate an entity's resolution level and enrich its knowledge.
        Returns True if elevation was successful.
        """
        current_level_value = list(ResolutionLevel).index(entity.resolution_level)
        target_level_value = list(ResolutionLevel).index(target_resolution)

        if target_level_value <= current_level_value:
            return False  # Cannot elevate to same or lower level

        # Elevate the resolution level
        entity.resolution_level = target_resolution

        # Enrich knowledge based on the target resolution level
        if self.llm_client and not self.llm_client.dry_run:
            self._enrich_entity_knowledge(entity, target_resolution, timepoint)
        elif self.llm_client and self.llm_client.dry_run:
            # For dry-run testing, add mock knowledge items
            self._add_mock_knowledge_for_testing(entity, target_resolution)

        # Save the updated entity
        self.store.save_entity(entity)
        print(f"⬆️ Elevated {entity.entity_id} to {target_resolution.value} resolution")
        return True

    def _enrich_entity_knowledge(self, entity: Entity, target_resolution: ResolutionLevel, timepoint: Optional[Timepoint] = None) -> None:
        """
        Generate additional knowledge for an entity when it elevates to a higher resolution level.
        """
        existing_knowledge = entity.entity_metadata.get("knowledge_state", [])

        if not existing_knowledge:
            return  # No existing knowledge to build upon

        # Determine how many new knowledge items to generate based on target resolution
        knowledge_growth = {
            ResolutionLevel.SCENE: 3,      # Add 3 items when going to SCENE
            ResolutionLevel.GRAPH: 5,      # Add 5 items when going to GRAPH
            ResolutionLevel.DIALOG: 8,     # Add 8 items when going to DIALOG
            ResolutionLevel.TRAINED: 12    # Add 12 items when going to TRAINED
        }

        num_new_items = knowledge_growth.get(target_resolution, 3)

        # Create context for LLM knowledge generation
        context = {
            "entity_id": entity.entity_id,
            "role": entity.entity_metadata.get("role", "unknown"),
            "existing_knowledge": existing_knowledge[:10],  # Use first 10 items as context
            "target_resolution": target_resolution.value,
            "timepoint_context": timepoint.event_description if timepoint else "general context"
        }

        # Generate enrichment prompt
        prompt = f"""Based on the existing knowledge about {entity.entity_id} (role: {context['role']}), generate {num_new_items} additional specific knowledge items that would be appropriate for {target_resolution.value}-level detail.

Existing knowledge: {', '.join(context['existing_knowledge'])}

Context: {context['timepoint_context']}

Generate {num_new_items} new, specific knowledge items that deepen the understanding of this entity. Each item should be:
- Historically plausible
- Specific and concrete (not generic)
- Related to the entity's role and existing knowledge
- Appropriate for the level of detail

Return only the knowledge items as a JSON array of strings."""

        try:
            # Use the raw LLM client for text generation (not structured)
            response = self.llm_client.client.chat.completions.create(
                model=self.llm_client.default_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,  # Some creativity for knowledge generation
                max_tokens=500
            )

            # Parse the response
            import json
            response_text = response.choices[0].message.content.strip()

            # Try to extract JSON array
            try:
                # Look for JSON array in the response
                start_idx = response_text.find('[')
                end_idx = response_text.rfind(']') + 1
                if start_idx != -1 and end_idx > start_idx:
                    json_str = response_text[start_idx:end_idx]
                    new_knowledge_items = json.loads(json_str)
                else:
                    # Fallback: split by newlines and clean up
                    new_knowledge_items = [line.strip('- •').strip() for line in response_text.split('\n') if line.strip()]

                # Filter and limit the new knowledge items
                valid_items = [item for item in new_knowledge_items if item and len(item) > 10][:num_new_items]

                if valid_items:
                    # Add new knowledge to entity
                    existing_knowledge.extend(valid_items)
                    entity.entity_metadata["knowledge_state"] = existing_knowledge

                    # Create exposure events for new knowledge
                    exposure_events = []
                    timestamp = timepoint.timestamp if timepoint else datetime.now()

                    for knowledge_item in valid_items:
                        exposure_event = ExposureEvent(
                            entity_id=entity.entity_id,
                            event_type="learned",
                            information=knowledge_item,
                            source="resolution_elevation",
                            timestamp=timestamp
                        )
                        exposure_events.append(exposure_event)

                    # Batch save exposure events
                    if exposure_events:
                        self.store.save_exposure_events(exposure_events)

                    print(f"📚 Added {len(valid_items)} new knowledge items to {entity.entity_id}")

            except (json.JSONDecodeError, ValueError) as e:
                print(f"⚠️ Failed to parse LLM response for knowledge enrichment: {e}")

        except Exception as e:
            print(f"⚠️ Failed to enrich knowledge during elevation: {e}")
            # Continue with elevation even if knowledge enrichment fails

    def _add_mock_knowledge_for_testing(self, entity: Entity, target_resolution: ResolutionLevel) -> None:
        """
        Add mock knowledge items for testing purposes when in dry-run mode.
        """
        existing_knowledge = entity.entity_metadata.get("knowledge_state", [])

        if not existing_knowledge:
            return  # No existing knowledge to build upon

        # Mock knowledge items based on resolution level
        mock_knowledge_templates = {
            ResolutionLevel.SCENE: [
                "Led military campaigns with strategic brilliance",
                "Established key relationships with political allies",
                "Demonstrated leadership under pressure"
            ],
            ResolutionLevel.GRAPH: [
                "Built extensive network of political connections",
                "Influenced major historical decisions",
                "Mentored younger leaders in the movement",
                "Corresponded extensively with contemporaries",
                "Developed key strategic alliances"
            ],
            ResolutionLevel.DIALOG: [
                "Engaged in detailed correspondence about governance",
                "Participated in constitutional debates",
                "Mentored emerging political figures",
                "Negotiated critical diplomatic arrangements",
                "Established precedents for executive leadership",
                "Influenced the formation of government institutions",
                "Contributed to philosophical discussions on liberty",
                "Maintained extensive personal library and studies"
            ],
            ResolutionLevel.TRAINED: [
                "Authored significant political treatises",
                "Established presidential traditions and protocols",
                "Cultivated international diplomatic relationships",
                "Influenced the development of American political parties",
                "Promoted scientific and educational advancement",
                "Established precedents for civilian military control",
                "Contributed to the formation of federal judiciary",
                "Mentored the next generation of American leaders",
                "Developed comprehensive agricultural policies",
                "Promoted manufacturing and industrial development",
                "Established precedents for executive privilege",
                "Influenced westward expansion policies"
            ]
        }

        new_knowledge_items = mock_knowledge_templates.get(target_resolution, [])

        if new_knowledge_items:
            # Add new knowledge to entity
            existing_knowledge.extend(new_knowledge_items)
            entity.entity_metadata["knowledge_state"] = existing_knowledge

            # Create exposure events for new knowledge (even in dry-run for testing)
            exposure_events = []
            timestamp = datetime.now()

            for knowledge_item in new_knowledge_items:
                exposure_event = ExposureEvent(
                    entity_id=entity.entity_id,
                    event_type="learned",
                    information=knowledge_item,
                    source="resolution_elevation_test",
                    timestamp=timestamp
                )
                exposure_events.append(exposure_event)

            # Batch save exposure events
            if exposure_events:
                self.store.save_exposure_events(exposure_events)

            print(f"📚 Added {len(new_knowledge_items)} mock knowledge items to {entity.entity_id} (dry-run)")
