#!/bin/bash
# clean-and-find-orphans.sh
# Automated orphan file detection for timepoint-daedalus
# Finds Python files not imported anywhere, unused test files, and outdated utilities

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Output file
REPORT_FILE="orphan_candidates_report.txt"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔍 Timepoint-Daedalus Orphan File Detector"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Initialize report
echo "# Orphan File Candidates Report" > "$REPORT_FILE"
echo "Generated: $(date)" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# ===================================================================
# Section 1: Find Python files not imported anywhere
# ===================================================================
echo -e "${BLUE}[1/5] Analyzing Python import graph...${NC}"
echo ""
echo "## Section 1: Unused Python Modules (Not Imported)" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

UNUSED_COUNT=0

# Get all Python files (exclude venv, __pycache__, archive)
PYTHON_FILES=$(find . -name "*.py" \
    -not -path "./venv/*" \
    -not -path "./__pycache__/*" \
    -not -path "./archive/*" \
    -not -path "*/venv/*" \
    -not -path "*/__pycache__/*" \
    -type f)

for file in $PYTHON_FILES; do
    # Extract module name (remove ./ and .py)
    module_name=$(basename "$file" .py)

    # Skip __init__ files
    if [[ "$module_name" == "__init__" ]]; then
        continue
    fi

    # Search for imports of this module
    import_count=$(grep -r "from.*${module_name}.*import\|import.*${module_name}" . \
        --exclude-dir=venv \
        --exclude-dir=__pycache__ \
        --exclude-dir=archive \
        --include="*.py" \
        --exclude="$file" \
        2>/dev/null | wc -l | tr -d ' ')

    if [[ "$import_count" -eq 0 ]]; then
        # Get file age
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            file_age=$(stat -f "%Sm" -t "%Y-%m-%d" "$file")
        else
            # Linux
            file_age=$(stat -c "%y" "$file" | cut -d' ' -f1)
        fi

        # Get file size
        file_size=$(du -h "$file" | cut -f1)

        echo "  ⚠️  $file" >> "$REPORT_FILE"
        echo "      Last modified: $file_age | Size: $file_size" >> "$REPORT_FILE"
        echo "      Not imported by any other file" >> "$REPORT_FILE"
        echo "" >> "$REPORT_FILE"

        echo -e "  ${YELLOW}⚠️  $file${NC} (not imported, $file_size)"
        UNUSED_COUNT=$((UNUSED_COUNT + 1))
    fi
done

echo ""
echo -e "${GREEN}Found $UNUSED_COUNT potentially unused modules${NC}"
echo ""

# ===================================================================
# Section 2: Find test files not run by test runners
# ===================================================================
echo -e "${BLUE}[2/5] Analyzing test file usage...${NC}"
echo ""
echo "## Section 2: Test Files Not Run by Test Runners" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

UNRUN_TEST_COUNT=0

# Find test runner files
TEST_RUNNERS="run_all_mechanism_tests.py test_rig.py conftest.py"

# Get all test files
TEST_FILES=$(find . -maxdepth 1 -name "test_*.py" -type f)

for test_file in $TEST_FILES; do
    test_basename=$(basename "$test_file")

    # Check if mentioned in any test runner
    mentioned=false
    for runner in $TEST_RUNNERS; do
        if [[ -f "$runner" ]]; then
            if grep -q "$test_basename" "$runner" 2>/dev/null; then
                mentioned=true
                break
            fi
        fi
    done

    # Check if pytest.mark exists (active test)
    has_pytest_marks=$(grep -c "@pytest.mark" "$test_file" 2>/dev/null || echo "0")

    if [[ "$mentioned" == false && "$has_pytest_marks" -eq 0 ]]; then
        # Get file age
        if [[ "$OSTYPE" == "darwin"* ]]; then
            file_age=$(stat -f "%Sm" -t "%Y-%m-%d" "$test_file")
        else
            file_age=$(stat -c "%y" "$test_file" | cut -d' ' -f1)
        fi

        file_size=$(du -h "$test_file" | cut -f1)

        echo "  ⚠️  $test_file" >> "$REPORT_FILE"
        echo "      Last modified: $file_age | Size: $file_size" >> "$REPORT_FILE"
        echo "      Not referenced in test runners, no pytest marks" >> "$REPORT_FILE"
        echo "" >> "$REPORT_FILE"

        echo -e "  ${YELLOW}⚠️  $test_file${NC} (not in test runners, $file_size)"
        UNRUN_TEST_COUNT=$((UNRUN_TEST_COUNT + 1))
    fi
