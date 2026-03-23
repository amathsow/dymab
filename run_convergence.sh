#!/bin/bash
# ============================================================
# Convergence experiment for Figure 2 (A12)
# Runs all 6 algorithms on 2 maps at increasing time budgets
# Maps  : dense (400 agents), Berlin (600 agents)
# Times : 4, 16, 32, 64, 128 seconds
# Output: dense_convergence.csv, Berlin_convergence.csv
# Columns: runtime, scenario, algorithm, soc, sod, solved
# ============================================================

DYMAB="./dymab"
LNS="./MAPF-LNS-master/lns"
BALANCE="./anytime-mapf-main/build/balance"
MAPS_DIR="./maps"

SEED=0
N_SCENARIOS=25

# DyMAB paper defaults
ALPHA=10000
EPSILON=1
DECAY_WIN=10
LAMBDA=5
NEIGHBOR_SIZES=5

TIME_BUDGETS="4 16 32 64 128"

# ============================================================
# Map / agent definitions
# ============================================================
declare -A MAP_FILE SCEN_DIR SCEN_PREFIX MAP_AGENTS
MAP_FILE["dense"]="${MAPS_DIR}/dense/den520d.map"
SCEN_DIR["dense"]="${MAPS_DIR}/dense/den520d.map-scen-random"
SCEN_PREFIX["dense"]="den520d-random-"
MAP_AGENTS["dense"]=400

MAP_FILE["Berlin"]="${MAPS_DIR}/Berlin/Berlin_1_256.map"
SCEN_DIR["Berlin"]="${MAPS_DIR}/Berlin/Berlin_1_256.map-scen-random"
SCEN_PREFIX["Berlin"]="Berlin_1_256-random-"
MAP_AGENTS["Berlin"]=600

# ============================================================
# Parsers
# ============================================================
parse_dymab_csv() {
    local csv=$1
    if [[ -f "$csv" ]]; then
        local soc=$(tail -1 "$csv" | cut -d',' -f3)
        local sdist=$(tail -1 "$csv" | cut -d',' -f6)
        local solved=$(tail -1 "$csv" | cut -d',' -f19)
        local sod=$(echo "$soc $sdist" | awk '{printf "%.0f", $1 - $2}')
        echo "$soc,$sod,$solved"
    else
        echo "0,0,0"
    fi
}

parse_balance_csv() {
    local csv=$1
    if [[ -f "$csv" ]]; then
        local soc=$(tail -1 "$csv" | cut -d',' -f2)
        local sdist=$(tail -1 "$csv" | cut -d',' -f5)
        local solved=$(tail -1 "$csv" | cut -d',' -f19)
        local sod=$(echo "$soc $sdist" | awk '{printf "%.0f", $1 - $2}')
        echo "$soc,$sod,$solved"
    else
        echo "0,0,0"
    fi
}

# Columns: runtime, solution_cost, initial_cost, min_f, root_g_value, ...
# root_g_value (col5) = sum of shortest paths = sum_dist; no "solved" column
parse_lns_csv() {
    local f=$1
    if [[ -f "$f" ]]; then
        local soc=$(tail -1 "$f" | cut -d',' -f2)
        local sdist=$(tail -1 "$f" | cut -d',' -f5)
        local solved=$(echo "$soc" | awk '{print ($1+0 > 0) ? 1 : 0}')
        local sod=$(echo "$soc $sdist" | awk '{printf "%.0f", $1 - $2}')
        echo "$soc,$sod,$solved"
    else
        echo "0,0,0"
    fi
}

