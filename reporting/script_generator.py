"""
Script Generator - Query database and transform simulation data into screenplay structure.

Converts temporal simulation data into screenplay/storyboard formats by:
- Querying Timepoints, Dialogs, Entities, Atmospheres, Environments from database
- Mapping timepoints → scenes
- Mapping dialogs → character dialog
- Mapping event descriptions → action lines
- Respecting temporal modes and causal chains
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import json


@dataclass
class DialogLine:
    """Single line of dialog in a scene"""
    speaker: str
    content: str
    emotional_tone: Optional[str] = None
    parenthetical: Optional[str] = None
    timestamp: Optional[datetime] = None


@dataclass
class SceneAtmosphere:
    """Atmosphere/mood of a scene"""
    tension_level: float = 0.5
    formality_level: float = 0.5
    emotional_valence: float = 0.0
    emotional_arousal: float = 0.5
    social_cohesion: float = 0.5
    energy_level: float = 0.5


@dataclass
class SceneEnvironment:
    """Physical environment of a scene"""
    location: str = "UNKNOWN LOCATION"
    interior: bool = True
    time_of_day: str = "DAY"
    lighting_level: float = 0.7
    ambient_temperature: float = 20.0
    weather: Optional[str] = None
    architectural_style: Optional[str] = None


@dataclass
class Character:
    """Character appearing in the script"""
    id: str
    name: str
    entity_type: str = "human"
    role: Optional[str] = None
    description: Optional[str] = None
    first_appearance_scene: int = 1
    personality_traits: List[float] = field(default_factory=lambda: [0.5, 0.5, 0.5, 0.5, 0.5])


@dataclass
class Scene:
    """Single scene in the screenplay"""
    scene_number: int
    timepoint_id: str
    heading: str
    timestamp: datetime
    environment: SceneEnvironment
    atmosphere: SceneAtmosphere
    description: str
    characters_present: List[str]
    dialog: List[DialogLine]
    action_beats: List[str]
    duration_estimate_seconds: int = 0
    causal_parent: Optional[str] = None
    causal_children: List[str] = field(default_factory=list)
    key_events: List[str] = field(default_factory=list)
    visual_notes: Optional[str] = None
    production_notes: Optional[str] = None


@dataclass
class ScriptData:
    """Complete screenplay data structure"""
    title: str
    world_id: str
    generated_at: datetime
    temporal_mode: str = "pearl"
    scenes: List[Scene] = field(default_factory=list)
    characters: List[Character] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ScriptGenerator:
    """
    Generate screenplay/storyboard structure from database.

    Example:
        from storage import GraphStore
        from reporting.script_generator import ScriptGenerator

        store = GraphStore("sqlite:///timepoint.db")
        generator = ScriptGenerator(store)

        script_data = generator.generate_script_structure(world_id="meeting_001")
        # Returns ScriptData with scenes, characters, dialog
    """

    def __init__(self, store):
        """
        Args:
            store: GraphStore instance for database queries
        """
        self.store = store

    def generate_script_structure(
        self,
        world_id: str,
        title: Optional[str] = None,
        temporal_mode: str = "pearl"
    ) -> ScriptData:
        """
        Generate complete screenplay structure from database.

        Args:
            world_id: World/simulation identifier (typically first timepoint_id)
            title: Script title (auto-generated if None)
            temporal_mode: Temporal mode (pearl, directorial, branching, etc.)

        Returns:
            ScriptData with scenes, characters, dialog
        """
        # Query all timepoints for this world
        timepoints = self._query_timepoints(world_id)

        if not timepoints:
            # Return empty script if no data
            return ScriptData(
                title=title or "Untitled Simulation",
                world_id=world_id,
                generated_at=datetime.utcnow(),
                temporal_mode=temporal_mode,
                metadata={"error": "No timepoints found for world_id"}
            )

        # Sort timepoints by causal order (respects temporal mode)
        ordered_timepoints = self._order_timepoints_by_causality(timepoints, temporal_mode)

        # Extract all entities (characters) across timepoints
        characters = self._extract_characters(ordered_timepoints)

        # Generate scenes from timepoints
        scenes = []
        for scene_num, tp in enumerate(ordered_timepoints, start=1):
            scene = self._generate_scene(tp, scene_num, temporal_mode)
            scenes.append(scene)

        # Update character first appearance
        self._update_character_first_appearances(characters, scenes)

        # Auto-generate title if not provided
        if not title:
            title = self._generate_title(ordered_timepoints, characters)

        # Create script data
        script_data = ScriptData(
            title=title,
            world_id=world_id,
            generated_at=datetime.utcnow(),
            temporal_mode=temporal_mode,
            scenes=scenes,
            characters=characters,
            metadata={
                "total_scenes": len(scenes),
                "total_duration_estimate": sum(s.duration_estimate_seconds for s in scenes),
                "entities_count": len(characters),
                "dialog_turns": sum(len(s.dialog) for s in scenes),
                "mechanisms_used": self._detect_mechanisms_used()
            }
        )

        return script_data

    def generate_script_structure_from_data(
        self,
        timepoints: List[Any],
        entities: List[Any],
        world_id: str,
        title: Optional[str] = None,
        temporal_mode: str = "pearl"
    ) -> ScriptData:
        """
        Generate complete screenplay structure from in-memory data.

        This method accepts timepoints and entities directly instead of querying
        the database. Use this when data is already loaded in memory.

        Args:
            timepoints: List of Timepoint objects
            entities: List of Entity objects
            world_id: World/simulation identifier
            title: Script title (auto-generated if None)
            temporal_mode: Temporal mode (pearl, directorial, branching, etc.)

        Returns:
            ScriptData with scenes, characters, dialog
        """
        if not timepoints:
            # Return empty script if no data
            return ScriptData(
                title=title or "Untitled Simulation",
                world_id=world_id,
                generated_at=datetime.utcnow(),
                temporal_mode=temporal_mode,
                metadata={"error": "No timepoints provided"}
            )

        # Sort timepoints by causal order (respects temporal mode)
        ordered_timepoints = self._order_timepoints_by_causality(timepoints, temporal_mode)

        # Extract characters from provided entities
        characters = self._extract_characters_from_data(ordered_timepoints, entities)

        # Generate scenes from timepoints
        scenes = []
        for scene_num, tp in enumerate(ordered_timepoints, start=1):
            scene = self._generate_scene(tp, scene_num, temporal_mode)
            scenes.append(scene)

        # Update character first appearance
        self._update_character_first_appearances(characters, scenes)

        # Auto-generate title if not provided
        if not title:
            title = self._generate_title(ordered_timepoints, characters)

        # Create script data
        script_data = ScriptData(
            title=title,
            world_id=world_id,
            generated_at=datetime.utcnow(),
            temporal_mode=temporal_mode,
            scenes=scenes,
            characters=characters,
            metadata={
                "total_scenes": len(scenes),
                "total_duration_estimate": sum(s.duration_estimate_seconds for s in scenes),
                "entities_count": len(characters),
                "dialog_turns": sum(len(s.dialog) for s in scenes),
                "mechanisms_used": self._detect_mechanisms_used()
            }
        )

        return script_data

    def _query_timepoints(self, world_id: str) -> List[Any]:
        """Query all timepoints for a world (simulation)"""
        # In practice, world_id might be a prefix or first timepoint_id
        # This is a simplified query - adjust based on your DB structure

        try:
            # Try to get all timepoints that share a common prefix or timeline_id
            from sqlmodel import select, Session
            from schemas import Timepoint

            with Session(self.store.engine) as session:
                # Option 1: If world_id is a timepoint_id, find its causal chain
                stmt = select(Timepoint).where(Timepoint.timepoint_id.like(f"{world_id}%"))
                timepoints = session.exec(stmt).all()

                # If no results, try treating world_id as timeline_id
                if not timepoints:
                    stmt = select(Timepoint).where(Timepoint.timeline_id == world_id)
                    timepoints = session.exec(stmt).all()

                return list(timepoints)
        except Exception as e:
            print(f"Warning: Could not query timepoints for {world_id}: {e}")
            return []

    def _order_timepoints_by_causality(
        self,
        timepoints: List[Any],
        temporal_mode: str
    ) -> List[Any]:
        """
        Order timepoints based on temporal mode and causal relationships.

        - Pearl: Chronological order following causal_parent
        - Directorial: Order by dramatic tension
        """
        if temporal_mode == "pearl":
            # Standard chronological order
            return self._order_chronologically(timepoints)
        elif temporal_mode == "directorial":
            # TODO: Order by dramatic tension
            return self._order_chronologically(timepoints)
        else:
            return self._order_chronologically(timepoints)

    def _order_chronologically(self, timepoints: List[Any]) -> List[Any]:
        """Order timepoints chronologically by timestamp"""
        return sorted(timepoints, key=lambda tp: tp.timestamp)

    def _extract_characters(self, timepoints: List[Any]) -> List[Character]:
        """Extract unique characters from all timepoints"""
        from sqlmodel import select, Session
        from schemas import Entity

        character_dict = {}

        try:
            with Session(self.store.engine) as session:
                for tp in timepoints:
                    for entity_id in tp.entities_present:
                        if entity_id not in character_dict:
                            # Query entity details
                            stmt = select(Entity).where(Entity.entity_id == entity_id)
                            entity = session.exec(stmt).first()

                            if entity:
                                # Extract personality traits
                                personality = entity.entity_metadata.get("personality_traits", [0.5] * 5)

                                # Create character
                                character = Character(
                                    id=entity.entity_id,
                                    name=self._format_character_name(entity.entity_id),
                                    entity_type=entity.entity_type,
                                    role=entity.entity_metadata.get("role"),
                                    description=self._generate_character_description(entity),
                                    personality_traits=personality
                                )
                                character_dict[entity_id] = character
        except Exception as e:
            print(f"Warning: Could not extract characters: {e}")

        return list(character_dict.values())

    def _extract_characters_from_data(
        self,
        timepoints: List[Any],
        entities: List[Any]
    ) -> List[Character]:
        """
        Extract unique characters from provided entities.

        This method works with in-memory entities instead of querying the database.

        Args:
            timepoints: List of timepoints to identify which entities appear
            entities: List of Entity objects

        Returns:
            List of Character objects
        """
        # Create entity lookup by ID
        entity_dict = {}
        for entity in entities:
            entity_id = entity.entity_id if hasattr(entity, 'entity_id') else str(entity)
            entity_dict[entity_id] = entity

        character_dict = {}

        # For each timepoint, extract entities present
        for tp in timepoints:
            entities_present = tp.entities_present if hasattr(tp, 'entities_present') else []

            for entity_id in entities_present:
                if entity_id not in character_dict:
                    entity = entity_dict.get(entity_id)

                    if entity:
                        # Extract personality traits
                        entity_metadata = entity.entity_metadata if hasattr(entity, 'entity_metadata') else {}
                        personality = entity_metadata.get("personality_traits", [0.5] * 5)

                        # Create character
                        character = Character(
                            id=entity_id,
                            name=self._format_character_name(entity_id),
                            entity_type=entity.entity_type if hasattr(entity, 'entity_type') else 'human',
                            role=entity_metadata.get("role"),
                            description=self._generate_character_description(entity),
                            personality_traits=personality
                        )
                        character_dict[entity_id] = character

        return list(character_dict.values())

    def _generate_scene(
        self,
        timepoint: Any,
        scene_number: int,
        temporal_mode: str
    ) -> Scene:
        """Generate a Scene from a Timepoint"""
        # Query environment
        environment = self._query_environment(timepoint.timepoint_id)

        # Query atmosphere
        atmosphere = self._query_atmosphere(timepoint.timepoint_id)

        # Query dialogs
        dialog_lines = self._query_dialog(timepoint.timepoint_id)

        # Generate scene heading
        heading = self._generate_scene_heading(environment, timepoint.timestamp)

        # Generate scene description
        description = self._generate_scene_description(timepoint, environment, atmosphere)

        # Extract action beats from event description
        action_beats = self._extract_action_beats(timepoint.event_description)

        # Estimate duration (rough heuristic)
        duration = self._estimate_scene_duration(dialog_lines, action_beats)

        # Create scene
        scene = Scene(
            scene_number=scene_number,
            timepoint_id=timepoint.timepoint_id,
            heading=heading,
            timestamp=timepoint.timestamp,
            environment=environment,
            atmosphere=atmosphere,
            description=description,
            characters_present=timepoint.entities_present,
            dialog=dialog_lines,
            action_beats=action_beats,
            duration_estimate_seconds=duration,
            causal_parent=timepoint.causal_parent,
            key_events=[timepoint.event_description[:100]],
            visual_notes=self._generate_visual_notes(atmosphere),
            production_notes=None
        )

        return scene

    def _query_environment(self, timepoint_id: str) -> SceneEnvironment:
        """Query EnvironmentEntity for timepoint"""
        try:
            from sqlmodel import select, Session
            from schemas import EnvironmentEntity

            with Session(self.store.engine) as session:
                stmt = select(EnvironmentEntity).where(EnvironmentEntity.timepoint_id == timepoint_id)
                env = session.exec(stmt).first()

                if env:
                    return SceneEnvironment(
                        location=env.location,
                        interior=True,  # Heuristic: default to INT
                        time_of_day=self._infer_time_of_day(env.lighting_level),
                        lighting_level=env.lighting_level,
                        ambient_temperature=env.ambient_temperature,
                        weather=env.weather,
                        architectural_style=env.architectural_style
                    )
        except Exception as e:
            print(f"Warning: Could not query environment for {timepoint_id}: {e}")

        return SceneEnvironment()

    def _query_atmosphere(self, timepoint_id: str) -> SceneAtmosphere:
        """Query AtmosphereEntity for timepoint"""
        try:
            from sqlmodel import select, Session
            from schemas import AtmosphereEntity

            with Session(self.store.engine) as session:
                stmt = select(AtmosphereEntity).where(AtmosphereEntity.timepoint_id == timepoint_id)
                atm = session.exec(stmt).first()

                if atm:
                    return SceneAtmosphere(
                        tension_level=atm.tension_level,
                        formality_level=atm.formality_level,
                        emotional_valence=atm.emotional_valence,
                        emotional_arousal=atm.emotional_arousal,
                        social_cohesion=atm.social_cohesion,
                        energy_level=atm.energy_level
                    )
        except Exception as e:
            print(f"Warning: Could not query atmosphere for {timepoint_id}: {e}")

        return SceneAtmosphere()

    def _query_dialog(self, timepoint_id: str) -> List[DialogLine]:
        """Query Dialog records for timepoint"""
        dialog_lines = []

        try:
            from sqlmodel import select, Session
            from schemas import Dialog

            with Session(self.store.engine) as session:
                stmt = select(Dialog).where(Dialog.timepoint_id == timepoint_id)
                dialogs = session.exec(stmt).all()

                for dialog_record in dialogs:
                    # Parse turns from JSON
                    turns = json.loads(dialog_record.turns) if isinstance(dialog_record.turns, str) else dialog_record.turns

                    for turn in turns:
                        # Handle both dict and object formats
                        if isinstance(turn, dict):
                            speaker = turn.get("speaker", "UNKNOWN")
                            content = turn.get("content", "")
                            emotional_tone = turn.get("emotional_tone")
                            timestamp = turn.get("timestamp")
                        else:
                            speaker = getattr(turn, "speaker", "UNKNOWN")
                            content = getattr(turn, "content", "")
                            emotional_tone = getattr(turn, "emotional_tone", None)
                            timestamp = getattr(turn, "timestamp", None)

                        # Convert emotional_tone to parenthetical
                        parenthetical = None
                        if emotional_tone:
                            parenthetical = emotional_tone

                        dialog_line = DialogLine(
                            speaker=speaker,
                            content=content,
                            emotional_tone=emotional_tone,
                            parenthetical=parenthetical,
                            timestamp=timestamp
                        )
                        dialog_lines.append(dialog_line)
        except Exception as e:
            print(f"Warning: Could not query dialog for {timepoint_id}: {e}")

        return dialog_lines

    def _generate_scene_heading(self, environment: SceneEnvironment, timestamp: datetime) -> str:
        """Generate Fountain-style scene heading"""
        int_ext = "INT." if environment.interior else "EXT."
        location = environment.location.upper().replace("_", " ")
        time = environment.time_of_day

        return f"{int_ext} {location} - {time}"

    def _generate_scene_description(
        self,
        timepoint: Any,
        environment: SceneEnvironment,
        atmosphere: SceneAtmosphere
    ) -> str:
        """Generate prose scene description"""
        parts = []

        # Add event description
        parts.append(timepoint.event_description)

        # Add atmosphere context
        if atmosphere.tension_level > 0.7:
            parts.append("The atmosphere is tense.")
        elif atmosphere.tension_level < 0.3:
            parts.append("The mood is relaxed.")

        if atmosphere.formality_level > 0.7:
            parts.append("The setting is formal.")

        # Add environmental details
        if environment.lighting_level < 0.3:
            parts.append("The lighting is dim.")
        elif environment.lighting_level > 0.8:
            parts.append("The space is brightly lit.")

        if environment.weather:
            parts.append(f"Outside, the weather is {environment.weather}.")

        return " ".join(parts)

    def _extract_action_beats(self, event_description: str) -> List[str]:
        """Extract action beats from event description"""
        # Simple implementation: split on sentences
        # In production, could use NLP to extract actions
        beats = [s.strip() for s in event_description.split('.') if s.strip()]
        return beats

    def _estimate_scene_duration(self, dialog_lines: List[DialogLine], action_beats: List[str]) -> int:
        """Estimate scene duration in seconds (rough heuristic)"""
        # Rough estimates:
        # - Dialog: 3 seconds per line
        # - Action beat: 5 seconds
        dialog_time = len(dialog_lines) * 3
        action_time = len(action_beats) * 5
        base_time = 30  # Minimum scene duration

        return base_time + dialog_time + action_time

    def _infer_time_of_day(self, lighting_level: float) -> str:
        """Infer time of day from lighting level"""
        if lighting_level < 0.3:
            return "NIGHT"
        elif lighting_level > 0.7:
            return "DAY"
        else:
            return "EVENING"

    def _generate_visual_notes(self, atmosphere: SceneAtmosphere) -> str:
        """Generate visual/cinematography notes"""
        if atmosphere.tension_level > 0.7:
            return "Tight framing, close-ups to emphasize tension"
        elif atmosphere.social_cohesion < 0.3:
            return "Wide shots showing physical/emotional distance"
        elif atmosphere.energy_level > 0.7:
            return "Dynamic camera movement, quick cuts"
        else:
            return "Standard coverage, medium shots"

    def _format_character_name(self, entity_id: str) -> str:
        """Format entity_id as character name"""
        # Convert "john_smith" → "John Smith"
        return entity_id.replace("_", " ").title()

    def _generate_character_description(self, entity: Any) -> str:
        """Generate character description from entity metadata"""
        parts = []

        entity_type = entity.entity_type
        if entity_type != "human":
            parts.append(f"({entity_type})")

        role = entity.entity_metadata.get("role")
        if role:
            parts.append(role)

        # Add physical description if available
        physical = entity.entity_metadata.get("physical_tensor", {})
        age = physical.get("age")
        if age:
            parts.append(f"age {int(age)}")

        return ", ".join(parts) if parts else None

    def _update_character_first_appearances(self, characters: List[Character], scenes: List[Scene]):
        """Update first appearance scene number for each character"""
        for character in characters:
            for scene in scenes:
                if character.id in scene.characters_present:
                    character.first_appearance_scene = scene.scene_number
                    break

    def _generate_title(self, timepoints: List[Any], characters: List[Character]) -> str:
        """Auto-generate script title"""
        if not timepoints:
            return "Untitled Simulation"

        # Extract key words from first timepoint event
        first_event = timepoints[0].event_description
        words = first_event.split()[:5]
        title_words = [w.title() for w in words if len(w) > 3][:3]

        if title_words:
            return " ".join(title_words)
        else:
            return f"Simulation with {len(characters)} Characters"

    def _detect_mechanisms_used(self) -> List[str]:
        """Detect which mechanisms were used in this simulation"""
        # This would query metadata or check which tables have data
        # For now, return common mechanisms
        return ["M10", "M11", "M13"]
