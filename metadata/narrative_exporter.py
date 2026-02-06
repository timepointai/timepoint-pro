"""
Narrative Export System - Generate comprehensive narrative summaries

Generates narrative aggregations of simulation runs in multiple formats:
- Markdown: Human-readable narrative reports
- JSON: Structured machine-readable data
- PDF: Publication-quality documents

Usage:
    exporter = NarrativeExporter()
    data = exporter.collect_run_data(metadata, timepoints, entities, store, training_data, config)
    md_path = exporter.export_markdown(data, output_path, depth="summary")
    json_path = exporter.export_json(data, output_path)
    pdf_path = exporter.export_pdf(data, output_path, depth="summary")
"""

from typing import List, Dict, Optional, Any
from pathlib import Path
from datetime import datetime
from pydantic import BaseModel, Field
import json


# ============================================================================
# Data Models
# ============================================================================

class CharacterProfile(BaseModel):
    """Profile of a single entity/character"""
    entity_id: str
    entity_type: str
    role: Optional[str] = None
    age: Optional[float] = None
    initial_knowledge: List[str] = []
    personality_traits: Optional[List[float]] = None
    knowledge_count: int = 0
    final_energy: Optional[float] = None
    final_emotional_state: Optional[Dict[str, float]] = None


class TimelineEntry(BaseModel):
    """Single timepoint in narrative timeline"""
    timepoint_id: str
    timestamp: Optional[str] = None
    event_description: str
    entities_present: List[str] = []
    dialog_turn_count: int = 0
    importance: float = 0.5
    causal_parent: Optional[str] = None  # Parent timepoint for convergence analysis


class DialogExcerpt(BaseModel):
    """Excerpt from a dialog conversation"""
    dialog_id: str
    timepoint_id: str
    participants: List[str]
    turns: List[Dict[str, Any]]  # Full turn data
    duration_seconds: Optional[int] = None


class TrainingInsights(BaseModel):
    """Summary of training data generated"""
    total_examples: int = 0
    energy_dynamics: Dict[str, Any] = Field(default_factory=dict)
    emotional_dynamics: Dict[str, Any] = Field(default_factory=dict)
    knowledge_transfer: Dict[str, Any] = Field(default_factory=dict)
    sample_prompts: List[str] = Field(default_factory=list)


class MechanismUsage(BaseModel):
    """Usage statistics for a mechanism"""
    mechanism_id: str
    mechanism_name: str
    usage_count: int = 0
    description: Optional[str] = None


class NarrativeData(BaseModel):
    """Complete narrative data for a simulation run"""
    # Metadata
    run_id: str
    template_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    causal_mode: str
    duration_seconds: Optional[float] = None
    cost_usd: float = 0.0
    status: str

    # Executive summary (template or LLM-enhanced)
    executive_summary: str

    # Content
    characters: List[CharacterProfile] = []
    timeline: List[TimelineEntry] = []
    dialogs: List[DialogExcerpt] = []
    training_insights: TrainingInsights = Field(default_factory=TrainingInsights)
    mechanisms: List[MechanismUsage] = []

    # Atmospheric/environmental context
    atmospheric_context: Dict[str, Any] = Field(default_factory=dict)

    # Results
    entities_created: int = 0
    timepoints_created: int = 0
    training_examples: int = 0
    llm_calls: int = 0
    tokens_used: int = 0

    # Validation results
    validations_passed: int = 0
    validations_failed: int = 0
    validation_details: List[Dict[str, Any]] = []

    # Assessment
    strengths: List[str] = []
    weaknesses: List[str] = []

    # Oxen upload
    oxen_uploaded: bool = False
    oxen_repo_url: Optional[str] = None


# ============================================================================
# Narrative Exporter
# ============================================================================

