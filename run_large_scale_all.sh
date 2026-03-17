#!/bin/bash
# ============================================================
# Large-scale anytime comparison: varying runtime budgets
# Fixed: k=3500 agents on all 7 large maps
# Runtimes: 60, 120, 300, 500 seconds
# Algorithms: MAPF-LNS2, UCB1, Thompson, DyMAB(α-UCB),
#             DyMAB(ε-Greedy), LaCAM*, ADDRESS
# Output: large_scale_results.csv
# ============================================================

DYMAB="./dymab"
LACAM2="./lacam2-dev/build/main"
ADDRESS="./ADDRESS-main/address"
MAPS_DIR="./maps/large"
RESULTS_FILE="large_scale_results.csv"
AGENTS=3500
SEED=0

# DyMAB hyperparameters (paper defaults)
ALPHA=10000
EPSILON=0.5
DECAY_WIN=100
LAMBDA=10
NEIGHBOR_SIZES=5

# Maps and their single scenario files
declare -A MAP_SCEN
MAP_SCEN["Boston_0_1024"]="Boston_0_1024.map.scen"
MAP_SCEN["Moscow_0_1024"]="Moscow_0_1024.map.scen"
MAP_SCEN["NewYork_0_1024"]="NewYork_0_1024.map.scen"
MAP_SCEN["Paris_0_1024"]="Paris_0_1024.map.scen"
MAP_SCEN["Shanghai_0_1024"]="Shanghai_0_1024.map.scen"
MAP_SCEN["Sydney_0_1024"]="Sydney_0_1024.map.scen"
MAP_SCEN["warehouse-20-40-10-2-2"]="warehouse-20-40-10-2-2-10000agents-1.scen"

# Write CSV header
echo "time_budget,map,algorithm,soc,auc,solved" > "$RESULTS_FILE"

# ============================================================
run_dymab() {
    local map=$1 scen=$2 time=$3 algo_flag=$4 algo_name=$5
    local map_file="${MAPS_DIR}/${map}.map"
    local scen_file="${MAPS_DIR}/${scen}"
    [[ "$map" == "warehouse"* ]] && scen_file="./maps/scen-warehouse/${scen}"

    local out="/tmp/dymab_${map}_t${time}_${algo_name}"
    echo "  [${algo_name}] ${map} t=${time}s ..."

    $DYMAB -m "$map_file" -a "$scen_file" -o "$out" \
        -k "$AGENTS" -t "$time" \
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

    # DyMAB CSV: col1=agents, col2=runtime, col3=soc, col11=auc, col19=success
    local csv="${out}-LNS.csv"
    if [[ -f "$csv" ]]; then
        local soc=$(tail -1 "$csv" | cut -d',' -f3)
        local auc=$(tail -1 "$csv" | cut -d',' -f11)
        local sol=$(tail -1 "$csv" | cut -d',' -f19)
        echo "$time,$map,$algo_name,$soc,$auc,$sol" | tee -a "$RESULTS_FILE"
    else
        echo "$time,$map,$algo_name,N/A,N/A,0" | tee -a "$RESULTS_FILE"
    fi
}

run_lns2() {
    local map=$1 scen=$2 time=$3
    local map_file="${MAPS_DIR}/${map}.map"
    local scen_file="${MAPS_DIR}/${scen}"
    [[ "$map" == "warehouse"* ]] && scen_file="./maps/scen-warehouse/${scen}"

    local out="/tmp/dymab_${map}_t${time}_LNS2"
    echo "  [MAPF-LNS2] ${map} t=${time}s ..."

    $DYMAB -m "$map_file" -a "$scen_file" -o "$out" \
        -k "$AGENTS" -t "$time" \
        --outputPaths="${out}_paths.txt" \
        --banditAlgo=Random \
        --destroyStrategy=RandomWalk \
        --neighborCandidateSizes=$NEIGHBOR_SIZES \
        --seed=$SEED --screen=1 2>/dev/null

    # DyMAB CSV: col1=agents, col2=runtime, col3=soc, col11=auc, col19=success
    local csv="${out}-LNS.csv"
    if [[ -f "$csv" ]]; then
        local soc=$(tail -1 "$csv" | cut -d',' -f3)
        local auc=$(tail -1 "$csv" | cut -d',' -f11)
        local sol=$(tail -1 "$csv" | cut -d',' -f19)
        echo "$time,$map,MAPF-LNS2,$soc,$auc,$sol" | tee -a "$RESULTS_FILE"
    else
        echo "$time,$map,MAPF-LNS2,N/A,N/A,0" | tee -a "$RESULTS_FILE"
    fi
}

