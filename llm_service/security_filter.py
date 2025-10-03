"""
Security Filter - Input bleaching and output sanitization

Protects against:
- Prompt injection attacks
- HTML/script injection
- Excessive input lengths
- Harmful content in responses
"""

from typing import List, Optional
import re
import html


class SecurityFilter:
    """
    Applies security controls to LLM inputs and outputs.

    Features:
    - Input bleaching (remove dangerous patterns)
    - HTML tag removal
    - Script injection prevention
    - Length limits
    - Output sanitization
    - PII detection (optional)
    """

    def __init__(
        self,
        max_input_length: int = 50000,
        dangerous_patterns: Optional[List[str]] = None,
        strict_mode: bool = False,
    ):
        """
        Initialize security filter.

        Args:
            max_input_length: Maximum allowed input length
            dangerous_patterns: List of regex patterns to block
            strict_mode: If True, raise errors on violations; if False, sanitize
        """
        self.max_input_length = max_input_length
        self.strict_mode = strict_mode

        # Default dangerous patterns
        self.dangerous_patterns = dangerous_patterns or [
            r"(?i)ignore.*previous.*instructions",
            r"(?i)forget.*system.*prompt",
            r"(?i)disregard.*rules",
            r"(?i)you are now.*",
            r"(?i)new instructions?:",
            r"<script[^>]*>.*?</script>",
            r"javascript:",
            r"on\w+\s*=",  # Event handlers like onclick=
        ]

        # Compile patterns for efficiency
        self.compiled_patterns = [
            re.compile(pattern, re.IGNORECASE | re.DOTALL)
            for pattern in self.dangerous_patterns
        ]

    def bleach_input(self, text: str) -> str:
        """
        Sanitize user input before sending to LLM.

        Args:
            text: Raw input text

        Returns:
            Sanitized text

        Raises:
            ValueError: If strict_mode=True and violations found
        """
        if not text:
            return text

        # Check length
        if len(text) > self.max_input_length:
            if self.strict_mode:
                raise ValueError(
                    f"Input exceeds maximum length: {len(text)} > {self.max_input_length}"
                )
            text = text[:self.max_input_length]

        # Remove HTML tags (preserve content)
        text = self._remove_html_tags(text)

        # Check for dangerous patterns
        for pattern in self.compiled_patterns:
            if pattern.search(text):
                if self.strict_mode:
                    raise ValueError(f"Input contains dangerous pattern: {pattern.pattern}")
                # Remove matched content
                text = pattern.sub('', text)

        # Remove SQL injection patterns
        text = self._remove_sql_injection(text)

        # Normalize whitespace
        text = self._normalize_whitespace(text)

        return text

    def sanitize_output(self, text: str) -> str:
        """
        Sanitize LLM output before storage/display.

        Args:
            text: Raw LLM response

        Returns:
            Sanitized response
        """
        if not text:
            return text

        # Remove any HTML/script tags that LLM might have generated
        text = self._remove_html_tags(text)

        # Remove potential code execution patterns
        text = self._remove_code_execution(text)

        # Normalize encoding
        text = self._normalize_encoding(text)

        return text

    def detect_pii(self, text: str) -> List[str]:
        """
        Detect potential PII in text (basic detection).

        Args:
            text: Text to scan

        Returns:
            List of detected PII types
        """
        pii_found = []

        # Email addresses
        if re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text):
            pii_found.append("email")

        # Phone numbers (US format)
        if re.search(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', text):
            pii_found.append("phone")

        # SSN pattern
        if re.search(r'\b\d{3}-\d{2}-\d{4}\b', text):
            pii_found.append("ssn")

        # Credit card numbers (basic pattern)
        if re.search(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', text):
            pii_found.append("credit_card")

        return pii_found

    def redact_pii(self, text: str) -> str:
        """
        Redact detected PII from text.

        Args:
            text: Text with potential PII

        Returns:
            Text with PII redacted
        """
        # Email
        text = re.sub(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            '[EMAIL_REDACTED]',
            text
        )

        # Phone numbers
        text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE_REDACTED]', text)

        # SSN
        text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN_REDACTED]', text)

        # Credit cards
        text = re.sub(
            r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
            '[CARD_REDACTED]',
            text
        )

        return text

    def _remove_html_tags(self, text: str) -> str:
        """Remove HTML tags while preserving content"""
        # Unescape HTML entities first
        text = html.unescape(text)

        # Remove tags
        text = re.sub(r'<[^>]+>', '', text)

        return text

    def _remove_sql_injection(self, text: str) -> str:
        """Remove common SQL injection patterns"""
        sql_patterns = [
            r"(?i)(union|select|insert|update|delete|drop|create|alter|exec|execute)\s+(from|into|table|database)",
            r"(?i)(--|#|\/\*|\*\/)",  # SQL comments
            r"(?i)'.*or.*'.*=.*'",  # Classic OR injection
        ]

        for pattern in sql_patterns:
            text = re.sub(pattern, '', text)

        return text

    def _remove_code_execution(self, text: str) -> str:
        """Remove patterns that could lead to code execution"""
        # Remove eval-like patterns
        text = re.sub(r'(?i)(eval|exec|__import__|compile)\s*\(', '', text)

        # Remove system command patterns
        text = re.sub(r'(?i)(system|popen|subprocess|os\.)\s*\(', '', text)

        return text

    def _normalize_whitespace(self, text: str) -> str:
        """Normalize excessive whitespace"""
        # Replace multiple spaces with single space
        text = re.sub(r' +', ' ', text)

        # Replace multiple newlines with double newline
        text = re.sub(r'\n\n+', '\n\n', text)

        # Strip leading/trailing whitespace
        text = text.strip()

        return text

    def _normalize_encoding(self, text: str) -> str:
        """Normalize text encoding"""
        # Convert to UTF-8 compatible format
        try:
            text = text.encode('utf-8', errors='ignore').decode('utf-8')
        except Exception:
            pass  # Keep original if encoding fails

        return text

    def validate_json_safe(self, json_str: str) -> bool:
        """
        Check if JSON string is safe (no code execution risks).

        Args:
            json_str: JSON string to validate

        Returns:
            True if safe, False if risky patterns detected
        """
        # Check for dangerous function calls in JSON values
        dangerous_in_json = [
            r'__proto__',
            r'constructor',
            r'prototype',
            r'eval',
            r'function\s*\(',
        ]

        for pattern in dangerous_in_json:
            if re.search(pattern, json_str, re.IGNORECASE):
                return False

        return True

    def get_filter_statistics(self) -> dict:
        """Get statistics on filtering operations"""
        return {
            "max_input_length": self.max_input_length,
            "dangerous_patterns_count": len(self.dangerous_patterns),
            "strict_mode": self.strict_mode,
        }
