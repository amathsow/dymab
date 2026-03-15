#!/bin/bash

# Run a single representative scenario and collect per-iteration reward log
# Then plot the reward time-series to visualise piecewise non-stationarity

MAP="maps/dense/den520d.map"
SCENARIO="maps/dense/den520d.map-scen-random/den520d-random-1.scen"
AGENTS=400
TIME=100
WINDOW=100
DECAY=5
EPSILON=1.0   # start at 1 so all arms are explored uniformly early on

echo "Rebuilding binary with reward logging..."
make -C . -j4 2>&1 | tail -5

echo "Running DyMAB to collect reward log..."
./dymab \
    -m $MAP \
    -a $SCENARIO \
    -o test \
    -k $AGENTS \
    -t $TIME \
    --outputPaths=paths.txt \
    --banditAlgo=Random \
    --neighborCandidateSizes=5 \
    --seed=0 \
    --decayWindow=$WINDOW \
    --lambdaDecay=$DECAY

echo "Plotting reward non-stationarity..."
python3 plot_reward_nonstationarity.py

echo "Done. See reward_nonstationarity.png"