done

echo ""
echo -e "${GREEN}Found $UNRUN_TEST_COUNT potentially unused test files${NC}"
echo ""

# ===================================================================
# Section 3: Find old files (>30 days without modification)
# ===================================================================
echo -e "${BLUE}[3/5] Finding old files (>30 days)...${NC}"
echo ""
echo "## Section 3: Old Files (>30 Days Since Modification)" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

OLD_FILE_COUNT=0

# Find files older than 30 days
OLD_FILES=$(find . -maxdepth 1 -name "*.py" -type f -mtime +30 \
    -not -name "orchestrator.py" \
    -not -name "workflows.py" \
    -not -name "llm*.py" \
    -not -name "storage.py" \
    -not -name "schemas.py" \
    -not -name "validation.py" \
    -not -name "tensors.py" \
    -not -name "query_interface.py" \
    2>/dev/null)

for file in $OLD_FILES; do
    # Get file age
    if [[ "$OSTYPE" == "darwin"* ]]; then
        file_age=$(stat -f "%Sm" -t "%Y-%m-%d" "$file")
        days_old=$(( ($(date +%s) - $(stat -f "%m" "$file")) / 86400 ))
    else
        file_age=$(stat -c "%y" "$file" | cut -d' ' -f1)
        days_old=$(( ($(date +%s) - $(stat -c "%Y" "$file")) / 86400 ))
    fi

    file_size=$(du -h "$file" | cut -f1)

    echo "  📅 $file" >> "$REPORT_FILE"
    echo "      Last modified: $file_age ($days_old days ago) | Size: $file_size" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"

    echo -e "  ${YELLOW}📅 $file${NC} ($days_old days old, $file_size)"
    OLD_FILE_COUNT=$((OLD_FILE_COUNT + 1))
done

echo ""
echo -e "${GREEN}Found $OLD_FILE_COUNT files >30 days old${NC}"
echo ""

# ===================================================================
# Section 4: Find duplicate/similar files
# ===================================================================
echo -e "${BLUE}[4/5] Finding potential duplicate files...${NC}"
echo ""
echo "## Section 4: Potential Duplicate Files" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

DUPLICATE_COUNT=0

# Check for common duplicate patterns
DUPLICATE_PATTERNS=(
    "test_e2e_*"
    "demo_*"
    "*_old.py"
    "*_backup.py"
    "*_v2.py"
    "run_*_finetune.py"
)

for pattern in "${DUPLICATE_PATTERNS[@]}"; do
    matches=$(find . -maxdepth 1 -name "$pattern" -type f 2>/dev/null | wc -l | tr -d ' ')

    if [[ "$matches" -gt 1 ]]; then
        echo "  Pattern: $pattern (found $matches files)" >> "$REPORT_FILE"
        find . -maxdepth 1 -name "$pattern" -type f 2>/dev/null | while read file; do
            if [[ "$OSTYPE" == "darwin"* ]]; then
                file_age=$(stat -f "%Sm" -t "%Y-%m-%d" "$file")
            else
                file_age=$(stat -c "%y" "$file" | cut -d' ' -f1)
            fi
            file_size=$(du -h "$file" | cut -f1)

            echo "    - $file ($file_age, $file_size)" >> "$REPORT_FILE"
        done
        echo "" >> "$REPORT_FILE"

        echo -e "  ${YELLOW}🔄 Found $matches files matching '$pattern'${NC}"
        DUPLICATE_COUNT=$((DUPLICATE_COUNT + matches))
    fi
