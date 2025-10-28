"""
Output Formatters for Multi-Format Report Generation

Supports Markdown, JSON, and CSV output formats.
"""

from typing import Dict, Any, List
from abc import ABC, abstractmethod
import json
import csv
from io import StringIO


class OutputFormatter(ABC):
    """Base class for output formatters"""

    @abstractmethod
    def format(self, data: Dict[str, Any]) -> str:
        """
        Format data to string output.

        Args:
            data: Dictionary containing report data

        Returns:
            Formatted string
        """
        pass


class MarkdownFormatter(OutputFormatter):
    """Format reports as Markdown"""

    def format(self, data: Dict[str, Any]) -> str:
        """Format data as Markdown"""
        lines = []

        # Title
        if "title" in data:
            lines.append(f"# {data['title']}\n")

        # Metadata
        if "metadata" in data:
            lines.append("## Metadata\n")
            for key, value in data["metadata"].items():
                lines.append(f"- **{key}**: {value}")
            lines.append("")

        # Summary
        if "summary" in data:
            lines.append("## Summary\n")
            lines.append(data["summary"])
            lines.append("")

        # Sections
        if "sections" in data:
            for section in data["sections"]:
                lines.append(f"## {section['title']}\n")
                if "content" in section:
                    lines.append(section["content"])
                if "items" in section:
                    for item in section["items"]:
                        lines.append(f"- {item}")
                lines.append("")

        # Tables
        if "tables" in data:
            for table in data["tables"]:
                lines.append(f"### {table.get('title', 'Table')}\n")
                lines.append(self._format_table(table))
                lines.append("")

        return "\n".join(lines)

    def _format_table(self, table: Dict[str, Any]) -> str:
        """Format table as Markdown"""
        if "headers" not in table or "rows" not in table:
            return ""

        lines = []
        headers = table["headers"]
        rows = table["rows"]

        # Header row
        lines.append("| " + " | ".join(str(h) for h in headers) + " |")
        # Separator
        lines.append("|" + "|".join([" --- " for _ in headers]) + "|")
        # Data rows
        for row in rows:
            lines.append("| " + " | ".join(str(cell) for cell in row) + " |")

        return "\n".join(lines)


class JSONFormatter(OutputFormatter):
    """Format reports as JSON"""

    def __init__(self, indent: int = 2):
        """
        Args:
            indent: Indentation level for pretty printing
        """
        self.indent = indent

    def format(self, data: Dict[str, Any]) -> str:
        """Format data as JSON"""
        return json.dumps(data, indent=self.indent, default=str)


class CSVFormatter(OutputFormatter):
    """Format reports as CSV"""

    def format(self, data: Dict[str, Any]) -> str:
        """
        Format data as CSV.

        Expects data to have a 'table' key with 'headers' and 'rows'.
        """
        if "table" not in data:
            # If no table, try to create one from flat data
            return self._format_dict_as_csv(data)

        table = data["table"]
        if "headers" not in table or "rows" not in table:
            return ""

        output = StringIO()
        writer = csv.writer(output)

        # Write headers
        writer.writerow(table["headers"])

        # Write rows
        for row in table["rows"]:
            writer.writerow(row)

        return output.getvalue()

    def _format_dict_as_csv(self, data: Dict[str, Any]) -> str:
        """Convert dictionary to CSV format"""
        output = StringIO()
        writer = csv.writer(output)

        # Headers
        writer.writerow(["Key", "Value"])

        # Data
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            writer.writerow([key, value])

        return output.getvalue()


class FormatterFactory:
    """Factory for creating formatters"""

    _formatters = {
        "markdown": MarkdownFormatter,
        "md": MarkdownFormatter,
        "json": JSONFormatter,
        "csv": CSVFormatter
    }

    @classmethod
    def create(cls, format: str, **kwargs) -> OutputFormatter:
        """
        Create formatter instance.

        Args:
            format: Format name (markdown, json, csv)
            **kwargs: Additional arguments for formatter

        Returns:
            OutputFormatter instance

        Raises:
            ValueError: If format not supported
        """
        format_lower = format.lower()
        if format_lower not in cls._formatters:
            raise ValueError(
                f"Unsupported format: {format}. "
                f"Supported: {list(cls._formatters.keys())}"
            )

        return cls._formatters[format_lower](**kwargs)

    @classmethod
    def get_supported_formats(cls) -> List[str]:
        """Get list of supported formats"""
        return list(cls._formatters.keys())


