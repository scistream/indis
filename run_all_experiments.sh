#!/bin/bash

# Run all experiment CSV files through automation framework
set -e

# Setup
EXP_DIR="exp"
RESULTS_DIR="experiment_results"
LOGS_DIR="logs"
mkdir -p "$RESULTS_DIR" "$LOGS_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

# Get all CSV files
csv_files=($(ls ${EXP_DIR}/*.csv 2>/dev/null || true))
if [ ${#csv_files[@]} -eq 0 ]; then
    echo -e "${RED}❌ No CSV files found in ${EXP_DIR}/${NC}"
    exit 1
fi

echo -e "${BLUE}🚀 Running ${#csv_files[@]} experiments${NC}"

# Process each file
success=0
failed=0
for csv_file in "${csv_files[@]}"; do
    # Extract experiment name
    exp_name=$(basename "$csv_file" .csv)
    result_file="${RESULTS_DIR}/${exp_name}_results.csv"
    log_file="${LOGS_DIR}/${exp_name}.log"
    
    echo -e "${BLUE}[$((success + failed + 1))/${#csv_files[@]}] ${exp_name}${NC}"
    
    # Run experiment
    cd src
    if python3 experiment_automation.py "../${csv_file}" --log-file "../${log_file}" >> "../${log_file}" 2>&1; then
        # Move default result file to named result file
        if [ -f "experiment_results_local.csv" ]; then
            mv "experiment_results_local.csv" "../${result_file}"
            echo -e "${GREEN}✅ Success → ${result_file}${NC}"
            success=$((success + 1))
        else
            echo -e "${RED}❌ No results generated${NC}"
            failed=$((failed + 1))
        fi
    else
        echo -e "${RED}❌ Failed - check ${log_file}${NC}"
        failed=$((failed + 1))
    fi
    cd ..
    
    # Brief pause between experiments
    [ $((success + failed)) -lt ${#csv_files[@]} ] && sleep 3
done

# Summary
echo -e "\n${BLUE}📊 Complete: ${GREEN}${success} success${NC}, ${RED}${failed} failed${NC}"

# Create summary file
cat > "${RESULTS_DIR}/summary.txt" << EOF
Batch Execution Summary - $(date)
Total: ${#csv_files[@]} experiments
Success: ${success}
Failed: ${failed}

Results saved in: ${RESULTS_DIR}/
Logs saved in: ${LOGS_DIR}/
EOF

echo -e "${BLUE}📋 Summary: ${RESULTS_DIR}/summary.txt${NC}"
[ $failed -eq 0 ] && exit 0 || exit 1