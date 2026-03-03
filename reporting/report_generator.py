"""
Report Generator for Multi-Format Report Generation

Generates comprehensive reports from simulation data including:
- Summary reports (high-level overview)
- Relationship reports (entity interactions)
- Knowledge reports (information flow)
- Timeline reports (chronological events)
"""

from datetime import datetime, timezone
from typing import Any

from .formatters import FormatterFactory
from .query_engine import EnhancedQueryEngine


class ReportGenerator:
    """
    Generate comprehensive reports from simulation data.

    Example:
        from reporting import ReportGenerator, EnhancedQueryEngine
        from query_interface import QueryInterface

        base_query = QueryInterface(llm_client, graph_store)
        engine = EnhancedQueryEngine(base_query)
        generator = ReportGenerator(engine)

        # Generate summary report
        report = generator.generate_summary_report(
            world_id="meeting_001",
            format="markdown"
        )

        # Generate relationship report
        report = generator.generate_relationship_report(
            world_id="meeting_001",
            entity_ids=["alice", "bob"],
            format="json"
        )
    """

    def __init__(self, query_engine: EnhancedQueryEngine):
        """
        Args:
            query_engine: EnhancedQueryEngine instance for data queries
        """
        self.query_engine = query_engine

    def generate_summary_report(
        self,
        world_id: str,
        format: str = "markdown",
        include_stats: bool = True,
        **formatter_kwargs,
    ) -> str:
        """
        Generate high-level summary report.

        Args:
            world_id: World identifier
            format: Output format (markdown, json, csv)
            include_stats: Whether to include statistics
            **formatter_kwargs: Additional arguments for formatter

        Returns:
            Formatted report string
        """
        # Get timeline summary
        timeline = self.query_engine.timeline_summary(world_id, include_minor_events=False)

        # Build report data structure
        data = {
            "title": f"Simulation Summary: {world_id}",
            "metadata": {
                "world_id": world_id,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "report_type": "summary",
            },
            "summary": self._generate_narrative_summary(timeline),
            "sections": [],
        }

        # Add key moments section
        if timeline.get("key_moments"):
            key_moments_section = {
                "title": "Key Moments",
                "items": [
                    f"Timepoint {moment['timepoint']}: {moment['description']}"
                    for moment in timeline["key_moments"]
                ],
            }
            data["sections"].append(key_moments_section)

        # Add statistics section if requested
        if include_stats:
            stats_section = self._build_stats_section(world_id, timeline)
            data["sections"].append(stats_section)

        # Add timeline table
        if timeline.get("events"):
            timeline_table = {
                "title": "Timeline Overview",
                "headers": ["Timepoint", "Event Type", "Description", "Importance"],
                "rows": [
                    [
                        event["timepoint"],
                        event["type"],
                        event["description"],
                        f"{event['importance']:.2f}",
                    ]
                    for event in timeline["events"]
                ],
            }
            data["tables"] = [timeline_table]

        # Format and return
        formatter = FormatterFactory.create(format, **formatter_kwargs)
        return formatter.format(data)

    def generate_relationship_report(
        self,
        world_id: str,
        entity_ids: list[str] | None = None,
        format: str = "markdown",
        **formatter_kwargs,
    ) -> str:
        """
        Generate relationship analysis report.

        Args:
            world_id: World identifier
            entity_ids: Optional list of entity IDs to focus on
            format: Output format (markdown, json, csv)
            **formatter_kwargs: Additional arguments for formatter

        Returns:
            Formatted report string
        """
        # Get relationship data
        relationships = self.query_engine.summarize_relationships(
            world_id, entity_filter=entity_ids
        )

        # Build report data structure
        data = {
            "title": f"Relationship Analysis: {world_id}",
            "metadata": {
                "world_id": world_id,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "report_type": "relationships",
                "entity_filter": entity_ids,
            },
            "summary": self._generate_relationship_summary(relationships),
            "sections": [],
        }

        # Add relationship stats section
        if relationships.get("summary_stats"):
            stats = relationships["summary_stats"]
            stats_section = {
                "title": "Relationship Statistics",
                "content": f"""
Total Relationships: {stats.get("total_relationships", 0)}
Average Strength: {stats.get("avg_strength", 0):.2f}
Relationship Types: {", ".join(stats.get("relationship_types", []))}
""",
            }
            data["sections"].append(stats_section)

        # Add relationship table
        if relationships.get("entity_pairs"):
            relationship_table = {
                "title": "Entity Relationships",
                "headers": ["Entity 1", "Entity 2", "Relationship Type", "Strength"],
                "rows": [
                    [pair["entity1"], pair["entity2"], pair["type"], f"{pair['strength']:.2f}"]
                    for pair in relationships["entity_pairs"]
                ],
            }
            data["tables"] = [relationship_table]

        # Format and return
        formatter = FormatterFactory.create(format, **formatter_kwargs)
        return formatter.format(data)

    def generate_knowledge_report(
        self,
        world_id: str,
        timepoint_range: tuple | None = None,
        format: str = "markdown",
        **formatter_kwargs,
    ) -> str:
        """
        Generate knowledge flow analysis report.

        Args:
            world_id: World identifier
            timepoint_range: Optional (start, end) timepoint range
            format: Output format (markdown, json, csv)
            **formatter_kwargs: Additional arguments for formatter

        Returns:
            Formatted report string
        """
        # Get knowledge flow data
        knowledge_flow = self.query_engine.knowledge_flow_graph(
            world_id, timepoint_range=timepoint_range
        )

        # Build report data structure
        data = {
            "title": f"Knowledge Flow Analysis: {world_id}",
            "metadata": {
                "world_id": world_id,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "report_type": "knowledge_flow",
                "timepoint_range": timepoint_range,
            },
            "summary": self._generate_knowledge_summary(knowledge_flow),
            "sections": [],
        }

        # Add flow metrics section
        if knowledge_flow.get("flow_metrics"):
            metrics = knowledge_flow["flow_metrics"]
            metrics_section = {
                "title": "Knowledge Flow Metrics",
                "content": f"""
Total Knowledge Transfers: {metrics.get("total_transfers", 0)}
Average Hops: {metrics.get("avg_hops", 0):.2f}
Knowledge Items: {", ".join(metrics.get("knowledge_items", []))}
""",
            }
            data["sections"].append(metrics_section)

        # Add knowledge flow table
        if knowledge_flow.get("edges"):
            flow_table = {
                "title": "Knowledge Transfer Events",
                "headers": ["Source", "Target", "Knowledge Item", "Timepoint"],
                "rows": [
                    [edge["source"], edge["target"], edge["knowledge"], edge["timepoint"]]
                    for edge in knowledge_flow["edges"]
                ],
            }
            data["tables"] = [flow_table]

        # Format and return
        formatter = FormatterFactory.create(format, **formatter_kwargs)
        return formatter.format(data)

    def generate_entity_comparison_report(
        self,
        world_id: str,
        entity_ids: list[str],
        aspects: list[str] | None = None,
        format: str = "markdown",
        **formatter_kwargs,
    ) -> str:
        """
        Generate entity comparison report.

        Args:
            world_id: World identifier
            entity_ids: List of entity IDs to compare
            aspects: Optional aspects to compare (personality, knowledge, relationships)
            format: Output format (markdown, json, csv)
            **formatter_kwargs: Additional arguments for formatter

        Returns:
            Formatted report string
        """
        # Get comparison data
        comparison = self.query_engine.entity_comparison(world_id, entity_ids, aspects=aspects)

        # Build report data structure
        data = {
            "title": f"Entity Comparison: {world_id}",
            "metadata": {
                "world_id": world_id,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "report_type": "entity_comparison",
                "entities": entity_ids,
                "aspects": aspects or ["personality", "knowledge", "relationships"],
            },
            "summary": self._generate_comparison_summary(comparison),
            "sections": [],
        }

        # Add comparison sections for each aspect
        if comparison.get("comparison_table"):
            for aspect, aspect_data in comparison["comparison_table"].items():
                section = {
                    "title": f"{aspect.title()} Comparison",
                    "content": self._format_comparison_aspect(aspect, aspect_data, entity_ids),
                }
                data["sections"].append(section)

        # Add similarity scores table
        if comparison.get("similarity_scores"):
            similarity_table = {
                "title": "Entity Similarity Scores",
                "headers": ["Entity 1", "Entity 2", "Similarity"],
                "rows": [
                    [pair[0], pair[1], f"{score:.2f}"]
                    for pair, score in comparison["similarity_scores"].items()
                ],
            }
            data["tables"] = [similarity_table]

        # Format and return
        formatter = FormatterFactory.create(format, **formatter_kwargs)
        return formatter.format(data)

    def _generate_narrative_summary(self, timeline: dict[str, Any]) -> str:
        """Generate narrative summary from timeline data"""
        event_count = len(timeline.get("events", []))
        key_moment_count = len(timeline.get("key_moments", []))

        summary = f"This simulation contains {event_count} events"
        if key_moment_count > 0:
            summary += f", with {key_moment_count} identified as key moments"
        summary += "."

        if timeline.get("narrative_arc"):
            arc = timeline["narrative_arc"]
            peak = arc.get("peak_moment", "unknown")
            summary += f" The narrative tension peaks at timepoint {peak}."

        return summary

    def _generate_relationship_summary(self, relationships: dict[str, Any]) -> str:
        """Generate relationship summary"""
        stats = relationships.get("summary_stats", {})
        total = stats.get("total_relationships", 0)
        avg_strength = stats.get("avg_strength", 0)

        return (
            f"Analysis identified {total} relationships "
            f"with an average strength of {avg_strength:.2f}."
        )

    def _generate_knowledge_summary(self, knowledge_flow: dict[str, Any]) -> str:
        """Generate knowledge flow summary"""
        metrics = knowledge_flow.get("flow_metrics", {})
        transfers = metrics.get("total_transfers", 0)
        items = len(metrics.get("knowledge_items", []))

        return (
            f"Tracked {transfers} knowledge transfer events "
            f"involving {items} distinct knowledge items."
        )

    def _generate_comparison_summary(self, comparison: dict[str, Any]) -> str:
        """Generate entity comparison summary"""
        entity_count = len(comparison.get("entity_ids", []))
        aspect_count = len(comparison.get("aspects", []))

        return f"Comparing {entity_count} entities across {aspect_count} aspects."

    def _build_stats_section(self, world_id: str, timeline: dict[str, Any]) -> dict[str, Any]:
        """Build statistics section"""
        event_count = len(timeline.get("events", []))
        key_moment_count = len(timeline.get("key_moments", []))

        return {
            "title": "Statistics",
            "items": [
                f"Total Events: {event_count}",
                f"Key Moments: {key_moment_count}",
                f"World ID: {world_id}",
            ],
        }

    def _format_comparison_aspect(
        self, aspect: str, aspect_data: dict[str, Any], entity_ids: list[str]
    ) -> str:
        """Format comparison aspect data"""
        lines = []
        for entity_id in entity_ids:
            if entity_id in aspect_data:
                entity_data = aspect_data[entity_id]
                if isinstance(entity_data, dict):
                    lines.append(f"\n**{entity_id}:**")
                    for key, value in entity_data.items():
                        lines.append(f"  - {key}: {value}")
                elif isinstance(entity_data, list):
                    lines.append(f"\n**{entity_id}:** {', '.join(str(x) for x in entity_data)}")
                else:
                    lines.append(f"\n**{entity_id}:** {entity_data}")
        return "\n".join(lines)