run_lacam2() {
    local map=$1 scen=$2 time=$3
    local map_file="${MAPS_DIR}/${map}.map"
    local scen_file="${MAPS_DIR}/${scen}"
    [[ "$map" == "warehouse"* ]] && scen_file="./maps/scen-warehouse/${scen}"

    local out="/tmp/lacam2_${map}_t${time}.txt"
    echo "  [LaCAM*] ${map} t=${time}s ..."

    $LACAM2 -m "$map_file" -i "$scen_file" -N "$AGENTS" \
        -t "$time" -o "$out" --log_short --objective 2 -v 0 -s $SEED 2>&1

    if [[ -f "$out" ]]; then
        local soc=$(grep "^soc="     "$out" | cut -d'=' -f2)
        local rt=$(grep  "^comp_time=" "$out" | cut -d'=' -f2)
        local sol=$(grep "^solved="  "$out" | cut -d'=' -f2)
        # LaCAM* has no AUC (complete solver, single result)
        echo "$time,$map,LaCAM*,$soc,—,$sol" | tee -a "$RESULTS_FILE"
    else
        echo "$time,$map,LaCAM*,N/A,—,0" | tee -a "$RESULTS_FILE"
    fi
}

run_address() {
    local map=$1 scen=$2 time=$3
    local map_file="${MAPS_DIR}/${map}.map"
    local scen_file="${MAPS_DIR}/${scen}"
    [[ "$map" == "warehouse"* ]] && scen_file="./maps/scen-warehouse/${scen}"

    local out="/tmp/address_${map}_t${time}"
    echo "  [ADDRESS] ${map} t=${time}s ..."

    $ADDRESS -m "$map_file" -a "$scen_file" -k "$AGENTS" \
        -t "$time" -o "$out" \
        --seed=$SEED --screen=0 --maxIterations=1000000 \
        --destroyStrategy=RandomWalk \
        --algorithm=bernoulie --k=64 2>/dev/null

    # ADDRESS CSV: col1=runtime, col2=soc, col10=auc, col18=success
    local csv="${out}-LNS.csv"
    if [[ -f "$csv" ]]; then
        local soc=$(tail -1 "$csv" | cut -d',' -f2)
        local auc=$(tail -1 "$csv" | cut -d',' -f10)
        local sol=$(tail -1 "$csv" | cut -d',' -f18)
        echo "$time,$map,ADDRESS,$soc,$auc,$sol" | tee -a "$RESULTS_FILE"
    else
        echo "$time,$map,ADDRESS,N/A,N/A,0" | tee -a "$RESULTS_FILE"
    fi
}

# ============================================================
# MAIN LOOP: varying runtime budgets, fixed k=3500
# Note: 60s dropped — initial solution alone takes >60s at this scale
# ============================================================
for TIME_BUDGET in 120 300 500 600; do
    echo "============================================"
    echo "  Runtime = ${TIME_BUDGET}s  |  k=${AGENTS} agents"
    echo "============================================"

    for MAP_NAME in "${!MAP_SCEN[@]}"; do
        SCEN="${MAP_SCEN[$MAP_NAME]}"
        echo ""
        echo "--- Map: ${MAP_NAME} ---"

        run_lns2   "$MAP_NAME" "$SCEN" "$TIME_BUDGET"
        run_dymab  "$MAP_NAME" "$SCEN" "$TIME_BUDGET" "UCB1"          "UCB1"
        run_dymab  "$MAP_NAME" "$SCEN" "$TIME_BUDGET" "Thompson"      "Thompson"
        run_dymab  "$MAP_NAME" "$SCEN" "$TIME_BUDGET" "AlphaUCB"      "DyMAB-aUCB"
        run_dymab  "$MAP_NAME" "$SCEN" "$TIME_BUDGET" "EpsilonGreedy" "DyMAB-eGreedy"
        run_lacam2 "$MAP_NAME" "$SCEN" "$TIME_BUDGET"
        run_address "$MAP_NAME" "$SCEN" "$TIME_BUDGET"
    done
done

echo ""
echo "============================================"
echo " Done. Results saved to $RESULTS_FILE"
echo "============================================"
echo ""
cat "$RESULTS_FILE"
