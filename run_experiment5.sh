#!/bin/bash
# ============================================================
# Run all algorithms for 5 maps, varying number of agents
# Generates one CSV per map: num_agents, scenario, algorithm, soc, sod, solved
# Maps: Berlin, ost003d, dense, random, Linkoping(NewCity)
# Algorithms: DyMAB-aUCB, DyMAB-eGreedy, MAPF-LNS2, MAPF-LNS,
#             BALANCE-UCB1, BALANCE-Thompson
# ============================================================

DYMAB="./dymab"
LNS="./MAPF-LNS-master/lns"
BALANCE="./anytime-mapf-main/build/balance"
MAPS_DIR="./maps"

N_SCENARIOS=25
TIME=120
SEED=0

# Per-map agent counts
declare -A MAP_AGENTS
MAP_AGENTS["Berlin"]="200 500 800 1000"
MAP_AGENTS["ost003d"]="200 400 600"
MAP_AGENTS["dense"]="200 500 800"
MAP_AGENTS["random"]="100 200 300"
MAP_AGENTS["NewCity"]="100 500 1000 1500 2000"

# DyMAB paper defaults
ALPHA=10000
EPSILON=0.5
DECAY_WIN=100
LAMBDA=10
NEIGHBOR_SIZES=5

# ============================================================
# Map definitions: name, map_file, scen_dir, scen_prefix
# ============================================================
declare -A MAP_FILE SCEN_DIR SCEN_PREFIX
MAP_FILE["Berlin"]="${MAPS_DIR}/Berlin/Berlin_1_256.map"
SCEN_DIR["Berlin"]="${MAPS_DIR}/Berlin/Berlin_1_256.map-scen-random"
SCEN_PREFIX["Berlin"]="Berlin_1_256-random-"

MAP_FILE["ost003d"]="${MAPS_DIR}/ost003d/ost003d.map"
SCEN_DIR["ost003d"]="${MAPS_DIR}/ost003d/ost003d.map-scen-random"
SCEN_PREFIX["ost003d"]="ost003d-random-"

MAP_FILE["dense"]="${MAPS_DIR}/dense/den520d.map"
SCEN_DIR["dense"]="${MAPS_DIR}/dense/den520d.map-scen-random"
SCEN_PREFIX["dense"]="den520d-random-"

MAP_FILE["random"]="${MAPS_DIR}/random/random-64-64-10.map"
SCEN_DIR["random"]="${MAPS_DIR}/random/random-64-64-10.map-scen-random"
SCEN_PREFIX["random"]="random-64-64-10-random-"

MAP_FILE["NewCity"]="${MAPS_DIR}/Linkoping/Linkoping_1000x572.map"
SCEN_DIR["NewCity"]="${MAPS_DIR}/Linkoping/random_linkoping"
SCEN_PREFIX["NewCity"]="linkoping_572-"

# ============================================================
# Helper: extract SOD from DyMAB CSV (col3=soc, col6=sum_dist, col19=solved)
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

# Helper: extract SOD from BALANCE CSV (col2=soc, col5=sum_dist, col19=solved)
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

