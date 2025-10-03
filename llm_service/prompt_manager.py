"""
Prompt Management - System and user prompt assembly with templating

Handles prompt construction, variable substitution, and context injection.
"""

from typing import Dict, Any, Optional, List
from string import Template
import json


class PromptManager:
    """
    Manages prompt construction and context injection.

    Supports:
    - Template variable substitution
    - Context enrichment (pre-call)
    - Response filtering (post-call)
    - Schema-to-prompt conversion
    """

    def __init__(self):
        self.global_system_prompt: Optional[str] = None
        self.prompt_templates: Dict[str, str] = {}

    def set_global_system_prompt(self, prompt: str) -> None:
        """Set a global system prompt that's prepended to all calls"""
        self.global_system_prompt = prompt

    def register_template(self, name: str, template: str) -> None:
        """Register a reusable prompt template"""
        self.prompt_templates[name] = template

    def build_prompt(
        self,
        template_name: Optional[str] = None,
        template_str: Optional[str] = None,
        variables: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Build a prompt from template and variables.

        Args:
            template_name: Name of registered template
            template_str: Direct template string
            variables: Variables for template substitution
            context: Additional context for enrichment

        Returns:
            Constructed prompt string
        """
        variables = variables or {}
        context = context or {}

        # Get template
        if template_name:
            if template_name not in self.prompt_templates:
                raise ValueError(f"Template '{template_name}' not registered")
            template = self.prompt_templates[template_name]
        elif template_str:
            template = template_str
        else:
            raise ValueError("Either template_name or template_str must be provided")

        # Substitute variables
        try:
            prompt = Template(template).safe_substitute(**variables)
        except Exception as e:
            raise ValueError(f"Template substitution failed: {e}")

        # Apply context enrichment if needed
        if context:
            prompt = self._enrich_with_context(prompt, context)

        return prompt

    def build_system_prompt(
        self,
        specific_prompt: Optional[str] = None,
        use_global: bool = True
    ) -> str:
        """
        Build system prompt with optional global prepend.

        Args:
            specific_prompt: Specific system prompt for this call
            use_global: Whether to prepend global system prompt

        Returns:
            Combined system prompt
        """
        prompts = []

        if use_global and self.global_system_prompt:
            prompts.append(self.global_system_prompt)

        if specific_prompt:
            prompts.append(specific_prompt)

        return "\n\n".join(prompts) if prompts else ""

    def schema_to_prompt(
        self,
        schema: type,
        instruction: str = "Return a JSON object matching this schema",
        include_example: bool = False
    ) -> str:
        """
        Convert a Pydantic model schema to a prompt string.

        Args:
            schema: Pydantic BaseModel class
            instruction: Instruction text
            include_example: Whether to include example JSON

        Returns:
            Prompt describing the expected schema
        """
        # Get schema dict from Pydantic model
        schema_dict = schema.model_json_schema()

        # Build field descriptions
        fields = []
        if 'properties' in schema_dict:
            for field_name, field_info in schema_dict['properties'].items():
                field_type = field_info.get('type', 'any')
                field_desc = field_info.get('description', '')
                required = field_name in schema_dict.get('required', [])

                field_str = f"- {field_name}: {field_type}"
                if required:
                    field_str += " (required)"
                if field_desc:
                    field_str += f" - {field_desc}"

                fields.append(field_str)

        prompt = f"{instruction}:\n\n"
        prompt += "\n".join(fields)
        prompt += "\n\nReturn only valid JSON, no other text."

        if include_example:
            # Create example with default values
            example = {}
            for field_name, field_info in schema_dict.get('properties', {}).items():
                field_type = field_info.get('type')
                if field_type == 'string':
                    example[field_name] = "example_string"
                elif field_type == 'number':
                    example[field_name] = 0.0
                elif field_type == 'integer':
                    example[field_name] = 0
                elif field_type == 'boolean':
                    example[field_name] = True
                elif field_type == 'array':
                    example[field_name] = []
                elif field_type == 'object':
                    example[field_name] = {}

            prompt += f"\n\nExample:\n```json\n{json.dumps(example, indent=2)}\n```"

        return prompt

    def entity_to_context_string(self, entity: Any) -> str:
        """
        Convert an entity object to a context string for prompts.

        Args:
            entity: Entity object with attributes

        Returns:
            Formatted context string
        """
        context_parts = []

        # Add entity ID
        if hasattr(entity, 'entity_id'):
            context_parts.append(f"Entity: {entity.entity_id}")

        # Add physical state
        if hasattr(entity, 'physical_tensor'):
            physical = entity.physical_tensor
            context_parts.append(f"Physical: age={physical.age}, health={physical.health:.2f}")

        # Add cognitive state
        if hasattr(entity, 'cognitive_tensor'):
            cognitive = entity.cognitive_tensor
            context_parts.append(f"Cognitive: energy={cognitive.energy_budget:.2f}")

        # Add knowledge
        if hasattr(entity, 'knowledge_state') and entity.knowledge_state:
            knowledge_preview = entity.knowledge_state[:3]  # First 3 items
            context_parts.append(f"Knowledge: {knowledge_preview}")

        return "\n".join(context_parts)

    def _enrich_with_context(self, prompt: str, context: Dict[str, Any]) -> str:
        """
        Enrich prompt with additional context information.

        Args:
            prompt: Base prompt
            context: Context dict with enrichment data

        Returns:
            Enriched prompt
        """
        enrichment_parts = []

        # Add temporal context if available
        if 'timepoint' in context:
            enrichment_parts.append(f"Timepoint: {context['timepoint']}")

        # Add entity relationships if available
        if 'relationships' in context:
            enrichment_parts.append(f"Relationships: {context['relationships']}")

        # Add any custom context fields
        for key, value in context.items():
            if key not in ['timepoint', 'relationships'] and isinstance(value, str):
                enrichment_parts.append(f"{key.title()}: {value}")

        if enrichment_parts:
            enrichment = "\n".join(enrichment_parts)
            return f"{prompt}\n\nContext:\n{enrichment}"

        return prompt

    def filter_response_context(
        self,
        response: str,
        remove_patterns: Optional[List[str]] = None,
        add_disclaimers: Optional[List[str]] = None
    ) -> str:
        """
        Post-process response with context filtering.

        Args:
            response: Raw LLM response
            remove_patterns: Regex patterns to remove
            add_disclaimers: Disclaimers to append

        Returns:
            Filtered response
        """
        import re

        filtered = response

        # Remove unwanted patterns
        if remove_patterns:
            for pattern in remove_patterns:
                filtered = re.sub(pattern, '', filtered, flags=re.IGNORECASE)

        # Add disclaimers
        if add_disclaimers:
            disclaimer_text = "\n\n" + "\n".join(add_disclaimers)
            filtered = filtered + disclaimer_text

        return filtered
