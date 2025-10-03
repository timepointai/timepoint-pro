#!/usr/bin/env python3
"""
add_test_markers.py - Automatically add pytest markers to test files

Analyzes test files and adds appropriate markers based on:
- File naming patterns
- Import statements
- Test characteristics
- Execution patterns
"""
import ast
import re
from pathlib import Path
from typing import List, Set, Tuple


class TestMarkerAnalyzer(ast.NodeVisitor):
    """Analyze test files to determine appropriate markers"""

    def __init__(self):
        self.imports = set()
        self.test_functions = []
        self.has_fixtures = False
        self.fixture_count = 0

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.add(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            self.imports.add(node.module)
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        # Check if it's a test function
        if node.name.startswith('test_'):
            self.test_functions.append(node.name)

        # Check if it's a fixture
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Attribute):
                if decorator.attr == 'fixture':
                    self.has_fixtures = True
                    self.fixture_count += 1
            elif isinstance(decorator, ast.Name):
                if decorator.id == 'fixture':
                    self.has_fixtures = True
                    self.fixture_count += 1

        self.generic_visit(node)


def analyze_test_file(file_path: Path) -> Set[str]:
    """Analyze a test file and return recommended markers"""
    markers = set()

    with open(file_path, 'r') as f:
        content = f.read()

    try:
        tree = ast.parse(content)
        analyzer = TestMarkerAnalyzer()
        analyzer.visit(tree)

        # Determine test level based on various factors
        # Unit tests: Simple, isolated, few dependencies
        if (len(analyzer.imports) < 5 and
            analyzer.fixture_count <= 1 and
            'llm' not in str(analyzer.imports).lower()):
            markers.add('unit')

        # Integration tests: Multiple components, multiple fixtures
        if analyzer.fixture_count >= 2 or len(analyzer.imports) >= 5:
            markers.add('integration')

        # System tests: Full stack testing
        if ('workflows' in analyzer.imports or
            'ai_entity_service' in analyzer.imports or
            'storage' in analyzer.imports):
            markers.add('system')

        # E2E tests: Named explicitly or comprehensive
        if 'e2e' in file_path.stem or 'autopilot' in file_path.stem:
            markers.add('e2e')

        # Feature-specific markers
        if 'llm' in analyzer.imports or 'llm_v2' in analyzer.imports:
            markers.add('llm')
            markers.add('slow')

        if 'animistic' in file_path.stem or 'animism' in content.lower():
            markers.add('animism')

        if 'temporal' in file_path.stem or 'temporal' in content.lower():
            markers.add('temporal')

        if 'ai_entity' in file_path.stem:
            markers.add('ai_entity')

        # Slow tests: Time-consuming operations
        if (re.search(r'time\.sleep', content) or
            re.search(r'for .* in range\([2-9]\d+', content) or
            'llm' in markers):
            markers.add('slow')

        # Performance tests
        if 'performance' in file_path.stem or 'benchmark' in content.lower():
            markers.add('performance')

        # Validation tests
        if 'validation' in file_path.stem or 'validator' in analyzer.imports:
            markers.add('validation')

    except SyntaxError:
        print(f"  ⚠️  Syntax error in {file_path}, skipping")

    return markers


def get_existing_markers(file_path: Path) -> Set[str]:
    """Extract existing markers from file"""
    markers = set()

    with open(file_path, 'r') as f:
        content = f.read()

    # Find all @pytest.mark.* decorators
    pattern = r'@pytest\.mark\.(\w+)'
    for match in re.finditer(pattern, content):
        markers.add(match.group(1))

    return markers


def add_markers_to_file(file_path: Path, markers: Set[str], dry_run: bool = False):
    """Add marker decorators to test file"""
    if not markers:
        return

    with open(file_path, 'r') as f:
        lines = f.readlines()

    # Find where to insert markers (after imports, before first test class/function)
    insert_line = 0
    for i, line in enumerate(lines):
        if line.startswith('import ') or line.startswith('from '):
            insert_line = i + 1
        elif line.strip().startswith('class Test') or line.strip().startswith('def test_'):
            break

    # Check if pytest is imported
    has_pytest_import = any('import pytest' in line for line in lines[:insert_line])

    if not has_pytest_import:
        lines.insert(insert_line, 'import pytest\n')
        insert_line += 1

    # Build marker comment
    marker_comment = f"\n# Test markers: {', '.join(sorted(markers))}\n"
    marker_decorators = ''.join(f"@pytest.mark.{marker}\n" for marker in sorted(markers))

    if dry_run:
        print(f"\n{file_path.name}:")
        print(f"  Would add: {', '.join(sorted(markers))}")
        return

    # Find and update class decorators
    updated = False
    new_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # If we find a test class without markers
        if line.strip().startswith('class Test'):
            # Check if previous line has markers
            if i > 0 and '@pytest.mark' in lines[i-1]:
                new_lines.append(line)
            else:
                # Add markers before class
                for marker in sorted(markers):
                    new_lines.append(f"@pytest.mark.{marker}\n")
                new_lines.append(line)
                updated = True
        else:
            new_lines.append(line)

        i += 1

    if updated:
        with open(file_path, 'w') as f:
            f.writelines(new_lines)
        print(f"  ✓ Added markers to {file_path.name}: {', '.join(sorted(markers))}")
    else:
        print(f"  ⚠️  No test classes found in {file_path.name}")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Add pytest markers to test files")
    parser.add_argument('--dry-run', action='store_true', help="Show what would be done")
    parser.add_argument('--force', action='store_true', help="Override existing markers")
    parser.add_argument('files', nargs='*', help="Specific files to process")

    args = parser.parse_args()

    # Get test files
    if args.files:
        test_files = [Path(f) for f in args.files]
    else:
        test_files = list(Path('.').glob('test_*.py'))
        # Exclude special files
        test_files = [f for f in test_files if f.name not in [
            'test_validation_system.py',
            'test_e2e_autopilot.py'  # Already has markers
        ]]

    print(f"Analyzing {len(test_files)} test files...\n")

    for file_path in sorted(test_files):
        existing_markers = get_existing_markers(file_path)
        recommended_markers = analyze_test_file(file_path)

        if existing_markers and not args.force:
            print(f"{file_path.name}: Already has markers: {', '.join(sorted(existing_markers))}")
            continue

        # Add new markers (merge with existing if force=True)
        if args.force:
            final_markers = recommended_markers | existing_markers
        else:
            final_markers = recommended_markers

        add_markers_to_file(file_path, final_markers, dry_run=args.dry_run)

    if args.dry_run:
        print("\n💡 Run without --dry-run to apply changes")


if __name__ == '__main__':
    main()