# Helper: extract SOD from MAPF-LNS CSV (col2=soc, col5=sum_dist, col19=solved — same as BALANCE)
parse_lns_csv() {
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

# ============================================================
# MAIN LOOP
# ============================================================
for MAP_NAME in Berlin ost003d dense random NewCity; do
    OUT_CSV="${MAP_NAME}_sod_vs_agents.csv"
    echo "num_agents,scenario,algorithm,soc,sod,solved" > "$OUT_CSV"
    echo "============================================"
    echo "  Map: ${MAP_NAME}"
    echo "============================================"

    IFS=' ' read -ra AGENTS_FOR_MAP <<< "${MAP_AGENTS[$MAP_NAME]}"
    for k in "${AGENTS_FOR_MAP[@]}"; do
        for SCEN_FILE in "${SCEN_DIR[$MAP_NAME]}"/${SCEN_PREFIX[$MAP_NAME]}*.scen; do
            MAP_F="${MAP_FILE[$MAP_NAME]}"
            scen_num=$(basename "$SCEN_FILE" .scen | grep -o '[0-9]*$')

            if [[ ! -f "$SCEN_FILE" ]]; then
                echo "  WARN: missing $SCEN_FILE — skipping"
                continue
            fi

            echo "  k=${k} scen=${scen_num}"
            OUT_BASE="/tmp/${MAP_NAME}_k${k}_s${scen_num}"

            # --- DyMAB-aUCB ---
            $DYMAB -m "$MAP_F" -a "$SCEN_FILE" -o "${OUT_BASE}_dymab_aucb" \
                -k $k -t $TIME --banditAlgo=AlphaUCB --destroyStrategy=Adaptive \
                --neighborCandidateSizes=$NEIGHBOR_SIZES --seed=$SEED \
                --alphaUCB=$ALPHA --initialEpsilon=$EPSILON \
                --decayWindow=$DECAY_WIN --lambdaDecay=$LAMBDA --screen=0 2>/dev/null
            res=$(parse_dymab_csv "${OUT_BASE}_dymab_aucb-LNS.csv")
            echo "$k,$scen_num,DyMAB-aUCB,$res" >> "$OUT_CSV"

            # --- DyMAB-eGreedy ---
            $DYMAB -m "$MAP_F" -a "$SCEN_FILE" -o "${OUT_BASE}_dymab_egrdy" \
                -k $k -t $TIME --banditAlgo=EpsilonGreedy --destroyStrategy=Adaptive \
                --neighborCandidateSizes=$NEIGHBOR_SIZES --seed=$SEED \
                --alphaUCB=$ALPHA --initialEpsilon=$EPSILON \
                --decayWindow=$DECAY_WIN --lambdaDecay=$LAMBDA --screen=0 2>/dev/null
            res=$(parse_dymab_csv "${OUT_BASE}_dymab_egrdy-LNS.csv")
            echo "$k,$scen_num,DyMAB-eGreedy,$res" >> "$OUT_CSV"

            # --- MAPF-LNS2 ---
            $DYMAB -m "$MAP_F" -a "$SCEN_FILE" -o "${OUT_BASE}_lns2" \
                -k $k -t $TIME --banditAlgo=Random --destroyStrategy=RandomWalk \
                --neighborCandidateSizes=$NEIGHBOR_SIZES --seed=$SEED --screen=0 2>/dev/null
            res=$(parse_dymab_csv "${OUT_BASE}_lns2-LNS.csv")
            echo "$k,$scen_num,MAPF-LNS2,$res" >> "$OUT_CSV"

            # --- MAPF-LNS ---
            $LNS -m "$MAP_F" -a "$SCEN_FILE" -o "${OUT_BASE}_lns" \
                -k $k -t $TIME -s 0 2>/dev/null
            res=$(parse_lns_csv "${OUT_BASE}_lns.csv")
            echo "$k,$scen_num,MAPF-LNS,$res" >> "$OUT_CSV"

            # --- BALANCE UCB1 ---
            $BALANCE -m "$MAP_F" -a "$SCEN_FILE" -o "${OUT_BASE}_bal_ucb1" \
                -k $k -t $TIME --banditAlgo=UCB1 --seed=$SEED -s 0 \
                --maxIterations=1000000 2>/dev/null
            res=$(parse_balance_csv "${OUT_BASE}_bal_ucb1-LNS.csv")
            echo "$k,$scen_num,BALANCE-UCB1,$res" >> "$OUT_CSV"

            # --- BALANCE Thompson ---
            $BALANCE -m "$MAP_F" -a "$SCEN_FILE" -o "${OUT_BASE}_bal_tho" \
                -k $k -t $TIME --banditAlgo=Thompson --seed=$SEED -s 0 \
                --maxIterations=1000000 2>/dev/null
            res=$(parse_balance_csv "${OUT_BASE}_bal_tho-LNS.csv")
            echo "$k,$scen_num,BALANCE-Thompson,$res" >> "$OUT_CSV"

        done
    done

    echo "  -> Saved: $OUT_CSV"
done

echo ""
echo "All done. CSVs generated:"
ls *_sod_vs_agents.csv 2>/dev/null