done

echo ""
echo -e "${GREEN}Found $DUPLICATE_COUNT potential duplicate files${NC}"
echo ""

# ===================================================================
# Section 5: Check for orphaned directories
# ===================================================================
echo -e "${BLUE}[5/5] Finding empty or orphaned directories...${NC}"
echo ""
echo "## Section 5: Empty/Orphaned Directories" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

EMPTY_DIR_COUNT=0

# Find empty directories (exclude venv, .git, __pycache__)
EMPTY_DIRS=$(find . -type d -empty \
    -not -path "./venv/*" \
    -not -path "./.git/*" \
    -not -path "./__pycache__/*" \
    -not -path "./archive/*" \
    2>/dev/null)

for dir in $EMPTY_DIRS; do
    echo "  📁 $dir" >> "$REPORT_FILE"
    echo "      Empty directory (no files)" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"

    echo -e "  ${YELLOW}📁 $dir${NC} (empty)"
    EMPTY_DIR_COUNT=$((EMPTY_DIR_COUNT + 1))
done

echo ""
echo -e "${GREEN}Found $EMPTY_DIR_COUNT empty directories${NC}"
echo ""

# ===================================================================
# Summary
# ===================================================================
echo "" >> "$REPORT_FILE"
echo "## Summary" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "- Unused Python modules: $UNUSED_COUNT" >> "$REPORT_FILE"
echo "- Unused test files: $UNRUN_TEST_COUNT" >> "$REPORT_FILE"
echo "- Old files (>30 days): $OLD_FILE_COUNT" >> "$REPORT_FILE"
echo "- Potential duplicates: $DUPLICATE_COUNT" >> "$REPORT_FILE"
echo "- Empty directories: $EMPTY_DIR_COUNT" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
TOTAL_CANDIDATES=$((UNUSED_COUNT + UNRUN_TEST_COUNT + OLD_FILE_COUNT + DUPLICATE_COUNT + EMPTY_DIR_COUNT))
echo "**Total orphan candidates: $TOTAL_CANDIDATES**" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "## Recommendations" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "1. Review unused Python modules - consider moving to archive/utils/" >> "$REPORT_FILE"
echo "2. Review unused test files - move to archive/tests/ if superseded" >> "$REPORT_FILE"
echo "3. Review old files - archive if no longer actively maintained" >> "$REPORT_FILE"
echo "4. Consolidate duplicate files - keep most recent, archive others" >> "$REPORT_FILE"
echo "5. Remove empty directories - use 'rmdir' for confirmed empty dirs" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "---" >> "$REPORT_FILE"
echo "Generated by clean-and-find-orphans.sh" >> "$REPORT_FILE"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✅ Analysis Complete${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 Summary:"
echo -e "  - Unused Python modules: ${YELLOW}$UNUSED_COUNT${NC}"
echo -e "  - Unused test files: ${YELLOW}$UNRUN_TEST_COUNT${NC}"
echo -e "  - Old files (>30 days): ${YELLOW}$OLD_FILE_COUNT${NC}"
echo -e "  - Potential duplicates: ${YELLOW}$DUPLICATE_COUNT${NC}"
echo -e "  - Empty directories: ${YELLOW}$EMPTY_DIR_COUNT${NC}"
echo ""
echo -e "  ${GREEN}Total orphan candidates: $TOTAL_CANDIDATES${NC}"
echo ""
echo -e "📄 Detailed report written to: ${BLUE}$REPORT_FILE${NC}"
echo ""
echo "Next steps:"
echo "  1. Review $REPORT_FILE"
echo "  2. Move candidates to archive/ directory"
echo "  3. Test system still works after archiving"
echo "  4. Commit changes"
echo ""
