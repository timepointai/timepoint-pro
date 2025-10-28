"""
Export Format Implementations

Supports multiple export formats with compression:
- JSONL (JSON Lines) - Streaming format for large datasets
- JSON - Standard JSON export
- CSV - Comma-separated values
- SQLite - Embedded database export
"""

from typing import Dict, Any, List, Optional, IO
import json
import csv
import gzip
import bz2
from pathlib import Path
from abc import ABC, abstractmethod
from io import StringIO
import sqlite3


class ExportFormat(ABC):
    """Base class for export formats"""

    def __init__(self, compression: Optional[str] = None):
        """
        Args:
            compression: Compression format (None, 'gzip', 'bz2')
        """
        self.compression = compression

    @abstractmethod
    def export(self, data: Any, output_path: str) -> None:
        """
        Export data to file.

        Args:
            data: Data to export
            output_path: Output file path
        """
        pass

    def _open_file(self, path: str, mode: str = 'w') -> IO:
        """Open file with optional compression"""
        if self.compression == 'gzip':
            return gzip.open(path, mode + 't', encoding='utf-8')
        elif self.compression == 'bz2':
            return bz2.open(path, mode + 't', encoding='utf-8')
        else:
            return open(path, mode, encoding='utf-8')

    def _add_compression_suffix(self, path: str) -> str:
        """Add compression suffix to path if applicable"""
        if self.compression == 'gzip':
            return path + '.gz'
        elif self.compression == 'bz2':
            return path + '.bz2'
        return path


class JSONLExporter(ExportFormat):
    """
    Export data in JSONL (JSON Lines) format.

    Each line is a valid JSON object, making it ideal for:
    - Streaming large datasets
    - Line-by-line processing
    - Append operations
    """

    def export(self, data: List[Dict[str, Any]], output_path: str) -> None:
        """
        Export list of dictionaries as JSONL.

        Args:
            data: List of dictionaries to export
            output_path: Output file path (e.g., 'output.jsonl')
        """
        output_path = self._add_compression_suffix(output_path)

        with self._open_file(output_path, 'w') as f:
            for item in data:
                json_line = json.dumps(item, default=str)
                f.write(json_line + '\n')

    def export_stream(self, data_generator, output_path: str) -> None:
        """
        Export data from generator (for large datasets).

        Args:
            data_generator: Generator yielding dictionaries
            output_path: Output file path
        """
        output_path = self._add_compression_suffix(output_path)

        with self._open_file(output_path, 'w') as f:
            for item in data_generator:
                json_line = json.dumps(item, default=str)
                f.write(json_line + '\n')


class JSONExporter(ExportFormat):
    """Export data in standard JSON format"""

    def __init__(self, compression: Optional[str] = None, indent: int = 2):
        """
        Args:
            compression: Compression format (None, 'gzip', 'bz2')
            indent: Indentation level for pretty printing
        """
        super().__init__(compression)
        self.indent = indent

    def export(self, data: Any, output_path: str) -> None:
        """
        Export data as JSON.

        Args:
            data: Data to export (dict, list, etc.)
            output_path: Output file path (e.g., 'output.json')
        """
        output_path = self._add_compression_suffix(output_path)

        with self._open_file(output_path, 'w') as f:
            json.dump(data, f, indent=self.indent, default=str)


class CSVExporter(ExportFormat):
    """Export data in CSV format"""

    def __init__(self, compression: Optional[str] = None, delimiter: str = ','):
        """
        Args:
            compression: Compression format (None, 'gzip', 'bz2')
            delimiter: CSV delimiter (default: ',')
        """
        super().__init__(compression)
        self.delimiter = delimiter

    def export(self, data: List[Dict[str, Any]], output_path: str) -> None:
        """
        Export list of dictionaries as CSV.

        Args:
            data: List of dictionaries with consistent keys
            output_path: Output file path (e.g., 'output.csv')
        """
        if not data:
            # Create empty file
            Path(output_path).touch()
            return

        output_path = self._add_compression_suffix(output_path)

        # Get headers from first item
        headers = list(data[0].keys())

        with self._open_file(output_path, 'w') as f:
            writer = csv.DictWriter(f, fieldnames=headers, delimiter=self.delimiter)
            writer.writeheader()
            for row in data:
                # Convert complex types to strings
                cleaned_row = {}
                for key, value in row.items():
                    if isinstance(value, (dict, list)):
                        cleaned_row[key] = json.dumps(value)
                    else:
                        cleaned_row[key] = value
                writer.writerow(cleaned_row)


