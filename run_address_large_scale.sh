#!/bin/bash
# Run ADDRESS on all large-scale maps with 3500 agents, 500s time budget
# Collects SOC (solution cost) and AUC for Table 4 comparison

ADDRESS="./ADDRESS-main/address"
MAPS_DIR="./maps/large"
RESULTS_FILE="address_large_scale_results.csv"
NUM_AGENTS=3500
TIME_BUDGET=500

echo "map,agents,soc,auc,runtime_s,solved" > "$RESULTS_FILE"

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

    OUT_PREFIX="/tmp/address_${MAP_NAME}"

    echo "Running ADDRESS on ${MAP_NAME} with k=${NUM_AGENTS}, t=${TIME_BUDGET}s ..."

    $ADDRESS \
        -m "$MAP_FILE" \
        -a "$SCEN_FILE" \
        -k "$NUM_AGENTS" \
        -t "$TIME_BUDGET" \
        -o "$OUT_PREFIX" \
        --seed=0 \
        --screen=1 \
        --maxIterations=1000000 \
        --destroyStrategy=RandomWalk \
        --algorithm=bernoulie \
        --k=64 2>&1

    # Extract from ADDRESS CSV output (format: runtime,solution cost,...,area under curve,...,success,...)
    CSV_FILE="${OUT_PREFIX}-LNS.csv"
    if [[ -f "$CSV_FILE" ]]; then
        # Get last data row (final result)
        LAST=$(tail -1 "$CSV_FILE")
        SOC=$(echo "$LAST"     | cut -d',' -f2)
        AUC=$(echo "$LAST"     | cut -d',' -f10)
        RUNTIME=$(echo "$LAST" | cut -d',' -f1)
        SOLVED=$(echo "$LAST"  | cut -d',' -f18)
    else
        SOC="N/A"; AUC="N/A"; RUNTIME="N/A"; SOLVED="0"
    fi

    echo "${MAP_NAME},${NUM_AGENTS},${SOC},${AUC},${RUNTIME},${SOLVED}" | tee -a "$RESULTS_FILE"
    echo "  -> SOC=${SOC}, AUC=${AUC}, runtime=${RUNTIME}s, solved=${SOLVED}"
    echo ""
done

echo "Done. Results saved to $RESULTS_FILE"
echo ""
cat "$RESULTS_FILE"
