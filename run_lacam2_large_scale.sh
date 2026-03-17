#!/bin/bash
# Run LaCAM* on all large-scale maps with 3500 agents, 500s time budget
# Collects SOC (Sum of Costs), AUC, and runtime for Table 4 comparison

LACAM2="./lacam2-dev/build/main"
MAPS_DIR="./maps/large"
RESULTS_FILE="lacam2_large_scale_results.csv"
AUC_SCRIPT="./compute_lacam2_auc.py"
NUM_AGENTS=3500
TIME_BUDGET=500

echo "map,agents,soc,auc,comp_time_ms,solved" > "$RESULTS_FILE"

declare -A MAP_SCEN
MAP_SCEN["Boston_0_1024"]="Boston_0_1024.map.scen"
MAP_SCEN["Moscow_0_1024"]="Moscow_0_1024.map.scen"
MAP_SCEN["NewYork_0_1024"]="NewYork_0_1024.map.scen"
MAP_SCEN["Paris_0_1024"]="Paris_0_1024.map.scen"
MAP_SCEN["Shanghai_0_1024"]="Shanghai_0_1024.map.scen"
MAP_SCEN["Sydney_0_1024"]="Sydney_0_1024.map.scen"
MAP_SCEN["warehouse-20-40-10-2-2"]="warehouse-20-40-10-2-2-10000agents-1.scen"

for MAP_NAME in "${!MAP_SCEN[@]}"; do
    SCEN="${MAP_SCEN[$MAP_NAME]}"
    MAP_FILE="${MAPS_DIR}/${MAP_NAME}.map"
    SCEN_FILE="${MAPS_DIR}/${SCEN}"

    # Warehouse scen is in a different folder
    if [[ "$MAP_NAME" == "warehouse"* ]]; then
        SCEN_FILE="./maps/scen-warehouse/${SCEN}"
    fi

    OUT_FILE="/tmp/lacam2_${MAP_NAME}.txt"
    LOG_FILE="/tmp/lacam2_${MAP_NAME}.log"

    echo "Running LaCAM* on ${MAP_NAME} with k=${NUM_AGENTS}, t=${TIME_BUDGET}s ..."

    # Run with verbose=1 to capture intermediate costs for AUC, redirect to log
    $LACAM2 \
        -m "$MAP_FILE" \
        -i "$SCEN_FILE" \
        -N "$NUM_AGENTS" \
        -t "$TIME_BUDGET" \
        -o "$OUT_FILE" \
        --log_short \
        --objective 2 \
        -v 1 \
        -s 0 2>&1 | tee "$LOG_FILE"

    # Extract final results from output file
    SOC=$(grep "^soc=" "$OUT_FILE" | cut -d'=' -f2)
    COMP_TIME=$(grep "^comp_time=" "$OUT_FILE" | cut -d'=' -f2)
    SOLVED=$(grep "^solved=" "$OUT_FILE" | cut -d'=' -f2)

    # Compute AUC from verbose log
    AUC_RESULT=$(python3 "$AUC_SCRIPT" "$LOG_FILE" "$TIME_BUDGET")
    AUC=$(echo "$AUC_RESULT" | cut -d',' -f2)

    echo "${MAP_NAME},${NUM_AGENTS},${SOC},${AUC},${COMP_TIME},${SOLVED}" | tee -a "$RESULTS_FILE"
    echo "  -> SOC=${SOC}, AUC=${AUC}, time=${COMP_TIME}ms, solved=${SOLVED}"
    echo ""
done

echo "Done. Results saved to $RESULTS_FILE"
echo ""
cat "$RESULTS_FILE"