# ============================================================================
# Script/Screenplay Formatters (for storyboard/script export)
# ============================================================================

class FountainFormatter:
    """
    Convert ScriptData to Fountain screenplay format.

    Fountain is a plain text markup language for screenwriting.
    Spec: https://fountain.io/syntax/

    Example:
        from reporting.formatters import FountainFormatter

        fountain = FountainFormatter()
        script_text = fountain.format(script_data)
        # Returns Fountain-formatted screenplay text
    """

    def format(self, script_data) -> str:
        """
        Convert ScriptData to Fountain format.

        Args:
            script_data: ScriptData structure from ScriptGenerator

        Returns:
            Fountain-formatted screenplay text
        """
        sections = []

        # Title page
        sections.append(self._format_title_page(script_data))

        # Scenes
        for scene in script_data.scenes:
            sections.append(self._format_scene(scene, script_data.characters))

        # Join with blank lines
        return "\n\n".join(sections)

    def _format_title_page(self, script_data) -> str:
        """Format Fountain title page"""
        lines = [
            f"Title: {script_data.title}",
            "Credit: Generated by Timepoint-Daedalus",
            f"Draft date: {script_data.generated_at.strftime('%Y-%m-%d')}",
            f"Source: {script_data.world_id}",
            ""
        ]

        # Add metadata
        if script_data.metadata:
            lines.append("[[")
            lines.append(f"Temporal Mode: {script_data.temporal_mode}")
            lines.append(f"Scenes: {script_data.metadata.get('total_scenes', len(script_data.scenes))}")
            lines.append(f"Characters: {script_data.metadata.get('entities_count', len(script_data.characters))}")
            lines.append(f"Dialog Turns: {script_data.metadata.get('dialog_turns', 0)}")
            lines.append("]]")
            lines.append("")

        return "\n".join(lines)

    def _format_scene(self, scene, characters: List) -> str:
        """Format a single scene in Fountain"""
        lines = []

        # Scene heading
        lines.append(scene.heading)
        lines.append("")

        # Scene description
        if scene.description:
            lines.append(scene.description)
            lines.append("")

        # Add atmosphere description
        atmosphere_desc = self._format_atmosphere(scene.atmosphere)
        if atmosphere_desc:
            lines.append(atmosphere_desc)
            lines.append("")

        # Character introductions (if first appearance)
        for char_id in scene.characters_present:
            character = self._find_character(char_id, characters)
            if character and character.first_appearance_scene == scene.scene_number:
                intro = self._format_character_introduction(character)
                if intro:
                    lines.append(intro)
                    lines.append("")

        # Interleave action beats and dialog
        lines.extend(self._format_scene_content(scene))

        # Visual notes as Fountain note
        if scene.visual_notes:
            lines.append("")
            lines.append(f"[[VISUAL: {scene.visual_notes}]]")

        return "\n".join(lines)

    def _format_atmosphere(self, atmosphere) -> str:
        """Format atmosphere as prose description"""
        parts = []

        # Tension
        if atmosphere.tension_level > 0.7:
            parts.append("The atmosphere is tense")
        elif atmosphere.tension_level < 0.3:
            parts.append("The mood is relaxed")

        # Formality
        if atmosphere.formality_level > 0.7:
            parts.append("formal")
        elif atmosphere.formality_level < 0.3:
            parts.append("casual")

        # Emotional valence
        if atmosphere.emotional_valence > 0.5:
            parts.append("positive energy fills the space")
        elif atmosphere.emotional_valence < -0.5:
            parts.append("negativity hangs in the air")

        # Social cohesion
        if atmosphere.social_cohesion < 0.3:
            parts.append("Individuals seem disconnected")

        if not parts:
            return ""

        # Join with proper punctuation
        if len(parts) == 1:
            return parts[0].capitalize() + "."
        elif len(parts) == 2:
            return f"{parts[0].capitalize()} and {parts[1]}."
        else:
            result = ", ".join(parts[:-1]) + f", and {parts[-1]}"
            return result.capitalize() + "."

    def _format_character_introduction(self, character) -> str:
        """Format character introduction (all caps name + description)"""
        name = character.name.upper()

        if character.description:
            return f"{name}, {character.description}, enters."
        else:
            return f"{name} enters."

    def _format_scene_content(self, scene) -> List[str]:
        """Format interleaved action and dialog"""
        lines = []

        # If we have dialog, interleave with action beats
        if scene.dialog:
            # Alternate between action beats and dialog
            action_idx = 0
            dialog_idx = 0

            while action_idx < len(scene.action_beats) or dialog_idx < len(scene.dialog):
                # Add action beat
                if action_idx < len(scene.action_beats):
                    lines.append(scene.action_beats[action_idx])
                    lines.append("")
                    action_idx += 1

                # Add dialog line
                if dialog_idx < len(scene.dialog):
                    lines.extend(self._format_dialog_line(scene.dialog[dialog_idx]))
                    lines.append("")
                    dialog_idx += 1

        else:
            # No dialog, just action beats
            for beat in scene.action_beats:
                lines.append(beat)
                lines.append("")

        return lines

    def _format_dialog_line(self, dialog) -> List[str]:
        """Format a single dialog line in Fountain"""
        lines = []

        # Character name (all caps)
        character_name = dialog.speaker.replace("_", " ").upper()
        lines.append(character_name)

        # Parenthetical (if present)
        if dialog.parenthetical:
            lines.append(f"({dialog.parenthetical})")

        # Dialog content
        lines.append(dialog.content)

        return lines

    def _find_character(self, char_id: str, characters: List):
        """Find character by ID"""
        for char in characters:
            if char.id == char_id:
                return char
        return None


