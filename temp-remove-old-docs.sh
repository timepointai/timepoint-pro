#!/bin/bash
# Temporary script to remove outdated markdown documentation
# Keeps only: README.md, MECHANICS.md, PLAN.md

echo "=================================================="
echo "REMOVING OUTDATED MARKDOWN DOCUMENTATION"
echo "=================================================="
echo ""
echo "Keeping:"
echo "  - README.md"
echo "  - MECHANICS.md"
echo "  - PLAN.md"
echo ""
echo "Removing all other markdown files in project root..."
echo ""

# Array of files to remove (all markdown files except the three we're keeping)
FILES_TO_REMOVE=(
    "CHANGE-ROUND.md"
    "README 2.md"
    "MECHANICS 2.md"
    "LLM-INTEGRATION-PLAN.md"
    "LLM-SERVICE-MIGRATION.md"
    "LLM-SERVICE-SUMMARY.md"
    "LLM-SERVICE-QUICKSTART.md"
    "LLM-SERVICE-INTEGRATION-COMPLETE.md"
    "LLM-ENHANCEMENTS-COMPLETE.md"
    "LLM-FUNCTION-COVERAGE-TABLE.md"
    "IMPLEMENTATION-PROOF.md"
    "RUN-AUTOPILOT.md"
    "TESTING.md"
    "TESTING_MIGRATION.md"
    "README_TESTING.md"
    "CONSOLIDATION_COMPLETE.md"
    "SETUP_TESTING.md"
    "ERRORS_FIXED.md"
    "README_START_HERE.md"
    "INDEX.md"
    "QUICK_FIX.md"
    "APPLICATION_FIXES.md"
    "TEST_FIXES_COMPLETE.md"
    "FINAL_TEST_FIXES.md"
    "ALL_TESTS_FIXED.md"
    "TEST_ASSERTION_FIXES.md"
    "ORCHESTRATOR_DOCUMENTATION.md"
    "ORCHESTRATOR_REPORT.md"
    "CURRENT_STATE_ANALYSIS.md"
    "ORCHESTRATOR_INTEGRATION_COMPLETE.md"
    "temp-summaries.md"
    "HANDOFF.md"
)

# Remove each file
for file in "${FILES_TO_REMOVE[@]}"; do
    if [ -f "$file" ]; then
        echo "  Removing: $file"
        rm "$file"
    else
        echo "  Not found (skipping): $file"
    fi
done

echo ""
echo "=================================================="
echo "CLEANUP COMPLETE"
echo "=================================================="
echo ""
echo "Remaining markdown files:"
ls -lh *.md 2>/dev/null || echo "  (none found - this is expected)"
echo ""
