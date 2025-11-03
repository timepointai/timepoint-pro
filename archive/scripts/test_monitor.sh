#!/bin/bash
# Simple test script to validate the monitor

echo "Running: test_template [1/3]"
sleep 1
echo "Run ID: run_20251101_120000_test123"
sleep 1
echo "Entities: 5, Timepoints: 10"
sleep 1
echo "Mechanisms: M1, M2, M7, M13"
sleep 1
echo "Cost: $0.05"
sleep 1
echo "✅ Success: test_template"
sleep 1

echo ""
echo "Running: test_template_2 [2/3]"
sleep 1
echo "Run ID: run_20251101_120010_test456"
sleep 1
echo "Entities: 3, Timepoints: 5"
sleep 1
echo "Mechanisms: M3, M8, M11"
sleep 1
echo "Cost: $0.03"
sleep 1
echo "✅ Success: test_template_2"

echo ""
echo "All tests complete!"