class StoryboardJSONFormatter:
    """
    Convert ScriptData to structured storyboard JSON.

    Provides detailed scene-by-scene breakdown with production metadata,
    suitable for programmatic access and visual storyboard tools.

    Example:
        from reporting.formatters import StoryboardJSONFormatter

        formatter = StoryboardJSONFormatter()
        storyboard_data = formatter.format(script_data)
        # Returns dict with scenes, characters, metadata
    """

    def format(self, script_data) -> Dict[str, Any]:
        """
        Convert ScriptData to storyboard JSON structure.

        Args:
            script_data: ScriptData structure from ScriptGenerator

        Returns:
            Dictionary with storyboard structure
        """
        return {
            "title": script_data.title,
            "world_id": script_data.world_id,
            "generated_at": script_data.generated_at.isoformat(),
            "temporal_mode": script_data.temporal_mode,
            "scenes": [self._format_scene(scene) for scene in script_data.scenes],
            "characters": [self._format_character(char) for char in script_data.characters],
            "metadata": script_data.metadata
        }

    def _format_scene(self, scene) -> Dict[str, Any]:
        """Format a single scene as JSON"""
        return {
            "scene_number": scene.scene_number,
            "timepoint_id": scene.timepoint_id,
            "heading": scene.heading,
            "timestamp": scene.timestamp.isoformat(),
            "setting": {
                "interior": scene.environment.interior,
                "location": scene.environment.location,
                "time_of_day": scene.environment.time_of_day,
                "lighting_level": scene.environment.lighting_level,
                "ambient_temperature": scene.environment.ambient_temperature,
                "weather": scene.environment.weather,
                "architectural_style": scene.environment.architectural_style
            },
            "atmosphere": {
                "tension_level": scene.atmosphere.tension_level,
                "formality_level": scene.atmosphere.formality_level,
                "emotional_valence": scene.atmosphere.emotional_valence,
                "emotional_arousal": scene.atmosphere.emotional_arousal,
                "social_cohesion": scene.atmosphere.social_cohesion,
                "energy_level": scene.atmosphere.energy_level
            },
            "description": scene.description,
            "characters_present": scene.characters_present,
            "dialog": [self._format_dialog_line(dl) for dl in scene.dialog],
            "action_beats": scene.action_beats,
            "duration_estimate_seconds": scene.duration_estimate_seconds,
            "causal_parent": scene.causal_parent,
            "causal_children": scene.causal_children,
            "key_events": scene.key_events,
            "visual_notes": scene.visual_notes,
            "production_notes": scene.production_notes
        }

    def _format_dialog_line(self, dialog) -> Dict[str, Any]:
        """Format dialog line as JSON"""
        return {
            "speaker": dialog.speaker,
            "line": dialog.content,
            "emotional_tone": dialog.emotional_tone,
            "parenthetical": dialog.parenthetical,
            "timestamp": dialog.timestamp.isoformat() if dialog.timestamp else None
        }

    def _format_character(self, character) -> Dict[str, Any]:
        """Format character as JSON"""
        return {
            "id": character.id,
            "name": character.name,
            "type": character.entity_type,
            "role": character.role,
            "first_appearance_scene": character.first_appearance_scene,
            "description": character.description,
            "personality_traits": character.personality_traits
        }