class SQLiteExporter(ExportFormat):
    """
    Export data to SQLite database.

    Note: SQLite exporter doesn't support compression (binary format already efficient).
    """

    def __init__(self):
        """SQLite exporter (compression not applicable)"""
        super().__init__(compression=None)

    def export(
        self,
        data: Dict[str, List[Dict[str, Any]]],
        output_path: str,
        overwrite: bool = False
    ) -> None:
        """
        Export data to SQLite database.

        Args:
            data: Dictionary mapping table names to list of records
            output_path: Output database path (e.g., 'output.db')
            overwrite: Whether to overwrite existing database

        Example:
            data = {
                "entities": [{"id": 1, "name": "Alice"}, ...],
                "timepoints": [{"id": 0, "timestamp": "..."}, ...]
            }
        """
        # Check if file exists
        db_exists = Path(output_path).exists()
        if db_exists and not overwrite:
            raise FileExistsError(
                f"Database {output_path} already exists. Set overwrite=True to replace."
            )

        # Remove existing file if overwriting
        if db_exists and overwrite:
            Path(output_path).unlink()

        # Create database
        conn = sqlite3.connect(output_path)
        cursor = conn.cursor()

        try:
            for table_name, records in data.items():
                if not records:
                    continue

                # Infer schema from first record
                first_record = records[0]
                columns = list(first_record.keys())
                column_types = []

                for key, value in first_record.items():
                    if isinstance(value, bool):
                        column_types.append(f"{key} INTEGER")
                    elif isinstance(value, int):
                        column_types.append(f"{key} INTEGER")
                    elif isinstance(value, float):
                        column_types.append(f"{key} REAL")
                    elif isinstance(value, (dict, list)):
                        column_types.append(f"{key} TEXT")  # Store as JSON
                    else:
                        column_types.append(f"{key} TEXT")

                # Create table
                create_sql = f"CREATE TABLE {table_name} ({', '.join(column_types)})"
                cursor.execute(create_sql)

                # Insert records
                placeholders = ', '.join(['?' for _ in columns])
                insert_sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"

                for record in records:
                    values = []
                    for col in columns:
                        value = record.get(col)
                        if isinstance(value, (dict, list)):
                            values.append(json.dumps(value))
                        else:
                            values.append(value)
                    cursor.execute(insert_sql, values)

            conn.commit()
        finally:
            conn.close()


class FountainExporter(ExportFormat):
    """
    Export screenplay data in Fountain format (.fountain).

    Fountain is a plain text markup language for screenwriting.
    This exporter works with ScriptData structures and outputs
    industry-standard Fountain format.
    """

    def export(self, script_data: Any, output_path: str) -> None:
        """
        Export ScriptData to Fountain format.

        Args:
            script_data: ScriptData structure from ScriptGenerator
            output_path: Output file path (e.g., 'screenplay.fountain')
        """
        from .formatters import FountainFormatter

        output_path = self._add_compression_suffix(output_path)

        # Format script as Fountain text
        formatter = FountainFormatter()
        fountain_text = formatter.format(script_data)

        # Write to file
        with self._open_file(output_path, 'w') as f:
            f.write(fountain_text)