class NarrativeExporter:
    """Generates narrative summaries in multiple formats"""

    def __init__(self):
        """Initialize the narrative exporter"""
        pass

    def collect_run_data(
        self,
        run_metadata,
        timepoints: List,
        entities: List,
        store,
        training_data: Optional[List[Dict]] = None,
        config = None
    ) -> NarrativeData:
        """
        Collect all simulation artifacts into structured narrative data.

        Args:
            run_metadata: RunMetadata object with run information
            timepoints: List of Timepoint objects
            entities: List of Entity objects
            store: GraphStore with dialogs and relationships
            training_data: Optional list of training examples
            config: SimulationConfig object

        Returns:
            NarrativeData object with all collected information
        """
        # Build character profiles
        characters = []
        for entity in entities:
            # Extract knowledge from entity metadata
            knowledge = []
            energy = None
            emotional_state = None

            if hasattr(entity, 'entity_metadata') and entity.entity_metadata:
                meta = entity.entity_metadata
                if 'cognitive_tensor' in meta:
                    cog = meta['cognitive_tensor']
                    knowledge = cog.get('knowledge_state', [])
                    energy = cog.get('energy_budget')
                    emotional_state = {
                        'valence': cog.get('emotional_valence', 0.0),
                        'arousal': cog.get('emotional_arousal', 0.0)
                    }

            profile = CharacterProfile(
                entity_id=entity.entity_id if hasattr(entity, 'entity_id') else str(entity),
                entity_type=entity.entity_type if hasattr(entity, 'entity_type') else "unknown",
                age=entity.entity_metadata.get('physical_tensor', {}).get('age') if hasattr(entity, 'entity_metadata') else None,
                initial_knowledge=knowledge[:10] if knowledge else [],  # First 10 items
                knowledge_count=len(knowledge) if knowledge else 0,
                final_energy=energy,
                final_emotional_state=emotional_state
            )
            characters.append(profile)

        # Build timeline
        timeline = []
        for tp in timepoints:
            entry = TimelineEntry(
                timepoint_id=tp.timepoint_id if hasattr(tp, 'timepoint_id') else str(tp),
                timestamp=str(tp.timestamp) if hasattr(tp, 'timestamp') else None,
                event_description=tp.event_description if hasattr(tp, 'event_description') else "Event",
                entities_present=tp.entities_present if hasattr(tp, 'entities_present') else [],
                causal_parent=tp.causal_parent if hasattr(tp, 'causal_parent') else None
            )
            timeline.append(entry)

        # Extract dialogs from store
        dialogs = []
        if store:
            try:
                all_dialogs = store.load_all_dialogs() if hasattr(store, 'load_all_dialogs') else []
                for dialog in all_dialogs:
                    if hasattr(dialog, 'dialog_id'):
                        # Deserialize JSON strings from DB storage
                        raw_participants = dialog.participants if hasattr(dialog, 'participants') else []
                        raw_turns = dialog.turns if hasattr(dialog, 'turns') else []
                        participants = json.loads(raw_participants) if isinstance(raw_participants, str) else (raw_participants or [])
                        turns = json.loads(raw_turns) if isinstance(raw_turns, str) else (raw_turns or [])

                        excerpt = DialogExcerpt(
                            dialog_id=dialog.dialog_id,
                            timepoint_id=dialog.timepoint_id if hasattr(dialog, 'timepoint_id') else "unknown",
                            participants=participants,
                            turns=turns
                        )
                        dialogs.append(excerpt)
            except Exception as e:
                print(f"    ⚠️  Could not load dialogs: {e}")

        # Build training insights
        training_insights = TrainingInsights()
        if training_data:
            training_insights.total_examples = len(training_data)

            # Extract sample prompts (first 3)
            training_insights.sample_prompts = [
                ex.get('prompt', '')[:200] + "..." if len(ex.get('prompt', '')) > 200 else ex.get('prompt', '')
                for ex in training_data[:3]
            ]

            # Analyze energy dynamics
            energy_changes = []
            for ex in training_data:
                if 'completion' in ex:
                    try:
                        comp = json.loads(ex['completion']) if isinstance(ex['completion'], str) else ex['completion']
                        if 'energy_change' in comp:
                            energy_changes.append(comp['energy_change'])
                    except:
                        pass

            if energy_changes:
                training_insights.energy_dynamics = {
                    'mean_change': sum(energy_changes) / len(energy_changes),
                    'total_samples': len(energy_changes)
                }

        # Build mechanism usage list
        mechanisms = []
        if hasattr(run_metadata, 'mechanisms_used'):
            for mech_id in sorted(run_metadata.mechanisms_used):
                usage = MechanismUsage(
                    mechanism_id=mech_id,
                    mechanism_name=mech_id,  # Could enhance with full names
                    usage_count=1
                )
                mechanisms.append(usage)

        # Generate executive summary (template-based)
        exec_summary = self._generate_template_summary(
            run_metadata, characters, timeline, dialogs, training_insights
        )

        # Count validations
        val_passed = 0
        val_failed = 0
        val_details = []
        if hasattr(run_metadata, 'validations'):
            for val in run_metadata.validations:
                if hasattr(val, 'passed') and val.passed:
                    val_passed += 1
                else:
                    val_failed += 1
                val_details.append({
                    'rule': val.rule_name if hasattr(val, 'rule_name') else "unknown",
                    'passed': val.passed if hasattr(val, 'passed') else False,
                    'message': val.message if hasattr(val, 'message') else ""
                })

        # Assess strengths and weaknesses
        strengths, weaknesses = self._assess_run(
            run_metadata, characters, timeline, dialogs, val_passed, val_failed
        )

        # Build complete narrative data
        return NarrativeData(
            run_id=run_metadata.run_id,
            template_id=run_metadata.template_id,
            started_at=run_metadata.started_at,
            completed_at=run_metadata.completed_at,
            causal_mode=run_metadata.causal_mode.value if hasattr(run_metadata.causal_mode, 'value') else str(run_metadata.causal_mode),
            duration_seconds=run_metadata.duration_seconds,
            cost_usd=run_metadata.cost_usd,
            status=run_metadata.status,
            executive_summary=exec_summary,
            characters=characters,
            timeline=timeline,
            dialogs=dialogs,
            training_insights=training_insights,
            mechanisms=mechanisms,
            entities_created=run_metadata.entities_created,
            timepoints_created=run_metadata.timepoints_created,
            training_examples=run_metadata.training_examples,
            llm_calls=run_metadata.llm_calls,
            tokens_used=run_metadata.tokens_used,
            validations_passed=val_passed,
            validations_failed=val_failed,
            validation_details=val_details,
            strengths=strengths,
            weaknesses=weaknesses,
            oxen_uploaded=bool(run_metadata.oxen_dataset_url) if hasattr(run_metadata, 'oxen_dataset_url') else False,
            oxen_repo_url=run_metadata.oxen_repo_url if hasattr(run_metadata, 'oxen_repo_url') else None
        )

    def _generate_template_summary(
        self,
        metadata,
        characters: List[CharacterProfile],
        timeline: List[TimelineEntry],
        dialogs: List[DialogExcerpt],
        training: TrainingInsights
    ) -> str:
        """Generate template-based executive summary"""
        char_names = ", ".join([c.entity_id for c in characters[:3]])
        if len(characters) > 3:
            char_names += f" (and {len(characters) - 3} more)"

        timeframe = ""
        if timeline:
            timeframe = f"unfolding across {len(timeline)} timepoints"

        dialog_info = ""
        if dialogs:
            total_turns = sum(len(d.turns) for d in dialogs)
            dialog_info = f"featuring {len(dialogs)} conversations with {total_turns} dialogue exchanges"

        summary = (
            f"A {metadata.causal_mode.value if hasattr(metadata.causal_mode, 'value') else metadata.causal_mode} "
            f"causality simulation of {metadata.template_id} "
            f"{timeframe}. "
            f"The narrative follows {len(characters)} characters ({char_names}) "
            f"{dialog_info}. "
            f"Simulation generated {training.total_examples} training examples "
            f"at a cost of ${metadata.cost_usd:.3f} over {metadata.duration_seconds:.1f} seconds."
        )

        return summary

    def _assess_run(
        self,
        metadata,
        characters: List[CharacterProfile],
        timeline: List[TimelineEntry],
        dialogs: List[DialogExcerpt],
        val_passed: int,
        val_failed: int
    ) -> tuple[List[str], List[str]]:
        """Assess run strengths and weaknesses"""
        strengths = []
        weaknesses = []

        # Assess completion
        if metadata.status == "completed":
            strengths.append("Successfully completed simulation")
        else:
            weaknesses.append(f"Incomplete simulation (status: {metadata.status})")

        # Assess content richness
        if dialogs and len(dialogs) > 0:
            total_turns = sum(len(d.turns) for d in dialogs)
            strengths.append(f"Rich dialogue generation ({len(dialogs)} conversations, {total_turns} turns)")
        else:
            weaknesses.append("No dialogs generated")

        if timeline and len(timeline) >= 3:
            strengths.append(f"Well-developed timeline ({len(timeline)} timepoints)")
        elif timeline and len(timeline) > 0:
            weaknesses.append(f"Short timeline ({len(timeline)} timepoints)")

        # Assess character development
        if characters:
            avg_knowledge = sum(c.knowledge_count for c in characters) / len(characters)
            if avg_knowledge >= 3:
                strengths.append(f"Strong character development (avg {avg_knowledge:.1f} knowledge items)")
            elif avg_knowledge > 0:
                weaknesses.append(f"Limited character development (avg {avg_knowledge:.1f} knowledge items)")

        # Assess validations
        if val_passed > 0:
            strengths.append(f"Passed {val_passed} validation checks")
        if val_failed > 0:
            weaknesses.append(f"Failed {val_failed} validation checks")

        # Assess cost efficiency
        cost_per_entity = metadata.cost_usd / metadata.entities_created if metadata.entities_created > 0 else 0
        if cost_per_entity < 0.01:
            strengths.append(f"Cost-efficient generation (${cost_per_entity:.4f} per entity)")

        return strengths, weaknesses

    def enhance_with_llm(self, narrative_data: NarrativeData, llm_client) -> NarrativeData:
        """
        Optionally enhance executive summary with LLM.

        Args:
            narrative_data: NarrativeData with template summary
            llm_client: LLMClient for enhancement

        Returns:
            Updated NarrativeData with enhanced summary
        """
        # Build detailed prompt from narrative data
        timeline_text = "\n".join([
            f"{i+1}. {tp.timestamp} - {tp.event_description}"
            for i, tp in enumerate(narrative_data.timeline[:10])
        ])

        char_text = "\n".join([
            f"- {c.entity_id} ({c.entity_type}): {c.knowledge_count} knowledge items"
            for c in narrative_data.characters[:5]
        ])

        prompt = f"""Write a compelling 3-4 sentence executive summary for this simulation run.

**Scenario**: {narrative_data.template_id}
**Causal Mode**: {narrative_data.causal_mode}
**Characters**:
{char_text}

**Timeline**:
{timeline_text}

**Dialogue**: {len(narrative_data.dialogs)} conversations with {sum(len(d.turns) for d in narrative_data.dialogs)} turns

Focus on the narrative arc, character interactions, and key outcomes. Write like you're describing a compelling story."""

        try:
            response = llm_client.service.call(
                system="You are an expert at writing engaging narrative summaries of historical simulations.",
                user=prompt,
                model="anthropic/claude-3-5-haiku-20241022",
                max_tokens=300,
                temperature=0.7,
                call_type="enhance_narrative_summary"
            )

            if response.success and response.content:
                narrative_data.executive_summary = response.content.strip()

        except Exception as e:
            print(f"    ⚠️  LLM enhancement failed: {e}, using template summary")

        return narrative_data

    def export_markdown(
        self,
        narrative_data: NarrativeData,
        output_path: Path,
        depth: str = "summary"
    ) -> Path:
        """
        Export narrative as Markdown document.

        Args:
            narrative_data: Complete narrative data
            output_path: Path for output file
            depth: Detail level - "minimal", "summary", or "comprehensive"

        Returns:
            Path to generated Markdown file
        """
        output_path = Path(output_path)

        # Build markdown content based on depth
        content = self._build_markdown_content(narrative_data, depth)

        # Write to file
        output_path.write_text(content, encoding='utf-8')

        return output_path

    def _build_markdown_content(self, data: NarrativeData, depth: str) -> str:
        """Build markdown content based on depth level"""
        lines = []

        # Header
        lines.append(f"# NARRATIVE SUMMARY: {data.template_id}")
        lines.append("")
        lines.append(f"**Run ID**: {data.run_id} | **Mode**: {data.causal_mode} | **Date**: {data.started_at.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        if data.duration_seconds:
            lines.append(f"**Duration**: {data.duration_seconds:.1f}s | **Cost**: ${data.cost_usd:.3f} | **Status**: {data.status}")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Executive Summary
        lines.append("## Executive Summary")
        lines.append("")
        lines.append(data.executive_summary)
        lines.append("")

        if depth == "minimal":
            # Minimal: Just metadata and summary
            return "\n".join(lines)

        # Characters (summary and comprehensive)
        if data.characters:
            lines.append("## Characters")
            lines.append("")
            for char in data.characters:
                lines.append(f"### {char.entity_id}")
                lines.append(f"- **Type**: {char.entity_type}")
                if char.age:
                    lines.append(f"- **Age**: {char.age}")
                lines.append(f"- **Knowledge Items**: {char.knowledge_count}")
                if char.final_energy:
                    lines.append(f"- **Final Energy**: {char.final_energy:.1f}")
                if char.final_emotional_state:
                    lines.append(f"- **Emotional State**: Valence {char.final_emotional_state['valence']:.2f}, Arousal {char.final_emotional_state['arousal']:.2f}")

                # Show initial knowledge for comprehensive
                if depth == "comprehensive" and char.initial_knowledge:
                    lines.append("")
                    lines.append("**Initial Knowledge**:")
                    for know in char.initial_knowledge:
                        lines.append(f"  - {know}")

                lines.append("")

        # Timeline
        if data.timeline:
            lines.append("## Timeline")
            lines.append("")
            for i, tp in enumerate(data.timeline, 1):
                timestamp = tp.timestamp if tp.timestamp else "Time unknown"
                lines.append(f"{i}. **{timestamp}** - {tp.event_description}")
                if depth == "comprehensive" and tp.entities_present:
                    lines.append(f"   - Entities present: {', '.join(tp.entities_present)}")
            lines.append("")

        # Dialogues
        if data.dialogs:
            lines.append(f"## Dialogues ({len(data.dialogs)} conversations)")
            lines.append("")

            for dialog in data.dialogs:
                lines.append(f"### Dialog: {dialog.dialog_id}")
                lines.append(f"**Participants**: {', '.join(dialog.participants)}")
                lines.append("")

                # Show excerpt or full based on depth
                turn_limit = None if depth == "comprehensive" else 3
                turns_to_show = dialog.turns[:turn_limit] if turn_limit else dialog.turns

                for turn in turns_to_show:
                    speaker = turn.get('speaker', 'Unknown')
                    content = turn.get('content', '')
                    emotional_tone = turn.get('emotional_tone', '')

                    if emotional_tone:
                        lines.append(f"**{speaker}** ({emotional_tone}):")
                    else:
                        lines.append(f"**{speaker}**:")
                    lines.append(f"> {content}")
                    lines.append("")

                if turn_limit and len(dialog.turns) > turn_limit:
                    lines.append(f"*({len(dialog.turns) - turn_limit} more turns...)*")
                    lines.append("")

        # Training Data Insights
        if data.training_insights.total_examples > 0:
            lines.append("## Training Data Insights")
            lines.append("")
            lines.append(f"**Total Training Examples**: {data.training_insights.total_examples}")

            if data.training_insights.energy_dynamics:
                lines.append("")
                lines.append("**Energy Dynamics**:")
                lines.append(f"- Mean energy change: {data.training_insights.energy_dynamics.get('mean_change', 0):.2f}")

            if depth == "comprehensive" and data.training_insights.sample_prompts:
                lines.append("")
                lines.append("**Sample Training Prompts**:")
                for i, prompt in enumerate(data.training_insights.sample_prompts, 1):
                    lines.append(f"{i}. {prompt}")

            lines.append("")

        # Mechanisms
        if data.mechanisms:
            lines.append(f"## Mechanisms Employed ({len(data.mechanisms)} total)")
            lines.append("")
            for mech in data.mechanisms:
                lines.append(f"- **{mech.mechanism_id}**: {mech.mechanism_name}")
            lines.append("")

        # Validation Results
        if data.validations_passed > 0 or data.validations_failed > 0:
            lines.append("## Validation Results")
            lines.append("")
            lines.append(f"- ✅ Passed: {data.validations_passed}")
            lines.append(f"- ❌ Failed: {data.validations_failed}")

            if depth == "comprehensive" and data.validation_details:
                lines.append("")
                lines.append("**Details**:")
                for val in data.validation_details:
                    status = "✅" if val['passed'] else "❌"
                    lines.append(f"- {status} {val['rule']}: {val['message']}")

            lines.append("")

        # Simulation Metadata
        lines.append("## Simulation Metadata")
        lines.append("")
        lines.append(f"- **Entities Created**: {data.entities_created}")
        lines.append(f"- **Timepoints Created**: {data.timepoints_created}")
        lines.append(f"- **Training Examples**: {data.training_examples}")
        lines.append(f"- **LLM Calls**: {data.llm_calls}")
        lines.append(f"- **Tokens Used**: {data.tokens_used:,}")

        if data.oxen_uploaded:
            lines.append(f"- **Oxen Repository**: {data.oxen_repo_url}")

        lines.append("")

        # Assessment
        if data.strengths or data.weaknesses:
            lines.append("## Outcome Assessment")
            lines.append("")

            if data.strengths:
                lines.append("**Strengths**:")
                for strength in data.strengths:
                    lines.append(f"- ✓ {strength}")
                lines.append("")

            if data.weaknesses:
                lines.append("**Weaknesses**:")
                for weakness in data.weaknesses:
                    lines.append(f"- ⚠️ {weakness}")
                lines.append("")

        # Footer
        lines.append("---")
        lines.append("")
        lines.append(f"*Generated by Timepoint-Daedalus Narrative Export System*")
        lines.append("")

        return "\n".join(lines)

    def export_json(self, narrative_data: NarrativeData, output_path: Path) -> Path:
        """
        Export narrative as JSON document.

        Args:
            narrative_data: Complete narrative data
            output_path: Path for output file

        Returns:
            Path to generated JSON file
        """
        output_path = Path(output_path)

        # Convert to dict and add format version
        data_dict = narrative_data.model_dump(mode='json')
        data_dict['format_version'] = "1.0"
        data_dict['generated_at'] = datetime.now().isoformat()

        # Write to file with pretty formatting
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data_dict, f, indent=2, ensure_ascii=False, default=str)

        return output_path

    def export_pdf(
        self,
        narrative_data: NarrativeData,
        output_path: Path,
        depth: str = "summary"
    ) -> Path:
        """
        Export narrative as PDF document.

        Args:
            narrative_data: Complete narrative data
            output_path: Path for output file
            depth: Detail level - "minimal", "summary", or "comprehensive"

        Returns:
            Path to generated PDF file

        Raises:
            ImportError: If reportlab is not installed
        """
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
            from reportlab.lib.enums import TA_LEFT, TA_CENTER
        except ImportError:
            raise ImportError(
                "reportlab package required for PDF export. "
                "Install with: pip install reportlab"
            )

        output_path = Path(output_path)

        # Create PDF document
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=1*inch,
            bottomMargin=0.75*inch
        )

        # Build story
        story = []
        styles = getSampleStyleSheet()

        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor='#1a1a1a',
            spaceAfter=12,
            alignment=TA_CENTER
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            textColor='#333333',
            spaceAfter=10
        )

        # Title
        story.append(Paragraph(f"NARRATIVE SUMMARY: {narrative_data.template_id}", title_style))
        story.append(Spacer(1, 0.2*inch))

        # Metadata
        meta_text = f"<b>Run ID:</b> {narrative_data.run_id}<br/>"
        meta_text += f"<b>Mode:</b> {narrative_data.causal_mode} | "
        meta_text += f"<b>Date:</b> {narrative_data.started_at.strftime('%Y-%m-%d %H:%M:%S')}<br/>"
        if narrative_data.duration_seconds:
            meta_text += f"<b>Duration:</b> {narrative_data.duration_seconds:.1f}s | "
            meta_text += f"<b>Cost:</b> ${narrative_data.cost_usd:.3f} | "
            meta_text += f"<b>Status:</b> {narrative_data.status}"

        story.append(Paragraph(meta_text, styles['Normal']))
        story.append(Spacer(1, 0.3*inch))

        # Executive Summary
        story.append(Paragraph("Executive Summary", heading_style))
        story.append(Paragraph(narrative_data.executive_summary, styles['Normal']))
        story.append(Spacer(1, 0.2*inch))

        # Add more sections based on depth (similar to markdown)
        if depth != "minimal":
            # Characters
            if narrative_data.characters:
                story.append(Paragraph("Characters", heading_style))
                for char in narrative_data.characters:
                    char_text = f"<b>{char.entity_id}</b> ({char.entity_type})<br/>"
                    char_text += f"Knowledge Items: {char.knowledge_count}"
                    story.append(Paragraph(char_text, styles['Normal']))
                    story.append(Spacer(1, 0.1*inch))
                story.append(Spacer(1, 0.2*inch))

            # Timeline
            if narrative_data.timeline:
                story.append(Paragraph("Timeline", heading_style))
                for i, tp in enumerate(narrative_data.timeline, 1):
                    timestamp = tp.timestamp if tp.timestamp else "Time unknown"
                    tp_text = f"{i}. <b>{timestamp}</b> - {tp.event_description}"
                    story.append(Paragraph(tp_text, styles['Normal']))
                story.append(Spacer(1, 0.2*inch))

        # Build PDF
        doc.build(story)

        return output_path
