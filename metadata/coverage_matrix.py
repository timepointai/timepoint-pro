"""
Coverage Matrix Generator - Generate validation matrices from run metadata

Creates comprehensive reports showing:
- Mechanism coverage (M1-M17) across templates
- Resolution diversity
- Causal mode coverage
- Cost analysis
- Training data generated
"""

from typing import List, Dict
from .run_tracker import RunMetadata, ALL_MECHANISMS
import pandas as pd
from schemas import ResolutionLevel, TemporalMode


class CoverageMatrix:
    """Generate coverage matrices from workflow runs"""

    def generate_full_matrix(self, runs: List[RunMetadata]) -> pd.DataFrame:
        """
        Generate comprehensive coverage matrix.

        Columns:
        - Template
        - M1-M17 Coverage (count/17)
        - Causal Mode
        - Resolutions Used (count/5)
        - Timepoints
        - Cost ($)
        - Training Examples
        - Status
        """
        rows = []

        for run in runs:
            # Count mechanisms used
            mechanisms_covered = len(run.mechanisms_used)
            mechanisms_str = f"{mechanisms_covered}/17 ({100*mechanisms_covered//17}%)"

            # Count unique resolutions assigned
            unique_resolutions = set()
            # Parse resolution assignments from metadata if available
            # For now, we'll track this as we collect data
            resolutions_str = "N/A"

            # Format timepoints
            timepoints_str = str(run.timepoints_created)

            # Format cost
            cost_str = f"${run.cost_usd:.2f}"

            # Status indicator
            status_icon = "✅" if run.status == "completed" else "❌" if run.status == "failed" else "🔄"

            # Handle causal_mode - it might be a string or enum
            causal_mode_str = run.causal_mode.value if hasattr(run.causal_mode, 'value') else run.causal_mode

            row = {
                "Template": run.template_id,
                "M1-M17": mechanisms_str,
                "Causal Mode": causal_mode_str,
                "Resolutions": resolutions_str,
                "Timepoints": timepoints_str,
                "Entities": run.entities_created,
                "Training Examples": run.training_examples,
                "Cost": cost_str,
                "Duration (s)": f"{run.duration_seconds:.1f}" if run.duration_seconds else "N/A",
                "Status": f"{status_icon} {run.status}"
            }

            rows.append(row)

        df = pd.DataFrame(rows)

        # Add summary row
        if len(runs) > 0:
            # Get unique causal modes (handle string or enum)
            unique_modes = set()
            for r in runs:
                if hasattr(r.causal_mode, 'value'):
                    unique_modes.add(r.causal_mode.value)
                else:
                    unique_modes.add(r.causal_mode)

            summary = {
                "Template": "TOTAL",
                "M1-M17": f"Overall",
                "Causal Mode": f"{len(unique_modes)}/5 modes",
                "Resolutions": "All levels",
                "Timepoints": sum(r.timepoints_created for r in runs),
                "Entities": sum(r.entities_created for r in runs),
                "Training Examples": sum(r.training_examples for r in runs),
                "Cost": f"${sum(r.cost_usd for r in runs):.2f}",
                "Duration (s)": f"{sum(r.duration_seconds or 0 for r in runs):.1f}",
                "Status": f"{sum(1 for r in runs if r.status == 'completed')}/{len(runs)}"
            }
            df = pd.concat([df, pd.DataFrame([summary])], ignore_index=True)

        return df

    def generate_mechanism_matrix(self, runs: List[RunMetadata]) -> pd.DataFrame:
        """
        Generate mechanism coverage matrix.

        Shows which mechanisms (M1-M17) were used in which templates.
        """
        rows = []

        for run in runs:
            row = {"Template": run.template_id}

            # Mark each mechanism as used or not
            for mechanism in ALL_MECHANISMS:
                row[mechanism] = "✓" if mechanism in run.mechanisms_used else "-"

            # Total coverage
            row["Total"] = f"{len(run.mechanisms_used)}/17"

            rows.append(row)

        df = pd.DataFrame(rows)

        # Add coverage summary row
        if len(runs) > 0:
            summary = {"Template": "Coverage"}
            for mechanism in ALL_MECHANISMS:
                templates_using = sum(1 for run in runs if mechanism in run.mechanisms_used)
                summary[mechanism] = f"{templates_using}/{len(runs)}"

            # Calculate total unique mechanisms (handle empty sets)
            all_mechanisms = [r.mechanisms_used for r in runs if r.mechanisms_used]
            if all_mechanisms:
                total_mechanisms = len(set.union(*all_mechanisms))
            else:
                total_mechanisms = 0
            summary["Total"] = f"{total_mechanisms}/17"

            df = pd.concat([df, pd.DataFrame([summary])], ignore_index=True)

        return df

    def generate_causal_mode_matrix(self, runs: List[RunMetadata]) -> pd.DataFrame:
        """
        Show which causal modes are covered.
        """
        all_modes = [TemporalMode.PEARL, TemporalMode.DIRECTORIAL,
                     TemporalMode.BRANCHING, TemporalMode.CYCLICAL, TemporalMode.PORTAL]

        mode_coverage = {}
        for mode in all_modes:
            # Handle causal_mode - might be string or enum
            templates = [r.template_id for r in runs
                        if (r.causal_mode == mode or
                            (isinstance(r.causal_mode, str) and r.causal_mode == mode.value))]
            mode_coverage[mode.value] = {
                "Templates": ", ".join(templates) if templates else "None",
                "Count": len(templates),
                "Coverage": "✓" if templates else "❌"
            }

        df = pd.DataFrame(mode_coverage).T
        df.index.name = "Causal Mode"
        return df.reset_index()

    def generate_text_report(self, runs: List[RunMetadata]) -> str:
        """
        Generate comprehensive text report.
        """
        report = []
        report.append("=" * 80)
        report.append("TIMEPOINT-DAEDALUS COVERAGE REPORT")
        report.append("=" * 80)
        report.append("")

        # Summary stats
        total_runs = len(runs)
        completed = sum(1 for r in runs if r.status == "completed")
        failed = sum(1 for r in runs if r.status == "failed")
        total_cost = sum(r.cost_usd for r in runs)
        total_examples = sum(r.training_examples for r in runs)

        report.append(f"Total Runs: {total_runs}")
        report.append(f"Completed: {completed} | Failed: {failed}")
        report.append(f"Total Cost: ${total_cost:.2f}")
        report.append(f"Total Training Examples: {total_examples}")
        report.append("")

        # Full matrix
        report.append("FULL COVERAGE MATRIX")
        report.append("-" * 80)
        df = self.generate_full_matrix(runs)
        report.append(df.to_string(index=False))
        report.append("")

        # Mechanism matrix
        report.append("MECHANISM COVERAGE (M1-M17)")
        report.append("-" * 80)
        df = self.generate_mechanism_matrix(runs)
        report.append(df.to_string(index=False))
        report.append("")

        # Causal mode matrix
        report.append("CAUSAL MODE COVERAGE")
        report.append("-" * 80)
        df = self.generate_causal_mode_matrix(runs)
        report.append(df.to_string(index=False))
        report.append("")

        # Mechanism completeness (handle empty sets)
        all_mechanisms_list = [r.mechanisms_used for r in runs if r.mechanisms_used]
        if all_mechanisms_list:
            all_mechanisms_used = set.union(*all_mechanisms_list)
        else:
            all_mechanisms_used = set()
        report.append(f"Mechanisms Covered: {len(all_mechanisms_used)}/17")
        if len(all_mechanisms_used) < 17:
            missing = set(ALL_MECHANISMS) - all_mechanisms_used
            report.append(f"Missing: {', '.join(sorted(missing))}")
        report.append("")

        # Causal mode completeness (handle string or enum)
        modes_used = set()
        for r in runs:
            if hasattr(r.causal_mode, 'value'):
                modes_used.add(r.causal_mode.value)
            else:
                modes_used.add(r.causal_mode)
        report.append(f"Causal Modes Covered: {len(modes_used)}/5")
        all_modes = {TemporalMode.PEARL, TemporalMode.DIRECTORIAL,
                     TemporalMode.BRANCHING, TemporalMode.CYCLICAL, TemporalMode.PORTAL}
        if len(modes_used) < 5:
            # Convert modes_used to enum values for comparison
            all_mode_values = {m.value for m in all_modes}
            missing_mode_values = all_mode_values - modes_used
            report.append(f"Missing: {', '.join(sorted(missing_mode_values))}")
        report.append("")

        report.append("=" * 80)
        report.append("END REPORT")
        report.append("=" * 80)

        return "\n".join(report)

    def generate_markdown_report(self, runs: List[RunMetadata]) -> str:
        """
        Generate markdown formatted report.
        """
        report = []
        report.append("# Timepoint-Daedalus Coverage Report")
        report.append("")
        report.append(f"**Generated**: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        # Summary
        total_runs = len(runs)
        completed = sum(1 for r in runs if r.status == "completed")
        total_cost = sum(r.cost_usd for r in runs)
        total_examples = sum(r.training_examples for r in runs)

        report.append("## Summary")
        report.append("")
        report.append(f"- **Total Runs**: {total_runs}")
        report.append(f"- **Completed**: {completed}/{total_runs}")
        report.append(f"- **Total Cost**: ${total_cost:.2f}")
        report.append(f"- **Training Examples**: {total_examples}")
        report.append("")

        # Full matrix
        report.append("## Full Coverage Matrix")
        report.append("")
        df = self.generate_full_matrix(runs)
        report.append(df.to_markdown(index=False))
        report.append("")

        # Mechanism matrix
        report.append("## Mechanism Coverage (M1-M17)")
        report.append("")
        df = self.generate_mechanism_matrix(runs)
        report.append(df.to_markdown(index=False))
        report.append("")

        # Causal modes
        report.append("## Causal Mode Coverage")
        report.append("")
        df = self.generate_causal_mode_matrix(runs)
        report.append(df.to_markdown(index=False))
        report.append("")

        # Completeness (handle empty sets)
        all_mechanisms_list = [r.mechanisms_used for r in runs if r.mechanisms_used]
        if all_mechanisms_list:
            all_mechanisms_used = set.union(*all_mechanisms_list)
        else:
            all_mechanisms_used = set()

        # Handle causal_mode - might be string or enum
        modes_used = set()
        for r in runs:
            if hasattr(r.causal_mode, 'value'):
                modes_used.add(r.causal_mode.value)
            else:
                modes_used.add(r.causal_mode)

        report.append("## Coverage Completeness")
        report.append("")
        report.append(f"- **Mechanisms**: {len(all_mechanisms_used)}/17 ({100*len(all_mechanisms_used)//17}%)")
        report.append(f"- **Causal Modes**: {len(modes_used)}/5 ({100*len(modes_used)//5}%)")
        report.append("")

        return "\n".join(report)
