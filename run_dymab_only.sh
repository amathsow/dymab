#!/bin/bash
# Run only DyMAB-aUCB and DyMAB-eGreedy for all 7 maps at 500s (k=3500)
# with the improved Hotspots temperature T=500

DYMAB="./dymab"
MAPS_DIR="./maps/large"
OUT_FILE="dymab_500s_results.csv"
AGENTS=3500
TIME=500
SEED=0
ALPHA=10000
EPSILON=0.5
DECAY_WIN=100
LAMBDA=10
NEIGHBOR_SIZES=5

declare -A MAP_SCEN
MAP_SCEN["Boston_0_1024"]="Boston_0_1024.map.scen"
MAP_SCEN["Moscow_0_1024"]="Moscow_0_1024.map.scen"
MAP_SCEN["NewYork_0_1024"]="NewYork_0_1024.map.scen"
MAP_SCEN["Paris_0_1024"]="Paris_0_1024.map.scen"
MAP_SCEN["Shanghai_0_1024"]="Shanghai_0_1024.map.scen"
MAP_SCEN["Sydney_0_1024"]="Sydney_0_1024.map.scen"
MAP_SCEN["warehouse-20-40-10-2-2"]="warehouse-20-40-10-2-2-10000agents-1.scen"

echo "map,algorithm,soc,auc,solved" > "$OUT_FILE"

run_dymab() {
    local map=$1 scen=$2 algo_flag=$3 algo_name=$4
    local map_file="${MAPS_DIR}/${map}.map"
    local scen_file="${MAPS_DIR}/${scen}"
    [[ "$map" == "warehouse"* ]] && scen_file="./maps/scen-warehouse/${scen}"

    local out="/tmp/dymab_${map}_t${TIME}_${algo_name}"
    echo "  [${algo_name}] ${map} ..."

    $DYMAB -m "$map_file" -a "$scen_file" -o "$out" \
        -k "$AGENTS" -t "$TIME" \
        --outputPaths="${out}_paths.txt" \
        --banditAlgo="$algo_flag" \
        --destroyStrategy=Adaptive \
        --neighborCandidateSizes=$NEIGHBOR_SIZES \
        --seed=$SEED \
        --alphaUCB=$ALPHA \
        --initialEpsilon=$EPSILON \
        --decayWindow=$DECAY_WIN \
        --lambdaDecay=$LAMBDA \
        --screen=1 2>/dev/null

    local csv="${out}-LNS.csv"
    if [[ -f "$csv" ]]; then
        local soc=$(tail -1 "$csv" | cut -d',' -f3)
        local auc=$(tail -1 "$csv" | cut -d',' -f11)
        local sol=$(tail -1 "$csv" | cut -d',' -f19)
        echo "$map,$algo_name,$soc,$auc,$sol" | tee -a "$OUT_FILE"
    else
        echo "$map,$algo_name,N/A,N/A,0" | tee -a "$OUT_FILE"
    fi
}

for MAP_NAME in "${!MAP_SCEN[@]}"; do
    SCEN="${MAP_SCEN[$MAP_NAME]}"
    echo ""
    echo "=== Map: ${MAP_NAME} ==="
    run_dymab "$MAP_NAME" "$SCEN" "AlphaUCB"      "DyMAB-aUCB"
    run_dymab "$MAP_NAME" "$SCEN" "EpsilonGreedy" "DyMAB-eGreedy"
done

echo ""
echo "Done. Results in $OUT_FILE"
cat "$OUT_FILE"
