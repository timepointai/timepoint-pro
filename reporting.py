# ============================================================================
# reporting.py - Report generation and file output
# ============================================================================
from typing import Dict, List
from datetime import datetime
import json
from pathlib import Path

def generate_report(mode: str, results: Dict, output_dir: str = "reports") -> str:
    """Generate and save detailed report"""
    Path(output_dir).mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{output_dir}/{mode}_report_{timestamp}.json"

    report = {
        "timestamp": datetime.now().isoformat(),
        "mode": mode,
        "results": results,
        "summary": {
            "total_cost": results.get("cost", 0),
            "total_tokens": results.get("tokens", 0),
            "success": results.get("violations", 0) == 0
        }
    }

    with open(filename, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\nReport saved: {filename}")
    return filename

def generate_markdown_report(mode: str, results: Dict, output_dir: str = "reports") -> str:
    """Generate human-readable markdown report"""
    Path(output_dir).mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{output_dir}/{mode}_report_{timestamp}.md"

    lines = [
        f"# Timepoint-Pro {mode.upper()} Report",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Summary",
        f"- **Mode:** {mode}",
        f"- **Cost:** ${results.get('cost', 0):.4f}",
        f"- **Tokens:** {results.get('tokens', 0)}",
        f"- **Violations:** {results.get('violations', 0)}",
        f"- **Entities Evaluated:** {results.get('entities_evaluated', 0)}",
    ]

    # Add resolution distribution if available
    if "resolution_distribution" in results:
        lines.extend([
            "",
            "## Resolution Distribution",
        ])
        for res_level, count in results["resolution_distribution"].items():
            lines.append(f"- **{res_level}:** {count} entities")

    lines.extend([
        "",
        "## Details",
        "```json",
        json.dumps(results, indent=2),
        "```"
    ])

    with open(filename, 'w') as f:
        f.write('\n'.join(lines))

    print(f"Markdown report saved: {filename}")
    return filename
