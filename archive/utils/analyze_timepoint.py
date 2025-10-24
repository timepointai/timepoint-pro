#!/usr/bin/env python3
"""
Timepoint-Daedalus Codebase Analyzer
Generates REPORT.md with ground truth about the project state
"""

import os
import json
import subprocess
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict

def run_command(cmd, cwd="."):
    """Run shell command and return output"""
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            cwd=cwd, 
            capture_output=True, 
            text=True,
            timeout=30
        )
        return result.stdout, result.stderr, result.returncode
    except Exception as e:
        return "", str(e), 1

def count_lines(filepath):
    """Count lines in a file"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return len(f.readlines())
    except:
        return 0

def analyze_file_structure():
    """Analyze project file structure"""
    print("📁 Analyzing file structure...")
    
    py_files = list(Path('.').glob('*.py'))
    test_files = list(Path('.').glob('test_*.py'))
    md_files = list(Path('.').glob('*.md'))
    
    # Count lines of code
    total_lines = 0
    file_stats = {}
    
    for f in py_files:
        lines = count_lines(f)
        total_lines += lines
        file_stats[f.name] = lines
    
    # Sort by size
    sorted_files = sorted(file_stats.items(), key=lambda x: x[1], reverse=True)
    
    return {
        'py_files': len(py_files),
        'test_files': len(test_files),
        'md_files': len(md_files),
        'total_lines': total_lines,
        'largest_files': sorted_files[:10],
        'all_py_files': [f.name for f in py_files],
        'all_test_files': [f.name for f in test_files],
        'all_md_files': [f.name for f in md_files]
    }

def analyze_tests():
    """Run pytest and analyze test results"""
    print("🧪 Analyzing test suite...")
    
    # Collect tests
    stdout, stderr, code = run_command("pytest --collect-only -q")
    
    total_tests = 0
    test_by_file = defaultdict(int)
    
    for line in stdout.split('\n'):
        if '::' in line and 'test_' in line:
            total_tests += 1
            filename = line.split('::')[0]
            test_by_file[filename] += 1
    
    # Try to run tests (with timeout)
    print("   Running test suite (this may take a minute)...")
    stdout, stderr, code = run_command("pytest -v --tb=no --timeout=60 2>&1", cwd=".")
    
    # Parse results
    passed = len(re.findall(r'PASSED', stdout))
    failed = len(re.findall(r'FAILED', stdout))
    skipped = len(re.findall(r'SKIPPED', stdout))
    errors = len(re.findall(r'ERROR', stdout))
    
    # Get test markers
    marker_stdout, _, _ = run_command("pytest --markers")
    
    # Extract custom markers
    custom_markers = []
    for line in marker_stdout.split('\n'):
        if line.startswith('  @pytest.mark.'):
            marker = line.split('  @pytest.mark.')[1].split(':')[0]
            custom_markers.append(marker)
    
    return {
        'total_collected': total_tests,
        'passed': passed,
        'failed': failed,
        'skipped': skipped,
        'errors': errors,
        'by_file': dict(test_by_file),
        'markers': custom_markers[:15],  # Limit output
        'test_output_sample': stdout[-2000:] if stdout else "No output"
    }

def analyze_dependencies():
    """Analyze project dependencies"""
    print("📦 Analyzing dependencies...")
    
    deps = {
        'requirements': [],
        'requirements_test': [],
        'pyproject': None
    }
    
    # Check requirements.txt
    if os.path.exists('requirements.txt'):
        with open('requirements.txt') as f:
            deps['requirements'] = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    
    # Check requirements-test.txt
    if os.path.exists('requirements-test.txt'):
        with open('requirements-test.txt') as f:
            deps['requirements_test'] = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    
    # Check pyproject.toml
    if os.path.exists('pyproject.toml'):
        with open('pyproject.toml') as f:
            deps['pyproject'] = f.read()[:500]  # First 500 chars
    
    return deps

def search_for_patterns():
    """Search for key patterns in code"""
    print("🔍 Searching for key patterns...")
    
    patterns = {}
    
    # Search for mechanism implementations
    stdout, _, _ = run_command("grep -r 'def.*mechanism' *.py 2>/dev/null | head -20")
    patterns['mechanism_functions'] = stdout.strip().split('\n') if stdout.strip() else []
    
    # Search for LLM calls
    stdout, _, _ = run_command("grep -r 'llm_client\\|LLMClient' *.py 2>/dev/null | wc -l")
    patterns['llm_references'] = int(stdout.strip()) if stdout.strip() else 0
    
    # Search for orchestrator usage
    stdout, _, _ = run_command("grep -r 'OrchestratorAgent\\|orchestrate' *.py 2>/dev/null | wc -l")
    patterns['orchestrator_references'] = int(stdout.strip()) if stdout.strip() else 0
    
    # Search for validation
    stdout, _, _ = run_command("grep -r '@Validator\\|validate_' *.py 2>/dev/null | wc -l")
    patterns['validator_references'] = int(stdout.strip()) if stdout.strip() else 0
    
    # Search for TODOs and FIXMEs
    stdout, _, _ = run_command("grep -r 'TODO\\|FIXME\\|XXX' *.py 2>/dev/null | head -20")
    patterns['todos'] = stdout.strip().split('\n') if stdout.strip() else []
    
    return patterns

def analyze_git():
    """Analyze git history"""
    print("📊 Analyzing git history...")
    
    git_info = {}
    
    # Recent commits
    stdout, _, _ = run_command("git log --oneline -10 2>/dev/null")
    git_info['recent_commits'] = stdout.strip().split('\n') if stdout.strip() else []
    
    # Branch info
    stdout, _, _ = run_command("git branch --show-current 2>/dev/null")
    git_info['current_branch'] = stdout.strip()
    
    # Status
    stdout, _, _ = run_command("git status --short 2>/dev/null")
    git_info['status'] = stdout.strip().split('\n') if stdout.strip() else []
    
    return git_info

def analyze_config():
    """Analyze configuration files"""
    print("⚙️  Analyzing configuration...")
    
    config = {}
    
    # Check for config files
    config_files = [
        'conf/config.yaml',
        'pytest.ini',
        'conftest.py',
        '.env.example'
    ]
    
    for cf in config_files:
        if os.path.exists(cf):
            config[cf] = "EXISTS"
        else:
            config[cf] = "MISSING"
    
    # Check pytest.ini markers
    if os.path.exists('pytest.ini'):
        with open('pytest.ini') as f:
            content = f.read()
            config['pytest_markers'] = [
                line.strip() for line in content.split('\n') 
                if line.strip().startswith('unit') or 
                   line.strip().startswith('integration') or
                   line.strip().startswith('system') or
                   line.strip().startswith('e2e')
            ]
    
    return config

def check_mechanisms():
    """Check which of the 17 mechanisms are mentioned in code"""
    print("🔧 Checking mechanism implementations...")
    
    mechanisms = {
        'M1_heterogeneous_fidelity': 0,
        'M2_progressive_training': 0,
        'M3_exposure_events': 0,
        'M4_physics_validation': 0,
        'M5_query_resolution': 0,
        'M6_ttm_tensor': 0,
        'M7_causal_chains': 0,
        'M8_embodied_states': 0,
        'M9_on_demand_generation': 0,
        'M10_scene_entities': 0,
        'M11_dialog_synthesis': 0,
        'M12_counterfactual': 0,
        'M13_multi_entity': 0,
        'M14_circadian': 0,
        'M15_prospection': 0,
        'M16_animistic': 0,
        'M17_modal_causality': 0
    }
    
    # Search patterns for each mechanism
    searches = {
        'M1_heterogeneous_fidelity': 'ResolutionLevel\\|resolution_level',
        'M3_exposure_events': 'ExposureEvent\\|exposure_event',
        'M6_ttm_tensor': 'TTMTensor\\|PhysicalTensor\\|CognitiveTensor',
        'M7_causal_chains': 'causal_parent\\|temporal_chain',
        'M12_counterfactual': 'counterfactual\\|branch_timeline',
        'M14_circadian': 'circadian\\|CircadianContext',
        'M15_prospection': 'prospection\\|ProspectiveState',
        'M16_animistic': 'animistic\\|AnimisticEntity',
        'M17_modal_causality': 'TemporalMode\\|modal.*causal'
    }
    
    for mechanism, pattern in searches.items():
        stdout, _, _ = run_command(f"grep -ri '{pattern}' *.py 2>/dev/null | wc -l")
        count = int(stdout.strip()) if stdout.strip() else 0
        mechanisms[mechanism] = count
    
    return mechanisms

def generate_report():
    """Generate comprehensive REPORT.md"""
    print("\n🚀 Starting Timepoint-Daedalus Analysis")
    print("=" * 60)
    
    report = {
        'timestamp': datetime.now().isoformat(),
        'file_structure': analyze_file_structure(),
        'tests': analyze_tests(),
        'dependencies': analyze_dependencies(),
        'patterns': search_for_patterns(),
        'git': analyze_git(),
        'config': analyze_config(),
        'mechanisms': check_mechanisms()
    }
    
    # Write JSON for debugging
    with open('analysis_data.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    # Generate markdown report
    md = []
    md.append("# Timepoint-Daedalus Ground Truth Analysis")
    md.append(f"\n**Generated:** {report['timestamp']}")
    md.append(f"\n**Analysis Tool:** analyze_timepoint.py\n")
    
    md.append("\n## Executive Summary\n")
    fs = report['file_structure']
    tests = report['tests']
    
    md.append(f"- **Python Files:** {fs['py_files']} ({fs['total_lines']:,} total lines)")
    md.append(f"- **Test Files:** {fs['test_files']}")
    md.append(f"- **Documentation Files:** {fs['md_files']}")
    md.append(f"- **Tests Collected:** {tests['total_collected']}")
    
    if tests['passed'] or tests['failed']:
        total_run = tests['passed'] + tests['failed']
        pass_rate = (tests['passed'] / total_run * 100) if total_run > 0 else 0
        md.append(f"- **Test Status:** {tests['passed']}/{total_run} passing ({pass_rate:.1f}%)")
    else:
        md.append(f"- **Test Status:** Unable to run tests (check environment)")
    
    md.append("\n---\n")
    
    # File Structure
    md.append("\n## 📁 File Structure\n")
    md.append(f"\n### Python Files ({fs['py_files']} files, {fs['total_lines']:,} lines)\n")
    md.append("\n**Largest Files:**\n")
    for fname, lines in fs['largest_files']:
        md.append(f"- `{fname}`: {lines:,} lines")
    
    md.append("\n\n**All Python Files:**\n")
    for fname in sorted(fs['all_py_files']):
        md.append(f"- {fname}")
    
    md.append("\n\n**Test Files:**\n")
    for fname in sorted(fs['all_test_files']):
        md.append(f"- {fname}")
    
    md.append("\n\n**Documentation:**\n")
    for fname in sorted(fs['all_md_files']):
        md.append(f"- {fname}")
    
    # Test Results
    md.append("\n\n## 🧪 Test Suite Analysis\n")
    md.append(f"\n**Collection:** {tests['total_collected']} tests found\n")
    
    if tests['passed'] or tests['failed']:
        md.append(f"\n**Results:**")
        md.append(f"- ✅ Passed: {tests['passed']}")
        md.append(f"- ❌ Failed: {tests['failed']}")
        md.append(f"- ⏭️  Skipped: {tests['skipped']}")
        md.append(f"- 🔥 Errors: {tests['errors']}")
    
    md.append("\n\n**Tests by File:**\n")
    for fname, count in sorted(tests['by_file'].items()):
        md.append(f"- `{fname}`: {count} tests")
    
    if tests['markers']:
        md.append("\n\n**Available Test Markers:**\n")
        for marker in tests['markers']:
            md.append(f"- @pytest.mark.{marker}")
    
    md.append("\n\n**Sample Test Output (last 1000 chars):**\n```")
    md.append(tests['test_output_sample'][-1000:])
    md.append("```\n")
    
    # Dependencies
    md.append("\n## 📦 Dependencies\n")
    deps = report['dependencies']
    
    if deps['requirements']:
        md.append(f"\n**requirements.txt ({len(deps['requirements'])} packages):**\n")
        for dep in deps['requirements'][:20]:
            md.append(f"- {dep}")
        if len(deps['requirements']) > 20:
            md.append(f"- ... and {len(deps['requirements']) - 20} more")
    
    if deps['requirements_test']:
        md.append(f"\n\n**requirements-test.txt ({len(deps['requirements_test'])} packages):**\n")
        for dep in deps['requirements_test']:
            md.append(f"- {dep}")
    
    # Code Patterns
    md.append("\n## 🔍 Code Pattern Analysis\n")
    patterns = report['patterns']
    
    md.append(f"\n- **LLM References:** {patterns['llm_references']} occurrences")
    md.append(f"- **Orchestrator References:** {patterns['orchestrator_references']} occurrences")
    md.append(f"- **Validator References:** {patterns['validator_references']} occurrences")
    
    if patterns['mechanism_functions']:
        md.append("\n\n**Mechanism Functions Found:**\n")
        for func in patterns['mechanism_functions'][:15]:
            md.append(f"- {func.strip()}")
    
    if patterns['todos']:
        md.append("\n\n**TODOs/FIXMEs Found:**\n")
        for todo in patterns['todos'][:15]:
            md.append(f"- {todo.strip()}")
    
    # Mechanism Implementation
    md.append("\n## 🔧 Mechanism Implementation Status\n")
    md.append("\n(Based on code references, not functionality verification)\n")
    
    mechs = report['mechanisms']
    for mech, count in sorted(mechs.items()):
        status = "✅" if count > 0 else "❓"
        md.append(f"- {status} **{mech.replace('_', ' ').title()}:** {count} references")
    
    implemented = sum(1 for c in mechs.values() if c > 0)
    md.append(f"\n**Total: {implemented}/{len(mechs)} mechanisms have code references**")
    
    # Configuration
    md.append("\n## ⚙️ Configuration\n")
    cfg = report['config']
    
    md.append("\n**Configuration Files:**\n")
    for fname, status in cfg.items():
        if not fname.startswith('pytest'):
            emoji = "✅" if status == "EXISTS" else "❌"
            md.append(f"- {emoji} `{fname}`: {status}")
    
    if 'pytest_markers' in cfg:
        md.append("\n\n**Pytest Test Levels:**\n")
        for marker in cfg.get('pytest_markers', []):
            md.append(f"- {marker}")
    
    # Git Info
    md.append("\n## 📊 Git Information\n")
    git = report['git']
    
    if git.get('current_branch'):
        md.append(f"\n**Current Branch:** `{git['current_branch']}`")
    
    if git.get('recent_commits'):
        md.append("\n\n**Recent Commits:**\n")
        for commit in git['recent_commits'][:10]:
            md.append(f"- {commit}")
    
    if git.get('status'):
        md.append("\n\n**Working Directory Status:**\n")
        for status in git['status'][:15]:
            md.append(f"- {status}")
    
    # Outstanding Work
    md.append("\n## 🎯 Recommendations\n")
    md.append("\n### Documentation Cleanup\n")
    md.append("- Keep: README.md, MECHANICS.md")
    md.append("- Create: PLAN.md (from CHANGE-ROUND.md outstanding items)")
    md.append("- Consider removing: Outdated analysis docs")
    
    md.append("\n### Testing Priority\n")
    if tests['failed'] > 0:
        md.append(f"- Fix {tests['failed']} failing tests")
    md.append("- Verify test markers are properly applied")
    md.append("- Add missing test coverage")
    
    md.append("\n### Code Quality\n")
    if patterns['todos']:
        md.append(f"- Address {len(patterns['todos'])} TODO/FIXME items")
    md.append("- Review mechanism implementations for completeness")
    
    md.append("\n---\n")
    md.append("\n*This report was generated automatically. Review analysis_data.json for raw data.*\n")
    
    # Write report
    report_content = '\n'.join(md)
    with open('REPORT.md', 'w') as f:
        f.write(report_content)
    
    print("\n" + "=" * 60)
    print("✅ Analysis complete!")
    print(f"📄 Generated: REPORT.md")
    print(f"📄 Raw data: analysis_data.json")
    print("=" * 60)
    
    return report_content

if __name__ == "__main__":
    try:
        report = generate_report()
        print("\n✨ Next steps:")
        print("1. Review REPORT.md")
        print("2. Share REPORT.md with Claude for accurate documentation")
        print("3. Claude will generate: README.md, MECHANICS.md, PLAN.md")
    except Exception as e:
        print(f"\n❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()