class StoryboardJSONExporter(ExportFormat):
    """
    Export storyboard data as structured JSON.

    Provides detailed scene-by-scene breakdown with production metadata,
    suitable for programmatic access and visual storyboard tools.
    """

    def __init__(self, compression: Optional[str] = None, indent: int = 2):
        """
        Args:
            compression: Compression format (None, 'gzip', 'bz2')
            indent: Indentation level for pretty printing
        """
        super().__init__(compression)
        self.indent = indent

    def export(self, script_data: Any, output_path: str) -> None:
        """
        Export ScriptData to storyboard JSON format.

        Args:
            script_data: ScriptData structure from ScriptGenerator
            output_path: Output file path (e.g., 'storyboard.json')
        """
        from .formatters import StoryboardJSONFormatter

        output_path = self._add_compression_suffix(output_path)

        # Format script as storyboard JSON
        formatter = StoryboardJSONFormatter()
        storyboard_data = formatter.format(script_data)

        # Write to file
        with self._open_file(output_path, 'w') as f:
            json.dump(storyboard_data, f, indent=self.indent, default=str)


class PDFExporter(ExportFormat):
    """
    Export screenplay data as PDF.

    Generates industry-standard screenplay PDFs with:
    - Courier 12pt font
    - Proper margins (1.5" left, 1" right, 1" top, 1" bottom)
    - Correct formatting for scene headings, action, character, dialog
    """

    def __init__(self, compression: Optional[str] = None):
        """
        Args:
            compression: Not applicable for PDF (binary format)
        """
        super().__init__(compression=None)  # PDF doesn't support text compression

    def export(self, script_data: Any, output_path: str) -> None:
        """
        Export ScriptData to PDF format.

        Args:
            script_data: ScriptData structure from ScriptGenerator
            output_path: Output file path (e.g., 'screenplay.pdf')
        """
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import inch
        from reportlab.pdfgen import canvas
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
        from reportlab.lib.enums import TA_LEFT, TA_CENTER

        # Ensure .pdf extension
        if not output_path.endswith('.pdf'):
            output_path = output_path + '.pdf'

        # Create PDF document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            leftMargin=1.5 * inch,
            rightMargin=1.0 * inch,
            topMargin=1.0 * inch,
            bottomMargin=1.0 * inch
        )

        # Build content
        story = []

        # Title page
        story.extend(self._build_title_page(script_data))
        story.append(PageBreak())

        # Screenplay content
        for scene in script_data.scenes:
            story.extend(self._build_scene(scene))

        # Build PDF
        doc.build(story)

    def _build_title_page(self, script_data) -> List:
        """Build title page elements"""
        from reportlab.platypus import Paragraph, Spacer
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.units import inch

        elements = []

        # Title style
        title_style = ParagraphStyle(
            'Title',
            fontName='Courier-Bold',
            fontSize=24,
            alignment=TA_CENTER,
            spaceAfter=12
        )

        # Subtitle style
        subtitle_style = ParagraphStyle(
            'Subtitle',
            fontName='Courier',
            fontSize=12,
            alignment=TA_CENTER,
            spaceAfter=6
        )

        # Add vertical space
        elements.append(Spacer(1, 2 * inch))

        # Title
        elements.append(Paragraph(script_data.title, title_style))
        elements.append(Spacer(1, 0.5 * inch))

        # Metadata
        if script_data.world_id:
            elements.append(Paragraph(f"World ID: {script_data.world_id}", subtitle_style))

        elements.append(Paragraph(f"Temporal Mode: {script_data.temporal_mode.title()}", subtitle_style))
        elements.append(Spacer(1, 0.25 * inch))

        # Generated timestamp
        timestamp = script_data.generated_at.strftime("%B %d, %Y")
        elements.append(Paragraph(timestamp, subtitle_style))

        elements.append(Spacer(1, 0.5 * inch))
        elements.append(Paragraph("Generated by Timepoint-Daedalus", subtitle_style))

        return elements

    def _build_scene(self, scene) -> List:
        """Build scene elements"""
        from reportlab.platypus import Paragraph, Spacer
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.enums import TA_LEFT
        from reportlab.lib.units import inch

        elements = []

        # Scene heading style (ALL CAPS, bold)
        heading_style = ParagraphStyle(
            'SceneHeading',
            fontName='Courier-Bold',
            fontSize=12,
            alignment=TA_LEFT,
            spaceAfter=12,
            spaceBefore=12
        )

        # Action style
        action_style = ParagraphStyle(
            'Action',
            fontName='Courier',
            fontSize=12,
            alignment=TA_LEFT,
            spaceAfter=12
        )

        # Character style (ALL CAPS, indented)
        character_style = ParagraphStyle(
            'Character',
            fontName='Courier',
            fontSize=12,
            alignment=TA_LEFT,
            leftIndent=2.2 * inch,
            spaceAfter=0
        )

        # Dialog style (indented)
        dialog_style = ParagraphStyle(
            'Dialog',
            fontName='Courier',
            fontSize=12,
            alignment=TA_LEFT,
            leftIndent=1.0 * inch,
            rightIndent=1.5 * inch,
            spaceAfter=12
        )

        # Parenthetical style (indented more)
        paren_style = ParagraphStyle(
            'Parenthetical',
            fontName='Courier',
            fontSize=12,
            alignment=TA_LEFT,
            leftIndent=1.5 * inch,
            spaceAfter=0
        )

        # Scene heading
        elements.append(Paragraph(scene.heading, heading_style))

        # Scene description
        if scene.description:
            elements.append(Paragraph(scene.description, action_style))

        # Interleave action beats and dialog (matching FountainFormatter approach)
        if scene.dialog:
            action_idx = 0
            dialog_idx = 0

            while action_idx < len(scene.action_beats) or dialog_idx < len(scene.dialog):
                # Add action beat
                if action_idx < len(scene.action_beats):
                    elements.append(Paragraph(scene.action_beats[action_idx], action_style))
                    action_idx += 1

                # Add dialog line
                if dialog_idx < len(scene.dialog):
                    dialog_line = scene.dialog[dialog_idx]

                    # Character name (all caps)
                    character_name = dialog_line.speaker.replace("_", " ").upper()
                    elements.append(Paragraph(character_name, character_style))

                    # Parenthetical (if present)
                    if dialog_line.parenthetical:
                        paren_text = f"({dialog_line.parenthetical})"
                        elements.append(Paragraph(paren_text, paren_style))

                    # Dialog text
                    elements.append(Paragraph(dialog_line.content, dialog_style))

                    dialog_idx += 1
        else:
            # No dialog, just action beats
            for beat in scene.action_beats:
                elements.append(Paragraph(beat, action_style))

        # Add space after scene
        elements.append(Spacer(1, 0.25 * inch))

        return elements


