"""
Response Parsing - Extract and validate structured outputs from LLM responses

Handles JSON extraction, schema validation, and error recovery.
"""

from typing import Type, TypeVar, Optional, Any, Dict
from pydantic import BaseModel, ValidationError
import json
import re

T = TypeVar('T', bound=BaseModel)


class ParseError(Exception):
    """Exception raised when response parsing fails"""
    pass


class ResponseParser:
    """
    Parses LLM responses into structured formats.

    Supports:
    - JSON extraction from markdown code blocks
    - Robust handling of malformed JSON
    - Pydantic schema validation
    - Type coercion for near-matches
    - Partial validation
    """

    def __init__(self, strict: bool = False):
        """
        Initialize parser.

        Args:
            strict: If True, raise errors on validation failures.
                   If False, attempt coercion and partial matches.
        """
        self.strict = strict

    def extract_json(self, text: str) -> str:
        """
        Extract JSON from LLM response text.

        Handles:
        - Markdown code blocks: ```json ... ```
        - Plain JSON objects
        - Multiple JSON objects (returns first)
        - Extra text before/after JSON

        Args:
            text: Raw LLM response text

        Returns:
            Extracted JSON string

        Raises:
            ParseError: If no valid JSON found
        """
        # Try to extract from markdown code block first
        code_block_patterns = [
            r'```json\s*([\s\S]*?)\s*```',
            r'```\s*([\s\S]*?)\s*```',
        ]

        for pattern in code_block_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                json_text = match.group(1).strip()
                if self._is_valid_json(json_text):
                    return json_text

        # Try to find JSON object directly
        # Look for patterns like { ... } or [ ... ]
        json_patterns = [
            r'\{[\s\S]*\}',  # Object
            r'\[[\s\S]*\]',  # Array
        ]

        for pattern in json_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                json_text = match.group(0).strip()
                if self._is_valid_json(json_text):
                    return json_text

        # If nothing found, try the whole text
        text_stripped = text.strip()
        if self._is_valid_json(text_stripped):
            return text_stripped

        # Provide helpful error message
        preview = text[:500] if len(text) > 500 else text
        raise ParseError(
            f"No valid JSON found in response.\n"
            f"Response preview (first 500 chars):\n{preview}\n\n"
            f"This usually means:\n"
            f"1. The LLM response was truncated (check token limits)\n"
            f"2. The JSON is malformed or incomplete\n"
            f"3. The response contains text but no JSON structure\n"
            f"4. The requested generation was too large for the model"
        )

    def parse_structured(
        self,
        text: str,
        schema: Type[T],
        allow_partial: bool = False
    ) -> T:
        """
        Parse response into a Pydantic model instance.

        Args:
            text: Raw LLM response text
            schema: Pydantic model class
            allow_partial: If True, allow missing required fields

        Returns:
            Instance of schema class

        Raises:
            ParseError: If parsing or validation fails
        """
        # Extract JSON
        try:
            json_str = self.extract_json(text)
        except ParseError as e:
            if self.strict:
                raise
            # Return null-filled instance
            return self._create_null_instance(schema)

        # Parse JSON
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ParseError(f"Invalid JSON: {e}")

        # Validate against schema
        try:
            return schema(**data)
        except ValidationError as e:
            if self.strict:
                raise ParseError(f"Schema validation failed: {e}")

            # Try to coerce and fix
            fixed_data = self._coerce_data(data, schema)

            if allow_partial:
                # Fill missing required fields with defaults
                fixed_data = self._fill_missing_fields(fixed_data, schema)

            try:
                return schema(**fixed_data)
            except ValidationError as e:
                # Last resort: return null instance (only if not strict)
                if self.strict:
                    raise ParseError(f"Schema validation failed: {e}")
                return self._create_null_instance(schema)

    def parse_json(self, text: str) -> Dict[str, Any]:
        """
        Parse response as plain JSON dict (no schema validation).

        Args:
            text: Raw LLM response text

        Returns:
            Parsed JSON as dict

        Raises:
            ParseError: If JSON extraction/parsing fails
        """
        json_str = self.extract_json(text)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ParseError(f"Invalid JSON: {e}")

    def parse_number(self, text: str) -> float:
        """
        Extract a numeric value from response text.

        Args:
            text: Raw LLM response text

        Returns:
            Extracted number

        Raises:
            ParseError: If no valid number found
        """
        # Try to parse as direct number
        text = text.strip()
        try:
            return float(text)
        except ValueError:
            pass

        # Look for numbers in text
        number_pattern = r'[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?'
        matches = re.findall(number_pattern, text)

        if matches:
            # Return first match
            return float(matches[0][0] if isinstance(matches[0], tuple) else matches[0])

        raise ParseError(f"No valid number found in: {text}")

    def _is_valid_json(self, text: str) -> bool:
        """Check if text is valid JSON"""
        try:
            json.loads(text)
            return True
        except (json.JSONDecodeError, ValueError):
            return False

    def _coerce_data(self, data: Dict[str, Any], schema: Type[BaseModel]) -> Dict[str, Any]:
        """
        Attempt to coerce data types to match schema.

        Args:
            data: Raw data dict
            schema: Target Pydantic schema

        Returns:
            Coerced data dict
        """
        coerced = {}
        schema_fields = schema.model_fields

        for field_name, value in data.items():
            if field_name not in schema_fields:
                continue  # Skip unknown fields

            field_info = schema_fields[field_name]
            field_type = field_info.annotation

            # Try type coercion
            try:
                # String to number
                if field_type in (int, float) and isinstance(value, str):
                    coerced[field_name] = field_type(value)
                # Number to string
                elif field_type == str and isinstance(value, (int, float)):
                    coerced[field_name] = str(value)
                # List to set, set to list
                elif field_type == list and isinstance(value, set):
                    coerced[field_name] = list(value)
                elif field_type == set and isinstance(value, list):
                    coerced[field_name] = set(value)
                else:
                    coerced[field_name] = value
            except (ValueError, TypeError):
                coerced[field_name] = value  # Keep original if coercion fails

        return coerced

    def _fill_missing_fields(self, data: Dict[str, Any], schema: Type[BaseModel]) -> Dict[str, Any]:
        """
        Fill missing required fields with default values.

        Args:
            data: Partial data dict
            schema: Target Pydantic schema

        Returns:
            Data with filled defaults
        """
        filled = data.copy()
        schema_fields = schema.model_fields

        for field_name, field_info in schema_fields.items():
            if field_name not in filled:
                # Use field default if available
                if field_info.default is not None:
                    filled[field_name] = field_info.default
                elif field_info.default_factory is not None:
                    filled[field_name] = field_info.default_factory()
                else:
                    # Generate type-appropriate default
                    field_type = field_info.annotation
                    filled[field_name] = self._get_type_default(field_type)

        return filled

    def _get_type_default(self, field_type: Any) -> Any:
        """Get a sensible default value for a field type"""
        if field_type == str:
            return ""
        elif field_type == int:
            return 0
        elif field_type == float:
            return 0.0
        elif field_type == bool:
            return False
        elif field_type == list:
            return []
        elif field_type == dict:
            return {}
        elif field_type == set:
            return set()
        else:
            return None

    def _create_null_instance(self, schema: Type[T]) -> T:
        """
        Create a null-filled instance of a schema.

        Args:
            schema: Pydantic model class

        Returns:
            Instance with all fields set to default/null values
        """
        defaults = {}
        for field_name, field_info in schema.model_fields.items():
            if field_info.default is not None:
                defaults[field_name] = field_info.default
            elif field_info.default_factory is not None:
                defaults[field_name] = field_info.default_factory()
            else:
                defaults[field_name] = self._get_type_default(field_info.annotation)

        return schema(**defaults)
