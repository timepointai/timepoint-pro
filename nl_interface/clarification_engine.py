"""
Clarification Engine for NL Interface

Detects ambiguities in natural language descriptions and generates
targeted clarification questions to resolve them before config generation.
"""

import re
from dataclasses import dataclass
from typing import Any


@dataclass
class Clarification:
    """A clarification question with context"""

    field: str
    question: str
    suggestions: list[str]
    priority: int  # 1=critical, 2=important, 3=nice-to-have
    detected_reason: str


class ClarificationEngine:
    """
    Detect ambiguities in natural language descriptions.

    Analyzes user input to identify missing or ambiguous information
    and generates targeted clarification questions.

    Example:
        engine = ClarificationEngine()
        clarifications = engine.detect_ambiguities(
            "Simulate a board meeting"
        )

        for clarification in clarifications:
            print(f"Q: {clarification.question}")
            print(f"Suggestions: {', '.join(clarification.suggestions)}")
    """

    def __init__(self):
        """Initialize clarification engine"""
        # Keywords for detecting scenario types
        self.historical_keywords = {
            "constitutional",
            "convention",
            "apollo",
            "revere",
            "washington",
            "franklin",
            "battle",
            "war",
            "treaty",
        }

        self.business_keywords = {
            "board",
            "meeting",
            "ceo",
            "startup",
            "acquisition",
            "merger",
            "earnings",
            "shareholders",
            "strategy",
        }

        self.crisis_keywords = {
            "crisis",
            "emergency",
            "disaster",
            "accident",
            "failure",
            "explosion",
            "pressure",
            "urgent",
        }

        # Entity count patterns
        self.entity_count_patterns = [
            r"\b(\d+)\s+(people|entities|participants|members|delegates|astronauts|executives)\b",
            r"\bwith\s+(\d+)\s+",
            r"\b(three|four|five|six|seven|eight|nine|ten)\b",
        ]

        # Timepoint count patterns
        self.timepoint_count_patterns = [
            r"\b(\d+)\s+(timepoints?|sessions?|meetings?|moments?)\b",
            r"\bover\s+(\d+)\s+",
        ]

        # Focus area keywords
        self.focus_keywords = {
            "dialog": ["conversation", "dialog", "dialogue", "talking", "speaking", "discussion"],
            "decision_making": ["decision", "choice", "determine", "decide", "judgment"],
            "relationships": ["relationship", "trust", "alliance", "conflict", "rapport"],
            "stress_responses": ["stress", "pressure", "crisis", "emergency", "panic"],
            "knowledge_propagation": [
                "spread",
                "alert",
                "inform",
                "communicate",
                "share information",
            ],
        }

    def detect_ambiguities(
        self, description: str, context: dict[str, Any] | None = None
    ) -> list[Clarification]:
        """
        Detect ambiguities in natural language description.

        Args:
            description: User's natural language description
            context: Optional additional context from conversation

        Returns:
            List of clarifications needed, sorted by priority
        """
        clarifications = []
        description_lower = description.lower()

        # Check for missing entity count
        if not self._has_entity_count(description_lower):
            clarifications.append(
                Clarification(
                    field="entity_count",
                    question="How many entities (people, organizations, etc.) should be in this simulation?",
                    suggestions=[
                        "3-5 for detailed interactions",
                        "10-20 for group dynamics",
                        "20+ for large-scale scenarios",
                    ],
                    priority=1,
                    detected_reason="No explicit entity count found",
                )
            )

        # Check for missing timepoint count
        if not self._has_timepoint_count(description_lower):
            clarifications.append(
                Clarification(
                    field="timepoint_count",
                    question="How many timepoints (moments in time) should be simulated?",
                    suggestions=[
                        "3-5 for quick scenarios",
                        "10-15 for detailed evolution",
                        "20+ for long narratives",
                    ],
                    priority=1,
                    detected_reason="No explicit timepoint count found",
                )
            )

        # Check for missing focus areas
        detected_focus = self._detect_focus_areas(description_lower)
        if not detected_focus:
            clarifications.append(
                Clarification(
                    field="focus",
                    question="What aspects should the simulation focus on?",
                    suggestions=[
                        "dialog - Generate conversations",
                        "decision_making - Track decisions and reasoning",
                        "relationships - Model trust and conflicts",
                        "stress_responses - Model behavior under pressure",
                        "knowledge_propagation - Track information flow",
                    ],
                    priority=2,
                    detected_reason="No clear focus areas detected",
                )
            )

        # Check for missing temporal context (historical scenarios)
        if self._is_historical(description_lower) and not self._has_time_reference(
            description_lower
        ):
            clarifications.append(
                Clarification(
                    field="start_time",
                    question="What specific date/time should this historical scenario start?",
                    suggestions=[
                        "Provide ISO datetime (e.g., '1787-05-25T10:00:00')",
                        "Provide year and time of day",
                    ],
                    priority=2,
                    detected_reason="Historical scenario without specific date",
                )
            )

        # Check for missing temporal mode hints
        if not self._has_temporal_mode_hint(description_lower):
            # Only ask if scenario suggests non-standard causality
            if any(
                keyword in description_lower
                for keyword in ["alternate", "what if", "counterfactual", "branching"]
            ):
                clarifications.append(
                    Clarification(
                        field="temporal_mode",
                        question="What temporal causality mode should be used?",
                        suggestions=[
                            "forward - Standard causal (historical realism)",
                            "branching - Multiple timelines/what-if scenarios",
                            "directorial - Narrative-driven (dramatic coherence)",
                        ],
                        priority=3,
                        detected_reason="Counterfactual language detected",
                    )
                )

        # Check for output preferences
        if not self._has_output_preference(description_lower):
            clarifications.append(
                Clarification(
                    field="outputs",
                    question="What outputs do you want from the simulation?",
                    suggestions=[
                        "dialog - Conversation transcripts",
                        "decisions - Decision points and reasoning",
                        "relationships - Relationship network evolution",
                        "knowledge_flow - Information propagation tracking",
                    ],
                    priority=2,
                    detected_reason="No explicit output preferences",
                )
            )

        # Check for animism requirements (non-human entities)
        if self._needs_animism(description_lower):
            clarifications.append(
                Clarification(
                    field="animism_level",
                    question="This scenario includes non-human entities. What level of animistic modeling?",
                    suggestions=[
                        "0 - No animism (default)",
                        "1 - Basic agency (simple goals)",
                        "2 - Complex agency (emotions, reasoning)",
                        "3 - Full human-like modeling",
                    ],
                    priority=2,
                    detected_reason="Non-human entities detected (horse, ship, organization, etc.)",
                )
            )

        # Check for variation/horizontal generation
        wants_variations = self._wants_variations(description_lower)
        has_variation_count = self._has_variation_count(description_lower)

        if wants_variations and not has_variation_count:
            clarifications.append(
                Clarification(
                    field="variation_count",
                    question="How many variations do you want to generate?",
                    suggestions=[
                        "10-50 for quick exploration",
                        "100-500 for training data",
                        "500-1000 for comprehensive dataset",
                    ],
                    priority=1,
                    detected_reason="Variation/horizontal generation requested",
                )
            )

        # Sort by priority (critical first)
        clarifications.sort(key=lambda c: c.priority)

        return clarifications

    def _has_entity_count(self, description: str) -> bool:
        """Check if description specifies entity count"""
        for pattern in self.entity_count_patterns:
            if re.search(pattern, description, re.IGNORECASE):
                return True
        return False

    def _has_timepoint_count(self, description: str) -> bool:
        """Check if description specifies timepoint count"""
        for pattern in self.timepoint_count_patterns:
            if re.search(pattern, description, re.IGNORECASE):
                return True
        return False

    def _detect_focus_areas(self, description: str) -> set[str]:
        """Detect focus areas from description"""
        detected = set()
        for focus_area, keywords in self.focus_keywords.items():
            if any(keyword in description for keyword in keywords):
                detected.add(focus_area)
        return detected

    def _is_historical(self, description: str) -> bool:
        """Check if description is about historical scenario"""
        # Check for historical keywords
        if any(keyword in description for keyword in self.historical_keywords):
            return True

        # Check for historical date patterns (e.g., "1787", "1970s")
        if re.search(r"\b(1[4-9]\d{2}|20[0-2]\d)\b", description):
            return True

        return False

    def _has_time_reference(self, description: str) -> bool:
        """Check if description has specific time reference"""
        # ISO datetime pattern
        if re.search(r"\d{4}-\d{2}-\d{2}", description):
            return True

        # Year pattern
        if re.search(r"\b(1[4-9]\d{2}|20[0-2]\d)\b", description):
            return True

        return False

    def _has_temporal_mode_hint(self, description: str) -> bool:
        """Check if description hints at temporal mode"""
        forward_hints = ["historical", "realistic", "causal"]
        branching_hints = ["alternate", "what if", "counterfactual", "branching", "timeline"]
        directorial_hints = ["narrative", "dramatic", "story"]

        all_hints = forward_hints + branching_hints + directorial_hints
        return any(hint in description for hint in all_hints)

    def _has_output_preference(self, description: str) -> bool:
        """Check if description specifies output preferences"""
        output_keywords = [
            "want to see",
            "show me",
            "output",
            "generate",
            "dialog",
            "conversation",
            "decision",
            "relationship",
        ]
        return any(keyword in description for keyword in output_keywords)

    def _needs_animism(self, description: str) -> bool:
        """Check if scenario includes non-human entities"""
        animistic_entities = [
            "horse",
            "ship",
            "boat",
            "car",
            "train",
            "plane",
            "organization",
            "company",
            "corporation",
            "building",
            "city",
            "nation",
            "country",
        ]
        return any(entity in description for entity in animistic_entities)

    def _wants_variations(self, description: str) -> bool:
        """Check if user wants to generate variations"""
        variation_keywords = [
            "variation",
            "variations",
            "horizontal",
            "generate many",
            "different versions",
            "multiple scenarios",
        ]
        return any(keyword in description for keyword in variation_keywords)

    def _has_variation_count(self, description: str) -> bool:
        """Check if description specifies variation count"""
        # Pattern like "50 variations" or "generate 100"
        if re.search(r"\b(\d+)\s+(variations?|versions?|scenarios?)\b", description, re.IGNORECASE):
            return True
        if re.search(r"generate\s+(\d+)", description, re.IGNORECASE):
            return True
        return False

    def answer_clarification(
        self, clarification: Clarification, answer: str, description: str
    ) -> str:
        """
        Incorporate clarification answer into description.

        Args:
            clarification: The clarification that was answered
            answer: User's answer
            description: Original description

        Returns:
            Updated description with clarification incorporated
        """
        # Simple append strategy - add answer to description
        # More sophisticated version could parse and integrate better

        if clarification.field == "entity_count":
            return f"{description} Include {answer} entities."

        elif clarification.field == "timepoint_count":
            return f"{description} Simulate {answer} timepoints."

        elif clarification.field == "focus":
            return f"{description} Focus on {answer}."

        elif clarification.field == "start_time":
            return f"{description} Start time: {answer}."

        elif clarification.field == "temporal_mode":
            return f"{description} Use {answer} temporal mode."

        elif clarification.field == "outputs":
            return f"{description} Output: {answer}."

        elif clarification.field == "animism_level":
            return f"{description} Animism level: {answer}."

        elif clarification.field == "variation_count":
            return f"{description} Generate {answer} variations."

        else:
            # Generic append
            return f"{description} {answer}"

    def get_clarification_summary(self, clarifications: list[Clarification]) -> str:
        """
        Get human-readable summary of clarifications needed.

        Args:
            clarifications: List of clarifications

        Returns:
            Summary string
        """
        if not clarifications:
            return "No clarifications needed - description is complete."

        critical = [c for c in clarifications if c.priority == 1]
        important = [c for c in clarifications if c.priority == 2]
        nice_to_have = [c for c in clarifications if c.priority == 3]

        summary = []

        if critical:
            summary.append(f"Critical ({len(critical)}): " + ", ".join(c.field for c in critical))

        if important:
            summary.append(
                f"Important ({len(important)}): " + ", ".join(c.field for c in important)
            )

        if nice_to_have:
            summary.append(
                f"Optional ({len(nice_to_have)}): " + ", ".join(c.field for c in nice_to_have)
            )

        return " | ".join(summary)