class ExportFormatFactory:
    """Factory for creating export format instances"""

    _formats = {
        "jsonl": JSONLExporter,
        "json": JSONExporter,
        "csv": CSVExporter,
        "sqlite": SQLiteExporter,
        "db": SQLiteExporter,  # Alias
        "fountain": FountainExporter,
        "storyboard": StoryboardJSONExporter,
        "pdf": PDFExporter
    }

    @classmethod
    def create(cls, format: str, **kwargs) -> ExportFormat:
        """
        Create export format instance.

        Args:
            format: Format name (jsonl, json, csv, sqlite)
            **kwargs: Additional arguments for format

        Returns:
            ExportFormat instance

        Raises:
            ValueError: If format not supported

        Example:
            # JSONL with gzip compression
            exporter = ExportFormatFactory.create("jsonl", compression="gzip")

            # JSON with custom indent
            exporter = ExportFormatFactory.create("json", indent=4)

            # CSV with custom delimiter
            exporter = ExportFormatFactory.create("csv", delimiter="|")
        """
        format_lower = format.lower()
        if format_lower not in cls._formats:
            raise ValueError(
                f"Unsupported format: {format}. "
                f"Supported: {list(cls._formats.keys())}"
            )

        return cls._formats[format_lower](**kwargs)

    @classmethod
    def get_supported_formats(cls) -> List[str]:
        """Get list of supported formats"""
        return list(cls._formats.keys())