# ============================================================
# MAIN LOOP
# ============================================================
for MAP_NAME in dense Berlin; do
    k=${MAP_AGENTS[$MAP_NAME]}
    MAP_F="${MAP_FILE[$MAP_NAME]}"
    OUT_CSV="${MAP_NAME}_convergence.csv"
    echo "runtime,scenario,algorithm,soc,sod,solved" > "$OUT_CSV"

    echo "============================================"
    echo "  Map: ${MAP_NAME}  agents: ${k}"
    echo "============================================"

    SCEN_COUNT=0
    for SCEN_FILE in "${SCEN_DIR[$MAP_NAME]}"/${SCEN_PREFIX[$MAP_NAME]}*.scen; do
        [[ -f "$SCEN_FILE" ]] || continue
        SCEN_COUNT=$((SCEN_COUNT + 1))
        [[ $SCEN_COUNT -gt $N_SCENARIOS ]] && break

        scen_num=$(basename "$SCEN_FILE" .scen | grep -o '[0-9]*$')
        echo "  scen=${scen_num}"

        for T in $TIME_BUDGETS; do
            echo "    t=${T}s"
            OUT_BASE="/tmp/${MAP_NAME}_k${k}_s${scen_num}_t${T}"

            # --- DyMAB-aUCB ---
            $DYMAB -m "$MAP_F" -a "$SCEN_FILE" -o "${OUT_BASE}_dymab_aucb" \
                -k $k -t $T --banditAlgo=AlphaUCB --destroyStrategy=Adaptive \
                --neighborCandidateSizes=$NEIGHBOR_SIZES --seed=$SEED \
                --alphaUCB=$ALPHA --initialEpsilon=$EPSILON \
                --decayWindow=$DECAY_WIN --lambdaDecay=$LAMBDA --screen=0 2>/dev/null
            res=$(parse_dymab_csv "${OUT_BASE}_dymab_aucb-LNS.csv")
            echo "$T,$scen_num,DyMAB-aUCB,$res" >> "$OUT_CSV"

            # --- DyMAB-eGreedy ---
            $DYMAB -m "$MAP_F" -a "$SCEN_FILE" -o "${OUT_BASE}_dymab_egrdy" \
                -k $k -t $T --banditAlgo=EpsilonGreedy --destroyStrategy=Adaptive \
                --neighborCandidateSizes=$NEIGHBOR_SIZES --seed=$SEED \
                --alphaUCB=$ALPHA --initialEpsilon=$EPSILON \
                --decayWindow=$DECAY_WIN --lambdaDecay=$LAMBDA --screen=0 2>/dev/null
            res=$(parse_dymab_csv "${OUT_BASE}_dymab_egrdy-LNS.csv")
            echo "$T,$scen_num,DyMAB-eGreedy,$res" >> "$OUT_CSV"

            # --- MAPF-LNS2 ---
            $DYMAB -m "$MAP_F" -a "$SCEN_FILE" -o "${OUT_BASE}_lns2" \
                -k $k -t $T --banditAlgo=Random --destroyStrategy=RandomWalk \
                --neighborCandidateSizes=$NEIGHBOR_SIZES --seed=$SEED --screen=0 2>/dev/null
            res=$(parse_dymab_csv "${OUT_BASE}_lns2-LNS.csv")
            echo "$T,$scen_num,MAPF-LNS2,$res" >> "$OUT_CSV"

            # --- MAPF-LNS ---
            $LNS -m "$MAP_F" -a "$SCEN_FILE" -o "${OUT_BASE}_lns" \
                -k $k -t $T -s 0 2>/dev/null
            res=$(parse_lns_csv "${OUT_BASE}_lns")
            echo "$T,$scen_num,MAPF-LNS,$res" >> "$OUT_CSV"

            # --- BALANCE UCB1 ---
            $BALANCE -m "$MAP_F" -a "$SCEN_FILE" -o "${OUT_BASE}_bal_ucb1" \
                -k $k -t $T --banditAlgo=UCB1 --seed=$SEED -s 0 \
                --maxIterations=1000000 2>/dev/null
            res=$(parse_balance_csv "${OUT_BASE}_bal_ucb1-LNS.csv")
            echo "$T,$scen_num,BALANCE-UCB1,$res" >> "$OUT_CSV"

            # --- BALANCE Thompson ---
            $BALANCE -m "$MAP_F" -a "$SCEN_FILE" -o "${OUT_BASE}_bal_tho" \
                -k $k -t $T --banditAlgo=Thompson --seed=$SEED -s 0 \
                --maxIterations=1000000 2>/dev/null
            res=$(parse_balance_csv "${OUT_BASE}_bal_tho-LNS.csv")
            echo "$T,$scen_num,BALANCE-Thompson,$res" >> "$OUT_CSV"

        done
    done

    echo "  -> Saved: $OUT_CSV"
done

echo ""
echo "All done. CSVs:"
ls dense_convergence.csv Berlin_convergence.csv 2>/dev/null
