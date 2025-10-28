"""
Export Pipeline for Batch Report Generation and Export

Orchestrates the complete export workflow:
1. Query data from simulation
2. Generate reports in specified formats
3. Export to multiple output formats
4. Optional compression
"""

from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from datetime import datetime, timezone
from .query_engine import EnhancedQueryEngine
from .report_generator import ReportGenerator
from .export_formats import ExportFormatFactory, ExportFormat


class ExportPipeline:
    """
    Orchestrate complete export workflow.

    Example:
        from reporting import ExportPipeline, EnhancedQueryEngine
        from query_interface import QueryInterface

        base_query = QueryInterface(llm_client, graph_store)
        engine = EnhancedQueryEngine(base_query)
        pipeline = ExportPipeline(engine)

        # Export single report
        pipeline.export_report(
            world_id="meeting_001",
            report_type="summary",
            export_format="json",
            output_path="reports/summary.json"
        )

        # Batch export all report types
        pipeline.export_batch(
            world_id="meeting_001",
            report_types=["summary", "relationships", "knowledge"],
            export_formats=["json", "markdown"],
            output_dir="reports/"
        )
    """

    def __init__(self, query_engine: EnhancedQueryEngine):
        """
        Args:
            query_engine: EnhancedQueryEngine instance for data queries
        """
        self.query_engine = query_engine
        self.report_generator = ReportGenerator(query_engine)
        self._export_stats = {
            "reports_generated": 0,
            "files_exported": 0,
            "total_size_bytes": 0
        }

    def export_report(
        self,
        world_id: str,
        report_type: str,
        export_format: str,
        output_path: str,
        compression: Optional[str] = None,
        **report_kwargs
    ) -> Dict[str, Any]:
        """
        Export single report.

        Args:
            world_id: World identifier
            report_type: Report type (summary, relationships, knowledge, entity_comparison, script)
            export_format: Export format (json, jsonl, csv, markdown, fountain, storyboard, pdf)
            output_path: Output file path
            compression: Compression format (None, 'gzip', 'bz2') - not applicable for PDF
            **report_kwargs: Additional arguments for report generation

        Returns:
            Export metadata (path, size, format, etc.)

        Raises:
            ValueError: If report_type not supported
        """
        # Generate report
        report_content = self._generate_report(world_id, report_type, export_format, **report_kwargs)

        # Normalize export format (markdown -> md)
        normalized_format = "md" if export_format.lower() in ["markdown", "md"] else export_format.lower()

        # Special handling for script exports (fountain, storyboard, pdf)
        if export_format.lower() in ["fountain", "storyboard", "pdf"]:
            # Script exports use ScriptData directly, not string content
            exporter = ExportFormatFactory.create(export_format, compression=compression)
            output_path = self._add_extension(output_path, export_format)

            # Export ScriptData directly (report_content is ScriptData for script reports)
            exporter.export(report_content, output_path)

            # Update output_path with compression suffix if applicable
            if compression:
                output_path = self._add_compression_suffix(output_path, compression)

        # For markdown format, write directly (it's already formatted)
        elif export_format.lower() in ["markdown", "md"]:
            output_path = self._add_extension(output_path, "md")
            if compression:
                output_path = self._add_compression_suffix(output_path, compression)
                # Write with compression
                import gzip, bz2
                open_func = gzip.open if compression == 'gzip' else bz2.open
                with open_func(output_path, 'wt', encoding='utf-8') as f:
                    f.write(report_content)
            else:
                Path(output_path).write_text(report_content, encoding='utf-8')
        else:
            # Use export format handlers
            exporter = ExportFormatFactory.create(export_format, compression=compression)
            output_path = self._add_extension(output_path, export_format)

            # Convert report content to appropriate data structure
            data = self._prepare_export_data(report_content, export_format)
            exporter.export(data, output_path)

            # Update output_path with compression suffix if applicable
            if compression:
                output_path = self._add_compression_suffix(output_path, compression)

        # Update stats
        self._export_stats["reports_generated"] += 1
        self._export_stats["files_exported"] += 1
        if Path(output_path).exists():
            self._export_stats["total_size_bytes"] += Path(output_path).stat().st_size

        return {
            "world_id": world_id,
            "report_type": report_type,
            "export_format": export_format,
            "compression": compression,
            "output_path": str(output_path),
            "file_size_bytes": Path(output_path).stat().st_size if Path(output_path).exists() else 0,
            "exported_at": datetime.now(timezone.utc).isoformat()
        }

    def export_batch(
        self,
        world_id: str,
        report_types: List[str],
        export_formats: List[str],
        output_dir: str,
        compression: Optional[str] = None,
        **report_kwargs
    ) -> List[Dict[str, Any]]:
        """
        Export multiple reports in multiple formats.

        Args:
            world_id: World identifier
            report_types: List of report types to generate
            export_formats: List of export formats
            output_dir: Output directory
            compression: Compression format (None, 'gzip', 'bz2')
            **report_kwargs: Additional arguments for report generation

        Returns:
            List of export metadata dictionaries
        """
        # Ensure output directory exists
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        results = []
        for report_type in report_types:
            for export_format in export_formats:
                # Normalize format for filename (markdown -> md)
                file_extension = "md" if export_format.lower() in ["markdown", "md"] else export_format.lower()

                # Generate output filename
                filename = f"{world_id}_{report_type}.{file_extension}"
                file_path = output_path / filename

                # Export report
                result = self.export_report(
                    world_id=world_id,
                    report_type=report_type,
                    export_format=export_format,
                    output_path=str(file_path),
                    compression=compression,
                    **report_kwargs
                )
                results.append(result)

        return results

    def export_world_package(
        self,
        world_id: str,
        output_dir: str,
        formats: Optional[List[str]] = None,
        compression: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Export complete world package with all report types.

        Args:
            world_id: World identifier
            output_dir: Output directory
            formats: Export formats (defaults to ["json", "markdown"])
            compression: Compression format (None, 'gzip', 'bz2')

        Returns:
            Package metadata with list of exported files
        """
        if formats is None:
            formats = ["json", "markdown"]

        # Export all report types
        report_types = ["summary", "relationships", "knowledge"]
        results = self.export_batch(
            world_id=world_id,
            report_types=report_types,
            export_formats=formats,
            output_dir=output_dir,
            compression=compression
        )

        # Create package metadata
        package_metadata = {
            "world_id": world_id,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "report_count": len(results),
            "formats": formats,
            "compression": compression,
            "files": results,
            "total_size_bytes": sum(r["file_size_bytes"] for r in results)
        }

        # Write package metadata
        metadata_path = Path(output_dir) / f"{world_id}_package_metadata.json"
        import json
        metadata_path.write_text(json.dumps(package_metadata, indent=2), encoding='utf-8')

        return package_metadata

    def _generate_report(
        self,
        world_id: str,
        report_type: str,
        format: str,
        **kwargs
    ) -> Any:
        """Generate report content based on type"""
        report_type_lower = report_type.lower()

        if report_type_lower == "summary":
            return self.report_generator.generate_summary_report(
                world_id=world_id,
                format=format,
                **kwargs
            )
        elif report_type_lower == "relationships":
            return self.report_generator.generate_relationship_report(
                world_id=world_id,
                format=format,
                **kwargs
            )
        elif report_type_lower == "knowledge":
            return self.report_generator.generate_knowledge_report(
                world_id=world_id,
                format=format,
                **kwargs
            )
        elif report_type_lower == "entity_comparison":
            # Requires entity_ids parameter
            entity_ids = kwargs.get("entity_ids", [])
            if not entity_ids:
                raise ValueError("entity_comparison report requires 'entity_ids' parameter")
            return self.report_generator.generate_entity_comparison_report(
                world_id=world_id,
                entity_ids=entity_ids,
                format=format,
                **kwargs
            )
        elif report_type_lower == "script":
            # Script/storyboard generation
            return self._generate_script_report(world_id, format, **kwargs)
        else:
            raise ValueError(
                f"Unsupported report type: {report_type}. "
                f"Supported: summary, relationships, knowledge, entity_comparison, script"
            )

    def _generate_script_report(
        self,
        world_id: str,
        format: str,
        **kwargs
    ) -> Any:
        """Generate script/storyboard from simulation data"""
        from .script_generator import ScriptGenerator
        from storage import GraphStore

        # Get database connection from query engine
        # This is a workaround - ideally ExportPipeline would have direct access to store
        if hasattr(self.query_engine, 'base_query') and hasattr(self.query_engine.base_query, 'store'):
            store = self.query_engine.base_query.store
        elif hasattr(self.query_engine, 'store'):
            store = self.query_engine.store
        else:
            # Fallback: create new store connection
            # You may need to adjust the database path
            store = GraphStore("sqlite:///timepoint.db")

        # Generate script structure
        generator = ScriptGenerator(store)

        # Get optional parameters
        title = kwargs.get("title")
        temporal_mode = kwargs.get("temporal_mode", "pearl")

        script_data = generator.generate_script_structure(
            world_id=world_id,
            title=title,
            temporal_mode=temporal_mode
        )

        return script_data

    def _prepare_export_data(self, report_content: str, export_format: str) -> Any:
        """Prepare report content for export format"""
        import json

        # For JSON export, parse the report content
        if export_format.lower() in ["json", "jsonl"]:
            return json.loads(report_content)

        # For CSV, we need structured data (will be handled by formatter)
        # This is a simplified approach - in production, you might want more control
        return report_content

    def _add_extension(self, path: str, extension: str) -> str:
        """Add file extension if not present"""
        path_obj = Path(path)
        if not path_obj.suffix or path_obj.suffix[1:].lower() != extension.lower():
            return str(path_obj) + f".{extension}"
        return path

    def _add_compression_suffix(self, path: str, compression: str) -> str:
        """Add compression suffix to path"""
        if compression == 'gzip':
            return path + '.gz'
        elif compression == 'bz2':
            return path + '.bz2'
        return path

    def get_export_stats(self) -> Dict[str, Any]:
        """Get export statistics"""
        stats = dict(self._export_stats)
        if stats["files_exported"] > 0:
            stats["avg_file_size_bytes"] = stats["total_size_bytes"] / stats["files_exported"]
        else:
            stats["avg_file_size_bytes"] = 0
        return stats

    def clear_stats(self):
        """Clear export statistics"""
        self._export_stats = {
            "reports_generated": 0,
            "files_exported": 0,
            "total_size_bytes": 0
        }
